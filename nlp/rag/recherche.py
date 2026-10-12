"""Recherche du RAG : ce que le LLM a compris de la question -> les fiches
qu'on lui donne pour repondre.

Trois recherches, selon la Requete (ecrite par comprendre.py) :
  par les noms    medicaments cites -> leur fiche, et la notice de leur molecule ;
  par la distance pharmacies d'un lieu, de garde, ou citees par leur nom
                  (outils/pharmacies.py). La garde du jour vient de Telecontact
                  (outils/garde.py) ; a defaut, des horaires 24h/24 ou nuit ;
  par le sens     toujours : les symptomes de la liste blanche les plus proches
                  de la question, dans ChromaDB, pour qu'aucune partie du message
                  ne reste sans reponse ("3ndi sda3, fin kayna pharmacie f maarif ?").
                  Seulement les symptomes : sans medicament nomme, la recherche
                  par le sens ramenait des notices sans rapport (la morphine pour
                  un mal de tete), que le LLM aurait pu prendre pour un conseil.

Quand une recherche ne donne rien, ou qu'il faut une precision du patient,
une fiche de type "note" le dit au LLM : il n'a pas a deviner.
"""
from dataclasses import dataclass, field
from functools import lru_cache

from rapidfuzz import fuzz, process

from nlp.linking.lieux import Lieu, resoudre_lieu
from nlp.linking.medicaments import normalize, transliterate
from nlp.linking.pharmacies import distance_km
from nlp.outils.garde import garde_du_jour
from nlp.outils.pharmacies import info_pharmacie, pharmacie_garde, pharmacies_lieu
from nlp.outils.resolution import matcher
from nlp.outils.securite import SEPARATEURS
from nlp.rag.fiches import OUVERTURES, STATUTS_AVEC_PRIX, telephone
from nlp.rag.index import collection, vecteur_question

MAX_MEDICAMENTS = 3     # par message : au-dela, la reponse devient illisible
MAX_MARQUES = 3         # marques montrees pour une molecule ou un nom incertain
MAX_FICHES_MOLECULE = 6 # une marque a parfois plusieurs fiches ("GLUCOPHAGE 500", "GLUCOPHAGE 850")
MAX_NOTICES = 4         # morceaux de notice par molecule
MAX_CONSEILS = 3        # symptomes de la liste blanche trouves par le sens
# Ressemblance minimale (0-100) entre le nom cite et une molecule de la base.
SEUIL_MOLECULE = 90
# "PP" (AMMPS) et "PRINCEPS" (CNOPS) : la marque d'origine d'une molecule.
PRINCEPS = {"PP", "PRINCEPS"}

MAX_GARDE = 5           # pharmacies de garde citees : les plus proches du quartier
GARDES = {"jour": "de jour", "nuit": "de nuit", "24h": "24h/24"}

TOUR_DE_GARDE = ("Le tour de garde du jour n'est pas dans nos données. Les pharmacies "
                 "ci-dessous sont ouvertes 24h/24 ou la nuit d'après leurs horaires.")


@dataclass
class Requete:
    """Ce que le LLM a compris du message du patient."""
    question: str                                   # reformulee en francais
    medicaments: list[str] = field(default_factory=list)   # noms, tels qu'ecrits
    lieu: str | None = None                         # ville et/ou quartier cites
    pharmacie: str | None = None                    # pharmacie citee par son nom
    pharmacies: bool = False                        # il cherche une pharmacie
    garde: bool = False                             # ... de garde, de nuit


@dataclass
class Trouve:
    fiches: list[dict] = field(default_factory=list)       # {"id", "type", "texte"} pour le LLM
    pharmacies: list[dict] = field(default_factory=list)   # pour les cartes de l'interface
    ville: str | None = None                               # ville reconnue, gardee pour la suite


def _note(texte: str) -> dict:
    return {"id": f"note:{texte}", "type": "note", "texte": texte}


# --- ChromaDB ---------------------------------------------------------------

def _en_fiches(ids, textes, metas) -> list[dict]:
    return [{"id": i, "type": m["type"], "texte": t, "meta": m}
            for i, t, m in zip(ids, textes, metas)]


