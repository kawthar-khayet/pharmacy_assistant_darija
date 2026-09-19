"""Configuration commune des tests.

Aucun test ne consomme d'appel au LLM : le NLU est remplace par une sortie
fixee a l'avance. Les tests verifient donc NOTRE code (routage des intents,
entity linking, formulation, API), pas la qualite du modele -- mesuree a part
par nlu/evaluate.py et nlu/compare_baseline.py.
"""
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "nlu"))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "lent: charge le modele Whisper (~2 s, et un telechargement de ~460 Mo au tout premier lancement)",
    )


@pytest.fixture(scope="session")
def api():
    import api.main as module
    return module


@pytest.fixture
def client(api, monkeypatch):
    from fastapi.testclient import TestClient

    # chaque test repart d'une memoire de conversation vide
    monkeypatch.setattr(api, "SESSIONS", {})
    return TestClient(api.app)


@pytest.fixture
def nlu(api, monkeypatch):
    """Remplace le NLU par une sortie choisie par le test :

        nlu("prix_remboursement", MEDICAMENT="doliprane")
    """

    def definir(intent, **entites):
        sortie = {
            "intent": intent,
            "entities": [{"type": t, "value": v} for t, v in entites.items()],
        }
        monkeypatch.setattr(
            api,
            "run_nlu",
            lambda texte: {"input": texte, "output": sortie, "validation_errors": []},
        )

    return definir


@pytest.fixture(scope="session")
def audio_fr():
    # "Bonjour, est-ce que vous avez du Doliprane un gramme ?", voix de synthese
    # Windows (Hortense, fr-FR) : un vrai enregistrement de parole, reproductible
    return (FIXTURES / "question_fr.wav").read_bytes()
