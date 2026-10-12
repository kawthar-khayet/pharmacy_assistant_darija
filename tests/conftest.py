"""Configuration commune des tests.

Aucun test ne consomme d'appel au LLM ni ne charge le modele d'embeddings :
les deux appels LLM (comprendre, repondre) sont remplaces par des sorties
fixees a l'avance, et l'index du RAG par un petit index en memoire, rempli de
vraies fiches. Les tests verifient donc NOTRE code (fiches, recherche dans les
bases, ce qu'on envoie au LLM, API), pas la qualite du modele.
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


# Medicaments et molecules dont les fiches entrent dans l'index de test.
MEDICAMENTS_TEST = {"DOLIPRANE", "ASPRO", "AUGMENTIN"}
MOLECULES_TEST = {"PARACETAMOL"}
VECTEUR = [1.0, 0.0, 0.0]


@pytest.fixture(autouse=True)
def pas_de_vrai_llm(monkeypatch):
    """Garde-fou : un test qui oublie de simuler le LLM (fixture `llm`) echoue
    au lieu de consommer le quota d'un fournisseur ; idem pour le modele
    d'embeddings, long a charger."""
    import nlp.llm
    import nlp.moteur
    import nlp.rag.comprendre
    import nlp.rag.index
    import nlp.rag.recherche

    def refuser(*args, **kwargs):
        raise AssertionError("appel LLM reel pendant un test : utiliser la fixture `llm`")

    def refuser_modele(*args, **kwargs):
        raise AssertionError("modele d'embeddings charge pendant un test : utiliser la fixture `index`")

    monkeypatch.setattr(nlp.llm, "appeler_llm", refuser)
    monkeypatch.setattr(nlp.moteur, "appeler_llm", refuser)
    monkeypatch.setattr(nlp.rag.comprendre, "appeler_llm", refuser)
    monkeypatch.setattr(nlp.rag.index, "modele", refuser_modele)
    monkeypatch.setattr(nlp.rag.recherche, "vecteur_question", lambda question: VECTEUR)
    # ni reponse retenue d'un test a l'autre, ni lecture du site des gardes
    nlp.moteur.cache.vider()
    monkeypatch.setattr(nlp.rag.recherche, "garde_du_jour", lambda ville: None)


@pytest.fixture(scope="session")
def fiches():
    """Toutes les fiches, ecrites une fois par fiches.py a partir des vraies bases."""
    from nlp.rag.fiches import toutes_les_fiches
    return toutes_les_fiches()


@pytest.fixture(scope="session")
def _collection(fiches):
    """Un index ChromaDB en memoire : les medicaments de MEDICAMENTS_TEST, les
    marques et les notices de MOLECULES_TEST, et tous les conseils. Tous les
    vecteurs sont egaux : on teste les filtres, pas la recherche par le sens."""
    import chromadb

    gardees = [f for f in fiches
               if f["type"] == "conseil"
               or (f["type"] == "medicament" and (f["meta"]["nom"] in MEDICAMENTS_TEST
                                                  or f["meta"].get("dci") in MOLECULES_TEST))
               or (f["type"] == "notice" and f["meta"]["dci"] in MOLECULES_TEST)]
    col = chromadb.EphemeralClient().create_collection("fiches_test", metadata={"hnsw:space": "cosine"})
    col.add(ids=[f["id"] for f in gardees], documents=[f["texte"] for f in gardees],
            embeddings=[VECTEUR] * len(gardees),
            metadatas=[{"type": f["type"], **f["meta"]} for f in gardees])
    return col


@pytest.fixture
def index(_collection, monkeypatch):
    import nlp.moteur
    import nlp.rag.recherche

    monkeypatch.setattr(nlp.rag.recherche, "collection", lambda: _collection)
    monkeypatch.setattr(nlp.moteur, "collection", lambda: _collection)
    return _collection


@pytest.fixture
def llm(index, monkeypatch):
    """Simule les deux appels LLM d'un message :

        appels = llm(medicaments=["doliprane"], question="Prix de Doliprane ?")

    Les champs sont ceux du JSON de comprehension (comprendre.md) ; `reponse`
    est le texte que le second appel renverra. Renvoie la liste des appels
    (systeme, messages), pour verifier ce qu'on a envoye au LLM.
    """
    import nlp.moteur
    import nlp.rag.comprendre
    from nlp.llm import ReponseLLM

    appels = []

    def definir(reponse="Reponse du LLM.", **champs):
        def faux(systeme, messages, en_json=True):
            appels.append({"systeme": systeme, "messages": [dict(m) for m in messages], "en_json": en_json})
            if en_json:
                return ReponseLLM(dict(champs), "test", "modele-de-test")
            return ReponseLLM({}, "test", "modele-de-test", reponse)

        monkeypatch.setattr(nlp.rag.comprendre, "appeler_llm", faux)
        monkeypatch.setattr(nlp.moteur, "appeler_llm", faux)
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
