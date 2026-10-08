"""Analyse d'un message : construit le prompt et appelle le LLM.

C'est le seul appel LLM du moteur. Le prompt est relu a chaque message :
pendant les tests, on peut modifier prompt.md, schema.json ou
conseil_symptomes.csv sans redemarrer le serveur. La reponse du LLM est
renvoyee telle quelle ; c'est validation.py qui la verifie.
"""
import csv
import json
from pathlib import Path

from nlp.config import DATA_CLEAN
from nlp.llm import ReponseLLM, appeler_llm

ICI = Path(__file__).resolve().parent
SCHEMA_PATH = ICI / "schema.json"
PROMPT_PATH = ICI / "prompt.md"
SYMPTOMES_PATH = DATA_CLEAN / "conseil_symptomes.csv"

# 3 echanges suffisent pour completer "f maarif" ; au-dela on paie des tokens
# pour rien et le modele risque de melanger avec une vieille demande.
HISTORIQUE_MAX = 6


def charger_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _liste(entrees: dict) -> str:
    return "\n".join(f"- {cle} : {texte}" for cle, texte in entrees.items())


def _demandes(demandes: dict) -> str:
    return "\n".join(
        f"- {cle} : {d['description']} (besoin : {', '.join(d['besoin']) or 'rien'})"
        for cle, d in demandes.items()
    )


def _symptomes() -> str:
    """Symptomes de conseil_symptomes.csv (colonnes obligatoires : id, description).

    Tant que le fichier n'existe pas, le modele ne connait aucun symptome et
    repond 'autre' : le bot oriente alors vers le pharmacien.
    """
    if not SYMPTOMES_PATH.exists():
        return "(aucun symptome configure pour l'instant : utilise toujours 'autre')"
    with SYMPTOMES_PATH.open(encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f))
    # si le fichier a plusieurs lignes par symptome (une par molecule par
    # exemple), le modele ne doit voir chaque symptome qu'une fois
    symptomes = {}
    for ligne in lignes:
        ident = (ligne.get("id") or "").strip()
        if ident:
            symptomes.setdefault(ident, (ligne.get("description") or "").strip())
    if not symptomes:
        return "(aucun symptome configure pour l'instant : utilise toujours 'autre')"
    return "\n".join(f"- {ident} : {desc}" for ident, desc in symptomes.items())


def construire_prompt(schema: dict | None = None) -> str:
    schema = schema or charger_schema()
    remplacements = {
        "{{SITUATIONS}}": _liste(schema["situations"]),
        "{{DEMANDES}}": _demandes(schema["demandes"]),
        "{{SYMPTOMES}}": _symptomes(),
        "{{FORMAT}}": _liste(schema["sortie"]["format"]),
    }
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    for repere, texte in remplacements.items():
        prompt = prompt.replace(repere, texte)
    return prompt


def analyser(message: str, historique: list[dict] | None = None) -> ReponseLLM:
    """Analyse le dernier message du patient, a la lumiere de la conversation.

    `historique` : messages precedents, du plus ancien au plus recent,
    [{"role": "user" | "assistant", "contenu": "..."}]. Leve LLMIndisponible
    (voir llm.py) si aucun fournisseur n'a pu repondre.
    """
    messages = list(historique or [])[-HISTORIQUE_MAX:]
    # Gemini refuse une conversation qui commence par un message du bot : la
    # coupe a HISTORIQUE_MAX peut tomber sur une reponse du bot, on la retire.
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "contenu": message})
    return appeler_llm(construire_prompt(), messages)
