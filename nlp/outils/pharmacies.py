"""Outil pharmacies : pharmacies d'un lieu, de garde, ou citees par leur nom.

Trois demandes de l'analyse :
  pharmacies_lieu -> les 5 plus proches du quartier cite ;
  pharmacie_garde -> les ouvertes 24h/24 ou la nuit, dans la ville du lieu ;
  info_pharmacie  -> adresse et telephone d'une pharmacie citee par son nom.

Comme prix.py, on renvoie des donnees avec un statut ; c'est le composeur qui
redige. DwaTalk ne connait aucun tour de garde, seulement les pharmacies dont
les horaires disent 24h/24 ou nuit : le composeur doit le dire au patient.
"""
import re

import pandas as pd

from nlp.linking.lieux import Lieu, charger_pharmacies
from nlp.linking.pharmacies import chercher_pharmacie, distance_km, fiche

MAX_PROCHES = 5
# Petite ville : on liste toutes ses pharmacies ; au-dela, on demande le quartier.
MAX_LISTE_VILLE = 5
# Plusieurs pharmacies du meme nom dans une ville : on en montre au plus 3.
MAX_HOMONYMES_VILLE = 3

_H24 = re.compile(r"24\s*H?\s*/\s*24|24\s*/\s*7", re.IGNORECASE)
_PLAGE = re.compile(r"^(\d{1,2})\s*H\s*A\s*(\d{1,2})\s*H$", re.IGNORECASE)


def type_ouverture(horaires) -> str | None:
    """"24h" (garde 24h/24, 24/7), "nuit" (00H A 09H, 23H A 09H) ou None.

    Une pharmacie de nuit commence au plus tot a 20h et ferme au plus tard a
    10h ; "09H A 00H" ferme tard mais n'est pas une pharmacie de nuit."""
    if not isinstance(horaires, str):
        return None
    if _H24.search(horaires):
        return "24h"
    m = _PLAGE.match(horaires.strip())
    if m:
        debut, fin = int(m[1]), int(m[2])
        if (debut >= 20 or debut == 0) and fin <= 10:
            return "nuit"
    return None


def _question_lieu(lieu: Lieu | None) -> dict | None:
    """Ce qu'il faut demander au patient avant de chercher, ou None."""
    if lieu is None or lieu.statut == "introuvable":
        return {"statut": "lieu_inconnu", "cite": lieu.cite if lieu else None}
    if lieu.statut == "ambigu":
        return {"statut": "preciser_ville", "lieu": lieu.nom, "villes": lieu.villes_possibles}
    return None


def _pres_de(lieu: Lieu) -> tuple[float, float] | None:
    """Seul un quartier donne un point utile ; le centre d'une ville, non."""
    return (lieu.latitude, lieu.longitude) if lieu.statut == "quartier" else None


def _dans_ville(ville: str) -> pd.DataFrame:
    df = charger_pharmacies()
    return df[df["ville"] == ville]


def plus_proches(latitude: float, longitude: float, combien: int = MAX_PROCHES) -> list[dict]:
    """Les pharmacies les plus proches d'un point, toutes communes confondues :
    un quartier en limite de ville a souvent sa pharmacie la plus proche de
    l'autre cote. Positions fiables seulement : un point qui ne situe que la
    ville fausserait la distance."""
    df = charger_pharmacies()
    fiables = df[df["position_fiable"]]
    distances = [distance_km(latitude, longitude, la, lo)
                 for la, lo in zip(fiables["latitude"], fiables["longitude"])]
    proches = fiables.assign(_distance=distances).nsmallest(combien, "_distance")
    return [fiche(r, (latitude, longitude)) for _, r in proches.iterrows()]


def pharmacies_lieu(lieu: Lieu | None) -> dict:
    """Les pharmacies les plus proches du quartier, ou celles d'une petite ville."""
    if (question := _question_lieu(lieu)):
        return question

    if lieu.statut == "ville":
        dans_ville = _dans_ville(lieu.ville)
        if len(dans_ville) > MAX_LISTE_VILLE:
            return {"statut": "preciser_quartier", "ville": lieu.ville,
                    "nb_pharmacies": len(dans_ville), "quartier_inconnu": lieu.quartier_inconnu}
        return {"statut": "trouve", "lieu": lieu.ville, "ville": lieu.ville,
                "quartier_inconnu": lieu.quartier_inconnu,
                "pharmacies": [fiche(r) for _, r in dans_ville.sort_values("nom").iterrows()]}

    return {"statut": "trouve", "lieu": lieu.nom, "ville": lieu.ville,
            "source_lieu": lieu.source,      # "adresses" : quartier situe par l'annuaire, moins precis
            "pharmacies": plus_proches(lieu.latitude, lieu.longitude)}


def pharmacie_garde(lieu: Lieu | None) -> dict:
    """Pharmacies ouvertes 24h/24 ou la nuit, dans la ville du lieu."""
    if (question := _question_lieu(lieu)):
        return question

    pres_de = _pres_de(lieu)
    dans_ville = _dans_ville(lieu.ville)
    ouvertes = dans_ville[dans_ville["horaires"].map(type_ouverture).notna()]
    fiches = [fiche(r, pres_de) | {"ouverture": type_ouverture(r["horaires"])}
              for _, r in ouvertes.iterrows()]
    if pres_de:
        fiches.sort(key=lambda f: (f["distance_km"] is None, f["distance_km"] or 0.0))
    return {"statut": "trouve" if fiches else "aucune",
            "lieu": lieu.nom, "ville": lieu.ville,
            "pharmacies": fiches[:MAX_PROCHES],
            "tour_de_garde_connu": False}    # toujours : a dire au patient


def info_pharmacie(nom: str, lieu: Lieu | None = None, ville_connue: str | None = None) -> dict:
    """Adresse, telephone et horaires d'une pharmacie citee par son nom.

    Avec un lieu, on ne cherche que dans sa ville (la plus proche d'abord) ;
    sans lieu, un nom present dans plusieurs villes fait demander laquelle.
    """
    if lieu is not None and lieu.statut == "ambigu":
        return {"statut": "preciser_ville", "lieu": lieu.nom, "villes": lieu.villes_possibles}

    ville = lieu.ville if lieu is not None and lieu.statut in ("quartier", "ville") else None
    pres_de = _pres_de(lieu) if ville else None
    r = chercher_pharmacie(nom, ville=ville, pres_de=pres_de, ville_connue=ville_connue)

    base = {"cite": nom, "nom": r.nom, "ville": r.ville,
            # lieu cite mais non reconnu : on a cherche le nom dans tout le pays
            "lieu_inconnu": lieu is not None and lieu.statut == "introuvable"}
    if r.statut == "ambigu":
        return base | {"statut": "preciser_ville", "villes": r.villes_possibles}
    if r.statut == "introuvable":
        return base | {"statut": "introuvable"}
    return base | {"statut": r.statut,       # "trouve" | "a_confirmer"
                   "pharmacies": r.pharmacies[:MAX_HOMONYMES_VILLE],
                   "nb_trouvees": len(r.pharmacies)}
