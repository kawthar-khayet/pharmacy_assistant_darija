"""Outil securite : ce que dit la notice officielle d'une molecule.

Six demandes de l'analyse, une par rubrique de la notice : indications,
effets_indesirables, contre_indications, precautions, interactions,
grossesse_allaitement.

Sources, preparees a froid (aucun appel LLM pendant la conversation) :
  data/clean/securite_medicaments.csv   texte de la notice francaise (BDPM), mot pour mot
  data/clean/securite_explications.json explications simples par rubrique et par langue,
                                        calculees par scripts/precalculer_resumes.py --explications

Le chat ne montre que l'explication simple, dans la langue du patient ; le
texte officiel francais part dans le volet sous la reponse. On ne renvoie que
les rubriques demandees, jamais toute la fiche.
"""
import json
import math
import re
from functools import lru_cache

import pandas as pd
from rapidfuzz import fuzz

from nlp.config import DATA_CLEAN
from nlp.linking.medicaments import normalize
from nlp.outils.resolution import MedicamentResolu

SECURITE_PATH = DATA_CLEAN / "securite_medicaments.csv"
RESUMES_PATH = DATA_CLEAN / "securite_resumes.json"          # page Medicaments (api/resume.py)
EXPLICATIONS_PATH = DATA_CLEAN / "securite_explications.json"

# Demande de l'analyse -> colonne du CSV (memes noms).
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


@lru_cache(maxsize=1)
def _explications() -> dict:
    """"DCI|langue" -> {rubrique: explication}. Fichier absent : aucune."""
    if not EXPLICATIONS_PATH.exists():
        return {}
    try:
        return json.loads(EXPLICATIONS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


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


def _dci(resolu: MedicamentResolu) -> str | None:
    for v in resolu.variantes:
        dci = v.get("dci")
        if isinstance(dci, str) and dci.strip():
            return dci
    return None


def _nom_affiche(resolu: MedicamentResolu, dci: str) -> str:
    """"ibuprofene" cite par le patient : on parle de la molecule, pas de la
    premiere marque qui la contient (IBUPROFENE B-BRAUN, une perfusion)."""
    if fuzz.ratio(normalize(resolu.cite.nom), normalize(dci)) >= 85:
        return dci
    return resolu.nom


def securite(resolu: MedicamentResolu, demandes: list[str], langue: str) -> dict:
    """Rubriques demandees de la notice d'un medicament resolu.

    statut : "trouve" | "a_confirmer" | "pas_d_info" | "introuvable".
    """
    if resolu.statut == "introuvable":
        return {"statut": "introuvable", "cite": resolu.cite.nom}
    base = {"nom": resolu.nom, "autres": resolu.autres}
    fiche = fiche_securite(_dci(resolu))
    if fiche is None:
        return base | {"statut": "pas_d_info"}

    demandees = [d for d in demandes if d in RUBRIQUES]
    rubriques = {d: fiche["rubriques"][d] for d in demandees if d in fiche["rubriques"]}
    explications = _explications().get(f"{fiche['dci']}|{langue}", {})
    return base | {
        "nom": _nom_affiche(resolu, fiche["dci"]),
        "statut": resolu.statut if rubriques else "pas_d_info",
        "dci": fiche["dci"],
        "rubriques": rubriques,                    # texte officiel, pour le volet sous la reponse
        "explications": {d: explications[d] for d in rubriques if d in explications},
        "manquantes": [d for d in demandees if d not in rubriques],
        "specialite_source": fiche["specialite_source"],
        "source_url": fiche["source_url"],
    }
