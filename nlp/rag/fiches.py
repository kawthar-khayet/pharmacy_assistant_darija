"""Fiches du RAG : les bases de data/clean/ reecrites en petits textes.

Le LLM ne lit pas les CSV : il recoit quelques fiches, choisies par
recherche.py, et repond seulement avec ce qu'elles contiennent. Une fiche =
un texte court et complet sur UN sujet :
  medicament  un nom de medicament : presentations, prix, remboursement
  notice      une rubrique de la notice d'une molecule (coupee si elle est longue)
  pharmacie   une pharmacie : adresse, telephone, horaires
  conseil     un symptome benin de la liste blanche

`meta` porte ce qui sert a chercher autrement que par le sens : nom du
medicament, molecule, ville, position GPS.

Lancer une fois, puis apres chaque mise a jour des CSV :
    py -m nlp.rag.fiches
"""
import json
import re
from collections import Counter

import pandas as pd

from nlp.config import DATA_CLEAN, RACINE
from nlp.linking.medicaments import STATUTS_EN_OFFICINE, dose_mg
from nlp.outils.conseil import commercialisee
from nlp.outils.pharmacies import type_ouverture
from nlp.outils.prix import REGIMES, presentations
from nlp.outils.resolution import matcher
from nlp.outils.securite import RUBRIQUES, SECURITE_PATH, nettoyer

FICHES_PATH = RACINE / "data" / "rag" / "fiches.jsonl"
PHARMACIES_PATH = DATA_CLEAN / "pharmacies_fusion.csv"
SYMPTOMES_PATH = DATA_CLEAN / "conseil_symptomes.csv"

# Le modele d'embeddings ne lit que le debut d'un long texte (512 tokens) :
# une rubrique de notice est coupee en morceaux de cette taille (caracteres).
TAILLE_MORCEAU = 1200

LIBELLES_RUBRIQUES = {
    "indications": "à quoi il sert (indications)",
    "effets_indesirables": "effets indésirables",
    "contre_indications": "contre-indications",
    "precautions": "précautions d'emploi",
    "interactions": "interactions avec d'autres médicaments",
    "grossesse_allaitement": "grossesse et allaitement",
}
OUVERTURES = {"24h": "ouverte 24h/24", "nuit": "ouverte la nuit"}

# Presentations dont on donne le prix. Les statuts "Retire" et "Suspendu" du
# registre AMMPS en font partie : ce registre marque ainsi des produits encore
# vendus en pharmacie (les suppositoires Panadol), on ne s'y fie donc pas pour
# cacher un prix. Restent ecartes l'export et les appels d'offres hospitaliers.
STATUTS_AVEC_PRIX = STATUTS_EN_OFFICINE | {"Retiré du Marché", "Suspendu du Marché"}


def _texte(x) -> str | None:
    """None pour une case vide (pandas la lit en NaN)."""
    return None if pd.isna(x) or not str(x).strip() else str(x).strip()


def _plus_frequent(lignes: pd.DataFrame, colonne: str) -> str | None:
    """La valeur la plus courante de la colonne : les sources (AMMPS, CNOPS,
    CNSS) n'ecrivent pas toujours la molecule ou le laboratoire pareil."""
    valeurs = lignes[colonne].dropna()
    return str(valeurs.mode().iloc[0]) if len(valeurs) else None


def _fiche(id_: str, type_: str, texte: str, **meta) -> dict:
    # la base vectorielle n'accepte pas de valeur vide dans meta
    return {"id": id_, "type": type_, "texte": texte,
            "meta": {c: v for c, v in meta.items() if v is not None}}


# --- medicaments ------------------------------------------------------------

def _remboursement_txt(regime: str, r: dict | None) -> str:
    nom = regime.upper()
    if r is None:
        return f"remboursement {nom} inconnu"
    if r["taux"] == 0:
        return f"non remboursé par la {nom}"
    if r["montant"] is None:
        return f"remboursé à {r['taux']:g} % par la {nom} (montant inconnu)"
    return (f"remboursé à {r['taux']:g} % par la {nom}, sur une base de "
            f"{r['base']:.2f} DH, soit {r['montant']:.2f} DH")


