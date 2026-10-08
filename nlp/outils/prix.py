"""Outil prix : prix public et remboursement (CNOPS / CNSS) d'un medicament.

Renvoie le prix et le remboursement des deux regimes ; c'est le composeur qui
n'affiche que ce que le patient a demande, et seulement pour SON regime (un
patient n'est adherent qu'a un seul).
"""
import re

import pandas as pd

from nlp.linking.medicaments import STATUTS_EN_OFFICINE, dose_mg, filtrer_dosage, normalize
from nlp.outils.resolution import MedicamentResolu, matcher

# Au-dela, une liste de prix est illisible dans un chat : on donne un prix par
# dosage (le plus bas et le plus haut des formes) au lieu de chaque forme.
MAX_PRESENTATIONS = 3
MAX_DOSAGES = 6
REGIMES = ("cnops", "cnss")


def _valeur(x):
    """None pour une case vide (pandas la lit en NaN)."""
    return None if pd.isna(x) else x


def _forme_de_base(forme) -> str:
    """"COMPRIME EFFERVESCENT SECABLE" et "COMPRIME EFFERVESCENT" : meme produit
    pour le patient, seule la barre de secabilite change."""
    return re.sub(r"\s*\bSECABLES?\b", "", normalize(forme or "")).strip()


def lignes_du_produit(resolu: MedicamentResolu, filtrer_forme: bool = True) -> pd.DataFrame:
    """Toutes les lignes du produit (le matcher n'en garde que 5), filtrees par
    le dosage et la forme donnes par le patient quand il y en a.

    `filtrer_forme=False` : pour lister les formes, on garde toutes celles du
    dosage demande (medicament.py dit ensuite si la forme demandee existe)."""
    df = matcher().df
    lignes = df[df["nom_norm"] == normalize(resolu.nom)]
    if resolu.cite.dosage:
        filtrees = filtrer_dosage(lignes, resolu.cite.dosage)
        if len(filtrees):
            lignes = filtrees
    if resolu.cite.forme and filtrer_forme:
        cle = normalize(resolu.cite.forme)
        filtrees = lignes[lignes["forme"].fillna("").apply(normalize).str.contains(re.escape(cle))]
        if len(filtrees):
            lignes = filtrees
    # Retire ou suspendu : plus de prix utile. Une ligne sans statut vient des
    # listes CNOPS / CNSS actuelles et reste valable.
    en_officine = (lignes["statut_commercialisation"].isna()
                   | lignes["statut_commercialisation"].isin(STATUTS_EN_OFFICINE))
    return lignes[en_officine]


def _remboursement(groupe: pd.DataFrame, voisins: pd.DataFrame, regime: str) -> dict | None:
    """Taux, base et montant rembourse pour un regime, ou None si inconnu.

    Le montant se calcule sur la BASE de remboursement du regime, pas sur le
    prix public. Base inconnue -> montant None : on ne le devine pas.
    """
    col_taux = f"taux_remboursement_{regime}"
    col_base = f"prix_base_remboursement_{regime}"
    # pas de taux dans ce groupe : celui d'une forme voisine de meme dosage
    # (meme famille, ex. un autre comprime) vaut pour le patient
    for lignes in (groupe, voisins):
        avec_taux = lignes[lignes[col_taux].notna()]
        if len(avec_taux):
            ligne = avec_taux.iloc[0]
            taux = float(ligne[col_taux])
            base = float(ligne[col_base]) if pd.notna(ligne[col_base]) else None
            return {
                "taux": taux,          # 0 = sur la liste mais non rembourse
                "base": base,
                "montant": round(base * taux / 100, 2) if base is not None else None,
            }
    return None


def presentations(lignes: pd.DataFrame) -> list[dict]:
    """Regroupe les lignes d'un meme produit : la base eclate une presentation
    selon la source (le prix vient de l'AMMPS, les taux de la CNOPS / CNSS)."""
    lignes = lignes.assign(_forme_base=lignes["forme"].apply(_forme_de_base))
    presentations = []
    for (dosage_cle, _), groupe in lignes.groupby(["dosage_cle", "_forme_base"], sort=False):
        avec_prix = groupe[groupe["ppv"].notna()].sort_values("ppv")
        ref = avec_prix.iloc[0] if len(avec_prix) else groupe.iloc[0]
        voisins = lignes[(lignes["dosage_cle"] == dosage_cle)
                         & (lignes["famille_forme"] == ref["famille_forme"])]
        presentations.append({
            "dosage": _valeur(ref["dosage"]),
            "forme": _valeur(ref["forme"]),
            "ppv": float(ref["ppv"]) if pd.notna(ref["ppv"]) else None,
            **{regime: _remboursement(groupe, voisins, regime) for regime in REGIMES},
        })
    return _fusionner_sources(presentations)


