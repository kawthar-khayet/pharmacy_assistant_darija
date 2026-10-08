"""Outil conseil : quoi demander au pharmacien pour un symptome courant et benin.

Liste blanche data/clean/conseil_symptomes.csv, ecrite a la main (a faire
relire par un pharmacien) : le LLM ne cite jamais de medicament, il ne fait
que reconnaitre le symptome. Ici :
  - enfant, bebe ou grossesse -> un professionnel, sans molecule ;
  - symptome qui dure plus que duree_max_jours -> un medecin ;
  - sinon la molecule de la liste (correspondance EXACTE de la DCI), seulement
    si elle est commercialisee au Maroc sous une forme non injectable. On ne
    cite pas de marque : les moins chers etaient parfois hors sujet (une
    preparation pour coloscopie pour une constipation) ; le pharmacien choisit
    le produit ;
  - le professionnel de la colonne orientation est toujours cite.
Comme les autres outils, on renvoie des donnees ; le composeur redige.
"""
import re
from functools import lru_cache

import pandas as pd

from nlp.analyse.analyseur import SYMPTOMES_PATH
from nlp.linking.medicaments import STATUTS_EN_OFFICINE
from nlp.outils.resolution import matcher

_ARABE = re.compile(r"[؀-ۿ]")


def _texte(x) -> str | None:
    return None if pd.isna(x) or not str(x).strip() else str(x).strip()


def libelles(description: str) -> dict:
    """"Fièvre légère (skhana khfifa, سخانة خفيفة)" -> le libelle dans chaque langue.

    La parenthese porte la darija latine et la darija en lettres arabes ; le
    francais est ce qui la precede. Une langue absente retombe sur le francais.
    """
    m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", description or "")
    francais = (m.group(1) if m else description or "").strip()
    latin, arabe = [], []
    for morceau in (m.group(2).split(",") if m else []):
        morceau = morceau.strip()
        if morceau:
            (arabe if _ARABE.search(morceau) else latin).append(morceau)
    darija_lat = ", ".join(latin) or francais
    darija_ar = "، ".join(arabe) or francais
    return {"fr": francais, "ary_lat": darija_lat, "ary_ar": darija_ar, "ar": darija_ar}


@lru_cache(maxsize=1)
def _liste() -> dict[str, list[dict]]:
    """id -> lignes du CSV (un symptome peut avoir plusieurs molecules)."""
    if not SYMPTOMES_PATH.exists():
        return {}
    df = pd.read_csv(SYMPTOMES_PATH, encoding="utf-8-sig")
    lignes: dict[str, list[dict]] = {}
    for r in df.to_dict("records"):
        if _texte(r.get("id")):
            lignes.setdefault(r["id"].strip(), []).append(r)
    return lignes


def commercialisee(dci: str) -> bool:
    """La molecule existe-t-elle en officine au Maroc, sous une forme non
    injectable, avec une DCI EXACTEMENT egale a une des ecritures donnees
    ("CETIRIZINE (DICHLORHYDRATE)|CETIRIZINE") ?"""
    ecritures = {e.strip().upper() for e in dci.split("|") if e.strip()}
    df = matcher().df
    lignes = df[df["dci"].fillna("").str.upper().isin(ecritures)]
    en_officine = (lignes["statut_commercialisation"].isna()
                   | lignes["statut_commercialisation"].isin(STATUTS_EN_OFFICINE))
    return bool((en_officine & (lignes["famille_forme"] != "injectable")).any())


def conseil(symptomes: list[str], patient: str = "inconnu", grossesse: str = "inconnu",
            duree_jours: int | None = None) -> dict:
    """statut : "professionnel" (enfant, bebe, grossesse) | "conseil".

    En "conseil", `symptomes` donne pour chacun :
      statut "molecule"  : une ou plusieurs molecules a demander au pharmacien ;
             "orientation" : pas de molecule dans la liste -> le professionnel ;
             "trop_long" : dure plus que duree_max_jours -> medecin ;
             "inconnu"   : hors de la liste -> pharmacien.
    """
    if grossesse == "oui" or patient in ("enfant", "bebe"):
        return {"statut": "professionnel", "raison": "grossesse" if grossesse == "oui" else patient}

    liste = _liste()
    resultats = []
    for ident in symptomes or ["autre"]:
        lignes = liste.get(ident)
        if not lignes:
            resultats.append({"id": ident, "statut": "inconnu", "orientation": "PHARMACIEN"})
            continue
        premiere = lignes[0]
        duree_max = min(int(l["duree_max_jours"]) for l in lignes if pd.notna(l.get("duree_max_jours")))
        commun = {
            "id": ident,
            "libelles": libelles(premiere.get("description") or ident),
            "duree_max_jours": duree_max,
            "orientation": (_texte(premiere.get("orientation")) or "PHARMACIEN").upper(),
            "signes_alerte": [s.strip() for s in (_texte(premiere.get("signes_alerte")) or "").split(";")
                              if s.strip()],
            "remarque": _texte(premiere.get("remarque")),
        }
        if duree_jours is not None and duree_jours > duree_max:
            resultats.append(commun | {"statut": "trop_long", "orientation": "MEDECIN"})
            continue
        molecules = []
        for l in lignes:
            dci = _texte(l.get("dci"))
            if dci and commercialisee(dci):
                molecules.append(dci.split("|")[0].strip())
        resultats.append(commun | {"statut": "molecule" if molecules else "orientation",
                                   "molecules": molecules})
    return {"statut": "conseil", "symptomes": resultats}