def _presentation_txt(p: dict) -> str:
    quoi = ", ".join(x for x in (p["dosage"], p["forme"]) if x) or "présentation unique"
    prix = f"prix public {p['ppv']:.2f} DH" if p["ppv"] is not None else "prix public inconnu"
    return f"- {quoi} : " + " ; ".join([prix] + [_remboursement_txt(r, p[r]) for r in REGIMES])


def fiches_medicaments() -> list[dict]:
    """Une fiche par nom de medicament, avec toutes ses presentations en officine."""
    df = matcher().df
    fiches = []
    for nom_norm, lignes in df.groupby("nom_norm", sort=True):
        if not nom_norm:
            continue
        nom = str(lignes["nom"].iloc[0])
        dci = _plus_frequent(lignes, "dci")
        # Une ligne sans statut vient des listes CNOPS / CNSS et reste valable.
        en_officine = lignes[lignes["statut_commercialisation"].isna()
                             | lignes["statut_commercialisation"].isin(STATUTS_AVEC_PRIX)]
        trouvees = presentations(en_officine) if len(en_officine) else []
        trouvees.sort(key=lambda p: dose_mg(p["dosage"]) or float("inf"))

        texte = [f"Médicament : {nom}"]
        if dci:
            texte.append(f"Molécule (DCI) : {dci}")
        if (classe := _plus_frequent(lignes, "classe_therapeutique")):
            texte.append(f"Classe : {classe}")
        if (labo := _plus_frequent(lignes, "laboratoire")):
            texte.append(f"Laboratoire : {labo}")
        if trouvees:
            texte.append("Présentations vendues au Maroc :")
            texte += [_presentation_txt(p) for p in trouvees]
        else:
            texte.append("Ce médicament n'est plus commercialisé au Maroc : pas de prix.")
        fiches.append(_fiche(f"med:{nom_norm}", "medicament", "\n".join(texte),
                             nom=nom, nom_norm=nom_norm, dci=dci.upper() if dci else None,
                             commercialise=bool(trouvees)))
    return fiches


# --- notices ----------------------------------------------------------------

def _morceaux(texte: str, taille: int = TAILLE_MORCEAU) -> list[str]:
    """Coupe entre deux lignes, jamais au milieu d'une phrase."""
    morceaux, courant = [], ""
    for ligne in texte.splitlines():
        if courant and len(courant) + len(ligne) + 1 > taille:
            morceaux.append(courant)
            courant = ligne
        else:
            courant = f"{courant}\n{ligne}" if courant else ligne
    if courant:
        morceaux.append(courant)
    return morceaux


def fiches_notices() -> list[dict]:
    """Une fiche par molecule et par rubrique de la notice (BDPM)."""
    if not SECURITE_PATH.exists():
        return []
    fiches = []
    for ligne in pd.read_csv(SECURITE_PATH).to_dict("records"):
        dci = str(ligne["dci"]).upper()
        specialite = _texte(ligne.get("specialite_bdpm"))
        for rubrique in RUBRIQUES:
            contenu = nettoyer(ligne.get(rubrique))
            if not contenu:
                continue
            morceaux = _morceaux(contenu)
            for i, morceau in enumerate(morceaux, start=1):
                partie = f" (partie {i}/{len(morceaux)})" if len(morceaux) > 1 else ""
                texte = [f"Notice de la molécule {dci} — {LIBELLES_RUBRIQUES[rubrique]}{partie}"]
                if specialite:
                    # la notice est francaise : elle decrit la molecule, pas la boite marocaine
                    texte.append(f"(notice française de {specialite})")
                texte.append(morceau)
                fiches.append(_fiche(f"notice:{dci}:{rubrique}:{i}", "notice", "\n".join(texte),
                                     dci=dci, rubrique=rubrique, partie=i))
    return fiches


# --- pharmacies -------------------------------------------------------------

def telephone(tel) -> str | None:
    """"528842597" -> "0528842597" : la base a perdu le zero du debut."""
    chiffres = re.sub(r"\D", "", _texte(tel) or "")
    if not chiffres:
        return None
    return "0" + chiffres if len(chiffres) == 9 else chiffres


