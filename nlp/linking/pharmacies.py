"""Pharmacies citees par leur nom : "pharmacie Ibn Sina", "صيدلية النخيل".

Recherche approchee (RapidFuzz) dans data/clean/pharmacies_fusion.csv, pour
la demande info_pharmacie (adresse, telephone). Les lieux sont resolus dans
lieux.py ; la reponse est composee par outils/pharmacies.py.

Les noms d'officine se repetent beaucoup ("Ibn Sina", "Al Amal") : un nom
seul designe souvent des pharmacies de plusieurs villes. On ne choisit pas a
la place du patient : on rend la liste des villes pour la lui demander.
"""
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd
from rapidfuzz import fuzz, process

from nlp.linking.lieux import ARABIZI, _CHIFFRE_COLLE, _cle_arabe, _latin, charger_pharmacies
from nlp.linking.translitteration import cle_phonetique, contient_arabe, translitterer

# Score (0-100) : au-dessus de "trouve", on donne la fiche ; entre les deux,
# on demande confirmation ("tu parles de la pharmacie Al Amal ?").
SEUILS = {"trouve": 90, "a_confirmer": 70}

# WRatio, qui classe, prend le maximum de plusieurs comparaisons dont une
# partielle : un nom court presque inclus dans une longue saisie score haut
# sur du bruit ("ABID" dans "BIDON INEXISTANTE XYZ123" -> 77). Un mot au moins
# doit donc vraiment ressembler a un mot du nom ; plus encore sur la cle
# phonetique, qui ecrase des distinctions (p/b, s/z, i/e).
PLANCHER_MOT = 80
PLANCHER_MOT_PHON = 90

# Deux scores a moins de 3 points : meme nom (Ibn Sina a Rabat et a Fes).
ECART_HOMONYMES = 3

# "Pharmacie", "sidlia"... : en tete de presque tous les noms, ne distingue rien.
PREFIXE_LATIN = re.compile(
    r"^(LA |GRANDE |NOUVELLE )*"
    r"(PHARMACIE|PHARMA|SIDLIA|SIDLIYA|SIDALIA|SAIDALIA|SAIDALIYA|SAYDALIA|SAYDALIYA)\s+"
    r"(DE |DU |DES |D |L )?"
)
PREFIXES_ARABES = {"صيدليه", "فارماسي"}       # apres _cle_arabe : ة -> ه, article retire


def _texte(x) -> str:
    return "" if pd.isna(x) else str(x)


def _court_latin(nom: str) -> str:
    """"Pharmacie du Centre" -> "CENTRE"."""
    s = _latin(nom)
    return PREFIXE_LATIN.sub("", s).strip() or s


def _court_requete(texte: str) -> str:
    """Comme _court_latin, plus l'arabizi du patient ("sidlia l3afia")."""
    s = _CHIFFRE_COLLE.sub(lambda m: ARABIZI[m.group(0)], _latin(texte))
    return PREFIXE_LATIN.sub("", s).strip() or s


def _court_arabe(nom: str) -> str:
    """"صيدلية النخيل" -> "نخيل"."""
    mots = _cle_arabe(nom).split()
    if len(mots) > 1 and mots[0] in PREFIXES_ARABES:
        mots = mots[1:]
    return " ".join(mots)


@lru_cache(maxsize=1)
def _table() -> pd.DataFrame:
    df = charger_pharmacies().copy()
    noms, noms_ar = df["nom"].map(_texte), df["nom_ar"].map(_texte)
    # Une pharmacie OSM sans nom latin porte son nom arabe dans "nom".
    df["court"] = ["" if contient_arabe(n) else _court_latin(n) for n in noms]
    df["court_ar"] = [_court_arabe(a) if a else (_court_arabe(n) if contient_arabe(n) else "")
                      for n, a in zip(noms, noms_ar)]
    df["court_phon"] = df["court"].map(cle_phonetique)
    return df


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance a vol d'oiseau (formule de haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def fiche(r, pres_de: tuple[float, float] | None = None) -> dict:
    """Ce qu'on sait d'une pharmacie. Les cases vides deviennent None : un NaN
    produirait un JSON invalide cote API."""
    def v(x):
        return None if pd.isna(x) or x == "" else x

    f = {
        "nom": r["nom"], "nom_ar": v(r["nom_ar"]),
        "adresse": v(r["adresse"]), "telephone": v(r["telephone"]), "horaires": v(r["horaires"]),
        "ville": r["ville"],
        "latitude": None if pd.isna(r["latitude"]) else float(r["latitude"]),
        "longitude": None if pd.isna(r["longitude"]) else float(r["longitude"]),
        "precision_gps": v(r["precision_gps"]),
        "distance_km": None,
    }
    # Une position qui ne situe que la ville donnerait une distance fausse.
    if pres_de and r["position_fiable"]:
        f["distance_km"] = round(distance_km(*pres_de, r["latitude"], r["longitude"]), 1)
    return f


