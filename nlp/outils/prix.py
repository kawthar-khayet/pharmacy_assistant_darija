"""Prix public et remboursement (CNOPS / CNSS) des presentations d'un medicament.

Sert a ecrire les fiches du RAG (nlp/rag/fiches.py) : chaque presentation
porte son prix et le remboursement des deux regimes.
"""
import re

import pandas as pd

from nlp.linking.medicaments import normalize

REGIMES = ("cnops", "cnss")


def _valeur(x):
    """None pour une case vide (pandas la lit en NaN)."""
    return None if pd.isna(x) else x


def _forme_de_base(forme) -> str:
    """"COMPRIME EFFERVESCENT SECABLE" et "COMPRIME EFFERVESCENT" : meme produit
    pour le patient, seule la barre de secabilite change."""
    return re.sub(r"\s*\bSECABLES?\b", "", normalize(forme or "")).strip()


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
