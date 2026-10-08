"""Appel LLM unique du moteur : Gemini, puis Groq, puis Ollama Cloud en secours.

C'est le seul fichier qui parle a un LLM. On lui donne des consignes (le prompt
systeme) et la conversation ; il renvoie le JSON du premier fournisseur qui
repond correctement, et le nom de ce fournisseur (utile pendant les tests pour
savoir qui a repondu). L'ordre et les cles se reglent dans le .env (config.py).
"""
import json
import logging
import time
from dataclasses import dataclass

import requests

from nlp.config import FOURNISSEURS, LLM_ORDRE, LLM_TENTATIVES, LLM_TIMEOUT

log = logging.getLogger(__name__)

# Quota, surcharge ou panne passagere : on relance le meme fournisseur une fois.
STATUTS_PASSAGERS = {429, 500, 502, 503, 504}


class LLMIndisponible(Exception):
    """Aucun fournisseur n'a pu repondre : le pipeline doit prevenir le patient."""


class _ErreurPassagere(Exception):
    """Vaut une relance du meme fournisseur (reseau, delai, 429, 5xx)."""


class _ErreurDefinitive(Exception):
    """Relancer ne changerait rien (cle ou modele invalide, reponse bloquee,
    JSON illisible) : on passe directement au fournisseur suivant."""


@dataclass
class ReponseLLM:
    donnees: dict       # le JSON renvoye par le modele, deja decode
    fournisseur: str    # "gemini", "gemini_secours", "groq" ou "ollama"
    modele: str


def _poster(url: str, entetes: dict, corps: dict) -> dict:
    try:
        r = requests.post(url, headers=entetes, json=corps, timeout=LLM_TIMEOUT)
    except requests.RequestException as e:  # delai depasse, reseau coupe...
        raise _ErreurPassagere(str(e)) from e
    if r.status_code in STATUTS_PASSAGERS:
        raise _ErreurPassagere(f"HTTP {r.status_code}")
    if not r.ok:
        # 400 / 401 / 403 / 404 : cle ou nom de modele a corriger dans le .env
        raise _ErreurDefinitive(f"HTTP {r.status_code} : {r.text[:300]}")
    return r.json()


def _messages_openai(systeme: str, messages: list[dict]) -> list[dict]:
    """Format commun a Groq et Ollama : le prompt systeme en premier message."""
    return [{"role": "system", "content": systeme}] + [
        {"role": m["role"], "content": m["contenu"]} for m in messages
    ]


def _gemini(conf: dict, systeme: str, messages: list[dict]) -> str:
    corps = {
        "system_instruction": {"parts": [{"text": systeme}]},
        # Gemini appelle "model" ce que les autres appellent "assistant"
        "contents": [
            {"role": "model" if m["role"] == "assistant" else "user",
             "parts": [{"text": m["contenu"]}]}
            for m in messages
        ],
        "generationConfig": {"temperature": 0, "response_mime_type": "application/json"},
    }
    rep = _poster(f"{conf['url']}/models/{conf['modele']}:generateContent",
                  {"x-goog-api-key": conf["cle"]}, corps)
    try:
        parties = rep["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        # reponse bloquee par les filtres de securite de Gemini, ou vide
        raise _ErreurDefinitive(f"reponse vide : {json.dumps(rep)[:300]}")
    # les parties "thought" sont le raisonnement interne du modele, pas la reponse
    return "".join(p.get("text", "") for p in parties if not p.get("thought"))


def _groq(conf: dict, systeme: str, messages: list[dict]) -> str:
    corps = {
        "model": conf["modele"],
        "messages": _messages_openai(systeme, messages),
        "temperature": 0,
        # mode JSON : Groq exige que le mot "JSON" figure dans le prompt systeme
        "response_format": {"type": "json_object"},
    }
    rep = _poster(f"{conf['url']}/chat/completions",
                  {"Authorization": f"Bearer {conf['cle']}"}, corps)
    try:
        return rep["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise _ErreurDefinitive(f"reponse vide : {json.dumps(rep)[:300]}")


def _ollama(conf: dict, systeme: str, messages: list[dict]) -> str:
    corps = {
        "model": conf["modele"],
        "messages": _messages_openai(systeme, messages),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    rep = _poster(f"{conf['url']}/chat",
                  {"Authorization": f"Bearer {conf['cle']}"}, corps)
    try:
        return rep["message"]["content"]
    except KeyError:
        raise _ErreurDefinitive(f"reponse vide : {json.dumps(rep)[:300]}")


_APPELS = {"gemini": _gemini, "gemini_secours": _gemini, "groq": _groq, "ollama": _ollama}


def _extraire_json(texte: str) -> dict:
    """Decode la reponse, meme si le modele l'a entouree de ``` ou de texte."""
    texte = texte.strip()
    if texte.startswith("```"):
        texte = texte.strip("`")
        texte = texte.split("\n", 1)[1] if "\n" in texte else texte
    try:
        donnees = json.loads(texte)
    except json.JSONDecodeError:
        debut, fin = texte.find("{"), texte.rfind("}")
        if debut == -1 or fin == -1:
            raise _ErreurDefinitive(f"pas de JSON dans la reponse : {texte[:200]}")
        try:
            donnees = json.loads(texte[debut:fin + 1])
        except json.JSONDecodeError as e:
            raise _ErreurDefinitive(f"JSON illisible : {e}") from e
    if not isinstance(donnees, dict):
        raise _ErreurDefinitive("le JSON renvoye n'est pas un objet")
    return donnees


def appeler_llm(systeme: str, messages: list[dict]) -> ReponseLLM:
    """Envoie la conversation au premier fournisseur disponible.

    `messages` : [{"role": "user" | "assistant", "contenu": "..."}, ...],
    du plus ancien au plus recent ; le dernier est la question du patient.
    Leve LLMIndisponible si aucun fournisseur n'a pu repondre.
    """
    erreurs = []
    for nom in LLM_ORDRE:
        conf = FOURNISSEURS.get(nom)
        if conf is None:
            erreurs.append(f"{nom} : fournisseur inconnu (verifier LLM_ORDRE)")
            continue
        if not conf["cle"]:
            erreurs.append(f"{nom} : pas de cle dans le .env")
            continue

        derniere = ""
        for tentative in range(LLM_TENTATIVES):
            try:
                texte = _APPELS[nom](conf, systeme, messages)
                return ReponseLLM(_extraire_json(texte), nom, conf["modele"])
            except _ErreurPassagere as e:
                derniere = f"{nom} : {e}"
                if tentative < LLM_TENTATIVES - 1:
                    time.sleep(1.5)  # laisser passer un pic de charge
            except _ErreurDefinitive as e:
                derniere = f"{nom} : {e}"
                break
        erreurs.append(derniere)
        log.warning("LLM indisponible, passage au suivant -- %s", derniere)

    raise LLMIndisponible(" ; ".join(erreurs) or "LLM_ORDRE est vide dans le .env")