def _par_ids(ids: list[str]) -> list[dict]:
    r = collection().get(ids=ids)
    return _en_fiches(r["ids"], r["documents"], r["metadatas"])


def _par_sens(vecteur: list[float], filtre: dict, combien: int) -> list[dict]:
    r = collection().query(query_embeddings=[vecteur], n_results=combien, where=filtre)
    return _en_fiches(r["ids"][0], r["documents"][0], r["metadatas"][0])


# --- medicaments ------------------------------------------------------------

def _molecule(nom: str) -> str | None:
    """La DCI, ecrite comme dans les fiches, si le patient a cite une molecule
    ("paracetamol") et non une marque."""
    m = matcher()
    hit = process.extractOne(normalize(transliterate(nom)), m.unique_dcis,
                             scorer=fuzz.ratio, score_cutoff=SEUIL_MOLECULE)
    if not hit:
        return None
    return str(m.df.loc[m.df["dci_norm"] == hit[0], "dci"].mode().iloc[0]).upper()


def _notices(dci: str, vecteur: list[float]) -> list[dict]:
    """Les morceaux de la notice de la molecule les plus proches de la question.
    Une association ("AMOXICILLINE / ACIDE CLAVULANIQUE") peut manquer alors
    que ses composants sont documentes : on les cherche aussi."""
    cles = [dci] + [p.strip() for p in SEPARATEURS.split(dci) if p.strip()]
    trouvees = _par_sens(vecteur, {"$and": [{"type": "notice"}, {"dci": {"$in": cles}}]},
                         MAX_NOTICES)
    return trouvees or [_note(f"Aucune notice de la molécule {dci} dans nos données.")]


@lru_cache(maxsize=None)
def _marques(dci: str) -> tuple[tuple[str, ...], ...]:
    """Les marques d'une molecule, la plus connue d'abord ; pour chacune, les
    cles nom_norm de ses fiches ("GLUCOPHAGE 500" et "GLUCOPHAGE 850" sont la
    meme marque : meme premier mot).

    Nos sources ne disent pas quelle marque se vend le mieux. On prend donc
    d'abord les princeps (la marque d'origine, en general celle que les gens
    nomment), puis les marques qui ont le plus de presentations.
    """
    df = matcher().df
    lignes = df[(df["dci"].fillna("").str.upper() == dci)
                & (df["statut_commercialisation"].isna()
                   | df["statut_commercialisation"].isin(STATUTS_AVEC_PRIX))]
    marques = []
    for _, groupe in lignes.groupby(lignes["nom_norm"].str.split().str[0]):
        princeps = groupe["type_produit"].isin(PRINCEPS).any()
        presentations = len(groupe[["dosage_cle", "forme"]].drop_duplicates())
        noms = tuple(sorted(groupe["nom_norm"].unique()))
        marques.append((not princeps, -presentations, noms))
    return tuple(noms for _, _, noms in sorted(marques))


def _medicament(nom: str, vecteur: list[float]) -> list[dict]:
    dci = _molecule(nom)
    if dci:
        marques = _marques(dci)
        ids = [f"med:{n}" for noms in marques[:MAX_MARQUES] for n in noms][:MAX_FICHES_MOLECULE]
        trouvees = {f["id"]: f for f in _par_ids(ids)} if ids else {}
        # ChromaDB ne rend pas les fiches dans l'ordre demande
        fiches = [trouvees[i] for i in ids if i in trouvees]
        autres = len(marques) - min(len(marques), MAX_MARQUES)
        note = _note(f"« {nom} » est une molécule ({dci}), vendue sous plusieurs marques. Voici les "
                     "plus connues ; le prix dépend de la marque."
                     + (f" Il existe {autres} autres marques dans nos données : le dire au patient "
                        "et lui proposer de préciser la marque qu'il cherche." if autres > 0 else ""))
        return [note] + fiches + _notices(dci, vecteur)

    # Le matcher renvoie toujours ses meilleurs candidats, meme quand aucun ne
    # ressemble : un candidat "non_fiable" n'est jamais montre.
    candidats = [c for c in matcher().match(nom, top_k=MAX_MARQUES)
                 if c["confidence"] != "non_fiable"]
    if not candidats:
        return [_note(f"Le médicament « {nom} » n'existe pas dans nos données.")]
    if candidats[0]["confidence"] != "auto":
        noms = ", ".join(c["nom_candidat"] for c in candidats)
        return [_note(f"« {nom} » n'est pas reconnu avec certitude. Noms proches : {noms}. "
                      "Demander au patient lequel il veut dire, sans donner d'autre information.")]
    fiches = _par_ids([f"med:{normalize(candidats[0]['nom_candidat'])}"])
    dci = fiches[0]["meta"].get("dci") if fiches else None
    return fiches + (_notices(dci, vecteur) if dci else [])


