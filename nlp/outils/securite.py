"""La notice officielle d'une molecule, rubrique par rubrique.

Source : data/clean/securite_medicaments.csv, le texte de la notice francaise
(BDPM), mot pour mot. Six rubriques : indications, effets_indesirables,
contre_indications, precautions, interactions, grossesse_allaitement.

Sert a ecrire les fiches du RAG (nlp/rag/fiches.py) et a la page Medicaments
(api/donnees.py). Les deux fichiers JSON sont les resumes pre-calcules de cette
page (api/resume.py).
"""
import math
import re
from functools import lru_cache

import pandas as pd

from nlp.config import DATA_CLEAN

SECURITE_PATH = DATA_CLEAN / "securite_medicaments.csv"
RESUMES_PATH = DATA_CLEAN / "securite_resumes.json"          # page Medicaments (api/resume.py)
EXPLICATIONS_PATH = DATA_CLEAN / "securite_explications.json"

# Rubriques de la notice = colonnes du CSV.
RUBRIQUES = ("indications", "effets_indesirables", "contre_indications",
             "precautions", "interactions", "grossesse_allaitement")

# Separateurs des DCI composees ("AMOXICILLINE / ACIDE CLAVULANIQUE").
SEPARATEURS = re.compile(r"\s*//\s*|\s*/\s*")

# Fin de la rubrique des effets indesirables des notices francaises : un renvoi
# vers la pharmacovigilance FRANCAISE, qui enverrait un patient marocain
# declarer au mauvais pays. On coupe, on ne reecrit jamais le texte medical.
DECLARATION_FRANCE = re.compile(
    r"\n\s*(D[ée]claration des effets secondaires|Si vous ressentez un quelconque effet ind[ée]sirable,"
    r" parlez-en)", re.IGNORECASE
)


def nettoyer(texte) -> str | None:
    """Sans puces, sans lignes vides, sans le renvoi a la pharmacovigilance francaise."""
    if texte is None or (isinstance(texte, float) and math.isnan(texte)):
        return None
    texte = str(texte)
    coupure = DECLARATION_FRANCE.search(texte)
    if coupure:
        texte = texte[: coupure.start()]
    lignes = [l.strip(" \t·•") for l in texte.splitlines()]
    return "\n".join(l for l in lignes if l) or None


@lru_cache(maxsize=1)
def _table() -> dict:
    """DCI en majuscules -> ligne du CSV. Fichier absent : rien n'est couvert."""
    if not SECURITE_PATH.exists():
        return {}
    df = pd.read_csv(SECURITE_PATH)
    return {str(l["dci"]).upper(): l for l in df.to_dict("records")}


def fiche_securite(dci: str | None) -> dict | None:
    """Toutes les rubriques d'une molecule, ou None si elle n'est pas couverte.

    On cherche la DCI complete, puis chacun de ses principes actifs : une
    association peut manquer alors que ses composants sont documentes.
    """
    if not dci:
        return None
    table = _table()
    cles = [str(dci).upper()] + [p.strip().upper() for p in SEPARATEURS.split(str(dci)) if p.strip()]
    for cle in cles:
        ligne = table.get(cle)
        if ligne is None:
            continue
        rubriques = {r: t for r in RUBRIQUES if (t := nettoyer(ligne.get(r)))}
        if not rubriques:
            continue
        atc = ligne.get("code_atc_notice")
        return {
            "dci": ligne["dci"],
            # la specialite francaise dont on cite la notice : pas la boite marocaine
            "specialite_source": ligne.get("specialite_bdpm"),
            "code_atc": atc if isinstance(atc, str) else None,
            "rubriques": rubriques,
            "source_url": ligne.get("source_url"),
            "date_recuperation": ligne.get("date_recuperation"),
        }
    return None