def _mots_utiles(texte: str) -> list[str]:
    """Les mots de 4 lettres ou plus : "IBN", "AL", "EL", "DAR" figurent dans
    des centaines de noms, et a eux seuls faisaient proposer Ibn Rochd a qui
    cherchait Ibn Sina. Un nom fait seulement de mots courts les garde."""
    mots = texte.split()
    return [m for m in mots if len(m) >= 4] or mots


def _meilleur_mot(a: str, b: str) -> float:
    """Ressemblance du meilleur couple de mots : sert de filtre, jamais a classer."""
    return max((fuzz.ratio(x, y) for x in _mots_utiles(a) for y in _mots_utiles(b)), default=0.0)


def _passe(requete: str, cles: pd.Series, plancher: int, facteur: float = 1.0) -> dict:
    """Score de chaque ligne de `cles` assez proche de `requete` (index -> score)."""
    if not requete:
        return {}
    trouves = {}
    for cle, score, label in process.extract(requete, cles, scorer=fuzz.WRatio,
                                             score_cutoff=SEUILS["a_confirmer"], limit=None):
        score *= facteur
        if score >= SEUILS["a_confirmer"] and _meilleur_mot(requete, cle) >= plancher:
            trouves[label] = score
    return trouves


@dataclass
class RechercheNom:
    cite: str                                   # tel qu'ecrit par le patient
    statut: str = "introuvable"                 # "trouve" | "a_confirmer" | "ambigu" | "introuvable"
    nom: str | None = None                      # nom retenu, pour le redire
    ville: str | None = None                    # ville ou l'on a cherche, si connue
    pharmacies: list[dict] = field(default_factory=list)       # fiches, la meilleure d'abord
    villes_possibles: list[str] = field(default_factory=list)  # si ambigu


def chercher_pharmacie(nom: str, ville: str | None = None,
                       pres_de: tuple[float, float] | None = None,
                       ville_connue: str | None = None) -> RechercheNom:
    """Pharmacie(s) portant ce nom.

    ville        : ville du lieu cite dans le message ; on ne cherche que la.
    pres_de      : (latitude, longitude) du quartier cite ; la plus proche d'abord.
    ville_connue : ville d'un message precedent, pour departager des homonymes.
    """
    resultat = RechercheNom(cite=nom, ville=ville)
    if not nom or not nom.strip():
        return resultat
    t = _table()
    pool = t[t["ville"] == ville] if ville else t

    # Arabe d'abord ; a defaut, translitteration et cle phonetique sur le latin.
    scores = {}
    latin = nom
    if contient_arabe(nom):
        scores = _passe(_court_arabe(nom), pool["court_ar"], PLANCHER_MOT)
        latin = translitterer(nom)
    if not scores:
        court = _court_requete(latin)
        scores = _passe(court, pool["court"], PLANCHER_MOT)
        for label, s in _passe(cle_phonetique(court), pool["court_phon"],
                               PLANCHER_MOT_PHON, facteur=0.95).items():
            scores[label] = max(s, scores.get(label, 0.0))
    if not scores:
        return resultat

    meilleur = max(scores.values())
    resultat.statut = "trouve" if meilleur >= SEUILS["trouve"] else "a_confirmer"
    labels = [l for l, s in scores.items() if s >= meilleur - ECART_HOMONYMES]
    retenues = pool.loc[labels].assign(_score=[scores[l] for l in labels])
    retenues = retenues.sort_values("_score", ascending=False)

    if not ville:
        villes = sorted(retenues["ville"].unique())
        if ville_connue in villes:
            retenues = retenues[retenues["ville"] == ville_connue]
            resultat.ville = ville_connue
        elif len(villes) > 1:
            resultat.statut = "ambigu"
            resultat.nom = retenues["nom"].iloc[0]
            resultat.villes_possibles = villes
            return resultat

    fiches = [fiche(r, pres_de) | {"score": round(float(r["_score"]), 1)}
              for _, r in retenues.iterrows()]
    if pres_de:
        fiches.sort(key=lambda f: (f["distance_km"] is None, f["distance_km"] or 0.0))
    resultat.pharmacies = fiches
    resultat.nom = fiches[0]["nom"]
    return resultat