# --- pharmacies -------------------------------------------------------------

def _fiche_pharmacie(p: dict) -> dict:
    """Meme texte que fiches.py, plus la distance au lieu demande."""
    texte = [f"Pharmacie : {p['nom']}" + (f" ({p['nom_ar']})" if p.get("nom_ar") else ""),
             f"Ville : {p['ville']}"]
    if p.get("adresse"):
        texte.append(f"Adresse : {p['adresse']}")
    if (tel := telephone(p.get("telephone"))):
        texte.append(f"Téléphone : {tel}")
    if p.get("horaires"):
        texte.append(f"Horaires : {p['horaires']}")
    if p.get("garde_du_jour"):
        texte.append(f"De garde le {p['garde_du_jour']} : {GARDES[p['ouverture']]}")
    elif p.get("ouverture"):
        texte.append(f"Ouverture : {OUVERTURES[p['ouverture']]}")
    if p.get("distance_km") is not None:
        texte.append(f"Distance du lieu demandé : {p['distance_km']} km")
    return {"id": f"pharma:{p['nom']}:{p['ville']}:{p.get('adresse')}", "type": "pharmacie",
            "texte": "\n".join(texte)}


def _note_pharmacies(res: dict) -> dict | None:
    """Ce que le LLM doit dire ou demander, selon le statut rendu par l'outil."""
    statut = res["statut"]
    if statut == "lieu_inconnu":
        if res.get("cite"):
            return _note(f"Le lieu « {res['cite']} » n'existe pas dans nos données : "
                         "demander au patient sa ville ou un quartier voisin.")
        return _note("Le patient n'a pas dit où il se trouve : lui demander sa ville ou son quartier.")
    if statut == "preciser_ville":
        nom = res.get("lieu") or res.get("nom")
        return _note(f"« {nom} » existe dans plusieurs villes ({', '.join(res['villes'])}) : "
                     "demander au patient laquelle.")
    if statut == "preciser_quartier":
        return _note(f"{res['ville']} compte {res['nb_pharmacies']} pharmacies dans nos données : "
                     "demander au patient son quartier.")
    if statut == "introuvable":
        return _note(f"La pharmacie « {res['cite']} » n'existe pas dans nos données.")
    if statut == "aucune":
        return _note(f"Aucune pharmacie ouverte 24h/24 ou la nuit à {res['ville']} dans nos données. "
                     "Le tour de garde du jour n'est pas dans nos données.")
    if statut == "a_confirmer":
        return _note(f"La pharmacie « {res['cite']} » n'est pas reconnue avec certitude : "
                     "demander au patient de confirmer le nom ci-dessous.")
    if res.get("quartier_inconnu"):
        return _note(f"Le quartier « {res['quartier_inconnu']} » n'existe pas dans nos données : "
                     f"voici les pharmacies de {res['ville']}.")
    return None