def fiches_pharmacies() -> list[dict]:
    """Une fiche par pharmacie ; la position GPS reste dans meta pour la distance."""
    df = pd.read_csv(PHARMACIES_PATH, dtype={"id": str, "telephone": str})
    fiches = []
    for r in df.to_dict("records"):
        nom, ville = _texte(r["nom"]), _texte(r["ville"])
        if not nom:
            continue
        nom_ar, ville_ar = _texte(r["nom_ar"]), _texte(r["ville_ar"])
        ouverture = type_ouverture(r["horaires"])

        texte = [f"Pharmacie : {nom}" + (f" ({nom_ar})" if nom_ar else "")]
        if ville:
            texte.append(f"Ville : {ville}" + (f" ({ville_ar})" if ville_ar else ""))
        if (adresse := _texte(r["adresse"])):
            texte.append(f"Adresse : {adresse}")
        if (tel := telephone(r["telephone"])):
            texte.append(f"Téléphone : {tel}")
        if (horaires := _texte(r["horaires"])):
            texte.append(f"Horaires : {horaires}")
        if ouverture:
            texte.append(f"Ouverture : {OUVERTURES[ouverture]}")
        fiches.append(_fiche(
            f"pharma:{r['id']}", "pharmacie", "\n".join(texte),
            nom=nom, nom_ar=nom_ar, ville=ville, ouverture=ouverture,
            latitude=float(r["latitude"]) if pd.notna(r["latitude"]) else None,
            longitude=float(r["longitude"]) if pd.notna(r["longitude"]) else None,
            precision_gps=_texte(r["precision_gps"]),
        ))
    return fiches


# --- conseil symptomes ------------------------------------------------------

def fiches_conseil() -> list[dict]:
    """Une fiche par symptome de la liste blanche (un symptome peut avoir
    plusieurs molecules : une ligne du CSV par molecule)."""
    if not SYMPTOMES_PATH.exists():
        return []
    df = pd.read_csv(SYMPTOMES_PATH, encoding="utf-8-sig")
    fiches = []
    for id_, lignes in df.groupby("id", sort=False):
        ref = lignes.iloc[0]
        # "CETIRIZINE (DICHLORHYDRATE)|CETIRIZINE" : plusieurs ecritures de la
        # meme molecule, on affiche la premiere. Seulement si elle est en vente.
        molecules = [d.split("|")[0].strip() for d in lignes["dci"].dropna().astype(str)
                     if d.strip() and commercialisee(d)]

        texte = [f"Symptôme : {ref['description']}"]
        if molecules:
            texte.append("Molécule à demander au pharmacien : " + " ou ".join(molecules))
        if pd.notna(ref["duree_max_jours"]):
            texte.append(f"Si le symptôme dure plus de {int(ref['duree_max_jours'])} jours : "
                         "consulter un médecin")
        if (signes := _texte(ref["signes_alerte"])):
            texte.append(f"Signes d'alerte (consulter un médecin sans attendre) : {signes}")
        if (orientation := _texte(ref["orientation"])):
            texte.append(f"À qui s'adresser : {orientation.lower()}")
        if (remarque := _texte(ref["remarque"])):
            texte.append(f"Remarque : {remarque}")
        texte.append("Enfant, bébé ou femme enceinte : ne citer aucune molécule, "
                     "orienter vers un médecin ou un pharmacien.")
        fiches.append(_fiche(f"conseil:{id_}", "conseil", "\n".join(texte), symptome=str(id_)))
    return fiches


def toutes_les_fiches() -> list[dict]:
    return fiches_medicaments() + fiches_notices() + fiches_pharmacies() + fiches_conseil()


def main():
    fiches = toutes_les_fiches()
    FICHES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FICHES_PATH.open("w", encoding="utf-8") as f:
        for fiche in fiches:
            f.write(json.dumps(fiche, ensure_ascii=False) + "\n")
    print(f"{len(fiches)} fiches ecrites dans {FICHES_PATH}")
    for type_, combien in Counter(fiche["type"] for fiche in fiches).items():
        print(f"  {type_:<11} {combien}")


if __name__ == "__main__":
    main()
