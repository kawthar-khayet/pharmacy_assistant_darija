"""Donnees complementaires pour les pages de l'interface : securite et classification ATC.

  - la securite (notice officielle) vient de nlp/outils/securite.py, la meme
    source que celle du bot ;
  - data/clean/dci_atc.csv donne la classification therapeutique.

Tout est charge en memoire au premier appel. Un fichier absent n'est pas une
erreur : l'API demarre et repond simplement qu'elle n'a pas l'information.
"""
from pathlib import Path

import pandas as pd

from nlp.outils.securite import fiche_securite

RACINE = Path(__file__).resolve().parent.parent
ATC_PATH = RACINE / "data" / "clean" / "dci_atc.csv"

_atc: dict | None = None


def securite(dci: str | None) -> dict | None:
    """Les rubriques de la notice d'une molecule, ou None si elle n'est pas couverte."""
    return fiche_securite(dci)


def _table_atc() -> dict:
    global _atc
    if _atc is None:
        _atc = {}
        if ATC_PATH.exists():
            table = pd.read_csv(ATC_PATH)
            for _, ligne in table[table["code_atc"].notna()].iterrows():
                classes = _atc.setdefault(str(ligne["dci"]).upper(), [])
                classe = {"code": ligne["code_atc"], "groupe": ligne["groupe_atc"],
                          "libelle": ligne["libelle_atc"]}
                if classe not in classes:
                    classes.append(classe)
    return _atc


def classes_atc(dci: str | None) -> list[dict]:
    """Les classes ATC d'une molecule. Plusieurs codes est la regle (voie orale
    et voie topique n'ont pas la meme classe) : l'interface les affiche toutes."""
    if not dci:
        return []
    return _table_atc().get(str(dci).upper(), [])
