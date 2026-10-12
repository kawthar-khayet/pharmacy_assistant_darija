"""Comprehension : le premier des deux appels LLM d'un message.

Le LLM lit le message (et la conversation) et dit quoi chercher : les
medicaments et le lieu cites, la pharmacie voulue, le symptome decrit (choisi
dans la liste blanche) et la question reformulee en francais (la recherche par
le sens comprend mal la darija). C'est lui qui
decide de la recherche ; recherche.py l'execute dans nos donnees.

Le prompt est relu a chaque message : on peut modifier comprendre.md pendant
les tests sans redemarrer le serveur.
"""
import csv
from dataclasses import dataclass
from pathlib import Path

from nlp.llm import appeler_llm
from nlp.rag.fiches import SYMPTOMES_PATH
from nlp.rag.recherche import Requete

PROMPT_PATH = Path(__file__).resolve().parent / "comprendre.md"

# 3 echanges suffisent pour completer "f maarif" ; au-dela on paie des tokens
# pour rien et le modele risque de melanger avec une vieille demande.
HISTORIQUE_MAX = 6
URGENCES = {"intoxication", "detresse"}


@dataclass
class Compris:
    requete: Requete
    urgence: str | None      # "intoxication" | "detresse" : le bot ne donne que les numeros
    fournisseur: str         # qui a repondu, pour le debogage


def _texte(x) -> str | None:
    return x.strip() if isinstance(x, str) and x.strip() else None


def symptomes_connus() -> dict[str, str]:
    """Identifiant -> description des symptomes de la liste blanche. Relu a
    chaque message, comme le prompt : la liste se modifie sans redemarrage."""
    if not SYMPTOMES_PATH.exists():
        return {}
    with SYMPTOMES_PATH.open(encoding="utf-8-sig", newline="") as f:
        return {l["id"].strip(): (l.get("description") or "").strip() for l in csv.DictReader(f) if l.get("id")}


def construire_prompt() -> str:
    liste = "\n".join(f"- {ident} : {description}" for ident, description in symptomes_connus().items())
    return PROMPT_PATH.read_text(encoding="utf-8").replace(
        "{{SYMPTOMES}}", liste or "(aucun symptôme configuré : laisse la liste vide)")


def en_requete(donnees: dict, message: str) -> Requete:
    """Le JSON du LLM, verifie champ par champ : un champ absent ou mal forme
    prend sa valeur par defaut au lieu de faire echouer la reponse."""
    medicaments = donnees.get("medicaments")
    if not isinstance(medicaments, list):
        medicaments = []
    # un symptome invente par le LLM n'a pas de fiche : on ne garde que ceux de la liste
    connus = symptomes_connus()
    symptomes = donnees.get("symptomes")
    symptomes = [s for s in symptomes if s in connus] if isinstance(symptomes, list) else []
    return Requete(
        # sans reformulation, on cherche avec le message tel quel
        question=_texte(donnees.get("question")) or message,
        medicaments=[m for x in medicaments if (m := _texte(x))],
        lieu=_texte(donnees.get("lieu")),
        pharmacie=_texte(donnees.get("pharmacie")),
        pharmacies=donnees.get("pharmacies") is True,
        garde=donnees.get("garde") is True,
        symptomes=list(dict.fromkeys(symptomes)),
    )


def conversation(historique: list[dict] | None) -> list[dict]:
    """Les derniers messages de la conversation, tels qu'on les envoie au LLM."""
    messages = list(historique or [])[-HISTORIQUE_MAX:]
    # Gemini refuse une conversation qui commence par un message du bot : la
    # coupe a HISTORIQUE_MAX peut tomber sur une reponse du bot, on la retire.
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    return messages


def comprendre(message: str, historique: list[dict] | None = None) -> Compris:
    """Ce qu'il faut chercher pour le dernier message du patient.

    `historique` : messages precedents, du plus ancien au plus recent,
    [{"role": "user" | "assistant", "contenu": "..."}]. Leve LLMIndisponible
    (voir llm.py) si aucun fournisseur n'a pu repondre.
    """
    messages = conversation(historique)
    messages.append({"role": "user", "contenu": message})

    rep = appeler_llm(construire_prompt(), messages)
    urgence = rep.donnees.get("urgence")
    return Compris(requete=en_requete(rep.donnees, message),
                   urgence=urgence if urgence in URGENCES else None,
                   fournisseur=rep.fournisseur)
