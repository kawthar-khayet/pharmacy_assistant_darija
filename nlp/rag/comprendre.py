"""Comprehension : le premier des deux appels LLM d'un message.

Le LLM lit le message (et la conversation) et dit quoi chercher : les
medicaments et le lieu cites, la pharmacie voulue, et la question reformulee
en francais (la recherche par le sens comprend mal la darija). C'est lui qui
decide de la recherche ; recherche.py l'execute dans nos donnees.

Le prompt est relu a chaque message : on peut modifier comprendre.md pendant
les tests sans redemarrer le serveur.
"""
from dataclasses import dataclass
from pathlib import Path

from nlp.llm import appeler_llm
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


def en_requete(donnees: dict, message: str) -> Requete:
    """Le JSON du LLM, verifie champ par champ : un champ absent ou mal forme
    prend sa valeur par defaut au lieu de faire echouer la reponse."""
    medicaments = donnees.get("medicaments")
    if not isinstance(medicaments, list):
        medicaments = []
    return Requete(
        # sans reformulation, on cherche avec le message tel quel
        question=_texte(donnees.get("question")) or message,
        medicaments=[m for x in medicaments if (m := _texte(x))],
        lieu=_texte(donnees.get("lieu")),
        pharmacie=_texte(donnees.get("pharmacie")),
        pharmacies=donnees.get("pharmacies") is True,
        garde=donnees.get("garde") is True,
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

    rep = appeler_llm(PROMPT_PATH.read_text(encoding="utf-8"), messages)
    urgence = rep.donnees.get("urgence")
    return Compris(requete=en_requete(rep.donnees, message),
                   urgence=urgence if urgence in URGENCES else None,
                   fournisseur=rep.fournisseur)