def _fusionner_sources(presentations: list[dict]) -> list[dict]:
    """L'AMMPS (prix) et la CNOPS / CNSS (taux) ne nomment pas toujours la forme
    pareil : "SACHET" d'un cote, "POUDRE POUR SOLUTION BUVABLE" de l'autre, pour
    le meme produit. A dosage egal, une seule presentation avec prix sans taux
    et une seule avec taux sans prix sont donc la meme : on les reunit."""
    def sans_taux(p):
        return p["ppv"] is not None and not any(p[r] for r in REGIMES)

    def sans_prix(p):
        return p["ppv"] is None and any(p[r] for r in REGIMES)

    for dosage in {p["dosage"] for p in presentations}:
        meme_dosage = [p for p in presentations if p["dosage"] == dosage]
        avec_prix = [p for p in meme_dosage if sans_taux(p)]
        avec_taux = [p for p in meme_dosage if sans_prix(p)]
        if len(avec_prix) == 1 and len(avec_taux) == 1:
            for regime in REGIMES:
                avec_prix[0][regime] = avec_taux[0][regime]
            presentations.remove(avec_taux[0])
    return presentations


def _taux_commun(presentations: list[dict], regime: str) -> float | None:
    """Le taux du regime s'il est le meme pour toutes les presentations (cas le
    plus frequent) : on peut alors le dire en une fois, sans lister."""
    taux = {p[regime]["taux"] if p[regime] else None for p in presentations}
    return taux.pop() if len(taux) == 1 else None


def _prix_par_dosage(presentations: list[dict]) -> list[dict]:
    """Prix le plus bas et le plus haut de chaque dosage, du plus faible au plus fort."""
    par_dosage: dict = {}
    for p in presentations:
        if p["ppv"] is not None:
            par_dosage.setdefault(p["dosage"], []).append(p["ppv"])
    ordre = sorted(par_dosage.items(), key=lambda kv: dose_mg(kv[0]) or float("inf"))
    return [{"dosage": d, "prix_min": min(v), "prix_max": max(v)} for d, v in ordre]


def prix(resolu: MedicamentResolu) -> dict:
    """Prix et remboursement (CNOPS et CNSS) d'un medicament resolu.

    statut : "trouve" | "a_confirmer" | "introuvable" | "plus_commercialise".
    Sans dosage connu et avec plus de MAX_PRESENTATIONS presentations,
    `presentations` est vide : seuls le prix par dosage et les taux communs
    sont donnes. `dosage_absent` : le dosage cite tel quel s'il n'est pas en vente.
    """
    if resolu.statut == "introuvable":
        return {"statut": "introuvable", "cite": resolu.cite.nom}

    lignes = lignes_du_produit(resolu)
    trouvees = presentations(lignes)
    if not trouvees:
        return {"statut": "plus_commercialise", "nom": resolu.nom}

    # dosage cite mais pas en vente : lignes_du_produit a garde tous les dosages
    dosage_absent = bool(resolu.cite.dosage) and filtrer_dosage(lignes, resolu.cite.dosage).empty
    # dosage trouve : quelques formes au plus, on les liste toutes
    trop = len(trouvees) > MAX_PRESENTATIONS and (not resolu.cite.dosage or dosage_absent)
    par_dosage = _prix_par_dosage(trouvees)
    return {
        "statut": resolu.statut,
        "nom": resolu.nom,
        "autres": resolu.autres,
        "presentations": [] if trop else trouvees,
        "trop_de_presentations": trop,
        "dosage_absent": resolu.cite.dosage if dosage_absent else None,
        "par_dosage": par_dosage[:MAX_DOSAGES],
        "dosages_coupes": len(par_dosage) > MAX_DOSAGES,
        "taux_commun": {regime: _taux_commun(trouvees, regime) for regime in REGIMES},
    }
