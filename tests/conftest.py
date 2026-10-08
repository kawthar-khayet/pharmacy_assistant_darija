"""Configuration commune des tests.

Aucun test ne consomme d'appel au LLM : l'analyse (le seul appel LLM du bot)
est remplacee par une sortie fixee a l'avance. Les tests verifient donc NOTRE
code (validation, recherche dans les bases, outils, redaction, API), pas la
qualite du modele.
"""
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "lent: charge le modele Whisper (~2 s, et un telechargement de ~460 Mo au tout premier lancement)",
    )


@pytest.fixture(autouse=True)
def pas_de_vrai_llm(monkeypatch):
    """Garde-fou : un test qui oublie de simuler l'analyse echoue au lieu de
    consommer le quota d'un fournisseur."""
    import nlp.llm
    import nlp.moteur

    def refuser(*args, **kwargs):
        raise AssertionError("appel LLM reel pendant un test : simuler l'analyse avec la fixture `analyse`")

    monkeypatch.setattr(nlp.llm, "appeler_llm", refuser)
    monkeypatch.setattr(nlp.moteur, "analyser", refuser)


@pytest.fixture
def analyse(monkeypatch):
    """Remplace l'analyse par une sortie choisie par le test :

        analyse(demandes=["prix"], medicaments=[{"nom": "doliprane"}])

    Les champs absents prennent leur valeur par defaut (situation "repondre",
    langue "fr"...). Renvoie la liste des appels, pour verifier l'historique
    transmis au LLM.
    """
    import nlp.moteur
    from nlp.llm import ReponseLLM

    appels = []

    def definir(**champs):
        sortie = {"situation": "repondre", "demandes": [], "medicaments": [], "lieu": None,
                  "pharmacie": None, "regime": "inconnu", "patient": "inconnu",
                  "grossesse": "inconnu", "symptomes": [], "duree_jours": None, "langue": "fr"}
        sortie.update(champs)

        def faux(message, historique=None):
            appels.append({"message": message, "historique": list(historique or [])})
            return ReponseLLM(sortie, "test", "modele-de-test")

        monkeypatch.setattr(nlp.moteur, "analyser", faux)
        return appels

    return definir


@pytest.fixture(scope="session")
def api():
    import api.main as module
    return module


@pytest.fixture
def client(api, monkeypatch):
    from collections import OrderedDict

    from fastapi.testclient import TestClient

    # chaque test repart d'une memoire de conversation vide
    monkeypatch.setattr(api, "SESSIONS", OrderedDict())
    return TestClient(api.app)


@pytest.fixture(scope="session")
def audio_fr():
    # "Bonjour, est-ce que vous avez du Doliprane un gramme ?", voix de synthese
    # Windows (Hortense, fr-FR) : un vrai enregistrement de parole, reproductible
    return (FIXTURES / "question_fr.wav").read_bytes()