def _garde(lieu: Lieu | None) -> dict | None:
    """Les pharmacies de garde aujourd'hui dans la ville du lieu, les plus
    proches du quartier d'abord ; None si on ne connait pas le tour de garde
    (lieu a preciser, ville non couverte, site injoignable)."""
    if lieu is None or lieu.statut not in ("quartier", "ville"):
        return None
    garde = garde_du_jour(lieu.ville)
    if not garde:
        return None
    pres_de = (lieu.latitude, lieu.longitude) if lieu.statut == "quartier" else None
    pharmacies = []
    for p in garde["pharmacies"]:
        situee = p["latitude"] is not None and p["longitude"] is not None
        pharmacies.append({
            "nom": p["nom"], "nom_ar": None, "adresse": p["adresse"], "telephone": p["telephone"],
            "horaires": None, "ville": lieu.ville, "quartier": p["quartier"],
            "latitude": p["latitude"], "longitude": p["longitude"],
            "precision_gps": "exacte" if situee else None,
            "distance_km": round(distance_km(*pres_de, p["latitude"], p["longitude"]), 1)
                           if pres_de and situee else None,
            "ouverture": p["ouverture"], "garde_du_jour": garde["date"], "source": garde["source"],
        })
    base = {"ville": lieu.ville, "date": garde["date"], "source": garde["source"]}
    if pres_de:
        pharmacies.sort(key=lambda p: (p["distance_km"] is None, p["distance_km"] or 0.0))
    elif len(pharmacies) > MAX_GARDE:
        # grande ville sans quartier : une liste de 40 officines n'aide personne
        return base | {"statut": "garde_preciser_quartier", "nb_pharmacies": len(pharmacies)}
    return base | {"statut": "garde_du_jour", "pharmacies": pharmacies[:MAX_GARDE]}


def _note_garde(res: dict) -> dict:
    if res["statut"] == "garde_preciser_quartier":
        return _note(f"{res['ville']} compte {res['nb_pharmacies']} pharmacies de garde le {res['date']} : "
                     "demander au patient son quartier pour lui donner les plus proches.")
    return _note(f"Pharmacies de garde à {res['ville']} le {res['date']}, d'après {res['source']}. "
                 "Pour chacune, dire si elle est de garde de jour, de nuit ou 24h/24. "
                 f"Dire que la liste vient de {res['source']} et conseiller d'appeler avant de se déplacer.")


def _pharmacies(requete: Requete, ville_connue: str | None, trouve: Trouve) -> None:
    # sans lieu dans le message, la ville deja dite dans la conversation sert de lieu
    cite = requete.lieu or ville_connue
    lieu = resoudre_lieu(cite, ville_connue) if cite else None
    if lieu and lieu.ville and lieu.statut in ("quartier", "ville"):
        trouve.ville = lieu.ville

    resultats = []
    if requete.pharmacie:
        resultats.append(info_pharmacie(requete.pharmacie, lieu if requete.lieu else None, ville_connue))
    if requete.garde:
        # le tour de garde du jour si on le connait, sinon les horaires 24h/24 ou nuit
        resultats.append(_garde(lieu) or pharmacie_garde(lieu))
    elif requete.pharmacies and not requete.pharmacie:
        resultats.append(pharmacies_lieu(lieu))

    for res in resultats:
        if res["statut"].startswith("garde_"):
            trouve.fiches.append(_note_garde(res))
        elif (note := _note_pharmacies(res)):
            trouve.fiches.append(note)
        if res.get("tour_de_garde_connu") is False and res.get("pharmacies"):
            trouve.fiches.append(_note(TOUR_DE_GARDE))
        for p in res.get("pharmacies", []):
            trouve.fiches.append(_fiche_pharmacie(p))
            trouve.pharmacies.append(p)


# --- recherche complete -----------------------------------------------------

def chercher(requete: Requete, ville_connue: str | None = None) -> Trouve:
    """Les fiches utiles pour repondre a la requete, sans doublon."""
    trouve = Trouve(ville=ville_connue)
    veut_pharmacie = bool(requete.pharmacie or requete.pharmacies or requete.garde)
    vecteur = vecteur_question(requete.question)

    if veut_pharmacie:
        _pharmacies(requete, ville_connue, trouve)
    for nom in requete.medicaments[:MAX_MEDICAMENTS]:
        trouve.fiches += _medicament(nom, vecteur)

    trouve.fiches += _par_sens(vecteur, {"type": "conseil"}, MAX_CONSEILS)

    vues, uniques = set(), []
    for f in trouve.fiches:
        if f["id"] not in vues:
            vues.add(f["id"])
            uniques.append(f)
    trouve.fiches = uniques
    return trouve
