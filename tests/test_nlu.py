"""Coherence du jeu de donnees, du schema et du client LLM (sans appel reel)."""
import json
import re

import pytest

import llm_prototype as lp

SCHEMA = lp.load_schema()
EXEMPLES = lp.load_seed_examples()
INTENTS = {i["id"] for i in SCHEMA["intents"]}
TYPES = {e["id"] for e in SCHEMA["entities"]}

# Regle de frontiere disponibilite / commande (voir build_seed_dataset.py) :
# une commande exige un verbe explicite de reservation ou d'achat.
VERBES_COMMANDE = re.compile(
    r"n?7goz|reserv|command|nchri|achet", re.IGNORECASE
)


# ------------------------------------------------------------- dataset

@pytest.mark.parametrize("ex", EXEMPLES.values(), ids=lambda ex: ex["id"])
def test_exemple_coherent_avec_le_schema(ex):
    assert ex["intent"] in INTENTS
    for e in ex["entities"]:
        assert e["type"] in TYPES
        # les offsets doivent designer exactement la valeur annotee
        assert ex["text"][e["start"]:e["end"]] == e["value"]


def test_regle_bghit_commande_exige_un_verbe():
    fautifs = [
        ex["id"] for ex in EXEMPLES.values()
        if ex["intent"] == "commande_reservation" and not VERBES_COMMANDE.search(ex["text"])
    ]
    assert not fautifs, f"commandes sans verbe de reservation/achat : {fautifs}"


def test_regle_bghit_disponibilite_sans_verbe_de_commande():
    fautifs = [
        ex["id"] for ex in EXEMPLES.values()
        if ex["intent"] == "disponibilite_medicament" and VERBES_COMMANDE.search(ex["text"])
    ]
    assert not fautifs, f"disponibilites contenant un verbe de commande : {fautifs}"


def test_few_shot_existent_et_couvrent_tous_les_intents():
    assert all(i in EXEMPLES for i in lp.FEW_SHOT_IDS)
    assert {EXEMPLES[i]["intent"] for i in lp.FEW_SHOT_IDS} == INTENTS


# -------------------------------------------------------------- prompt

def test_prompt_contient_la_regle_sidalia():
    few = [EXEMPLES[i] for i in lp.FEW_SHOT_IDS]
    prompt = lp.build_system_prompt(SCHEMA, few)
    assert "sidalia" in prompt and "noms COMMUNS" in prompt


def test_prompt_expose_la_regle_bghit_via_le_schema():
    few = [EXEMPLES[i] for i in lp.FEW_SHOT_IDS]
    assert "n7goz" in lp.build_system_prompt(SCHEMA, few)


# ---------------------------------------------------------- validation

def test_validation_accepte_une_sortie_correcte():
    sortie = {"intent": "prix_remboursement", "entities": [{"type": "MEDICAMENT", "value": "doliprane"}]}
    assert lp.validate_output(SCHEMA, "chhal taman doliprane", sortie) == []


def test_validation_signale_intent_type_et_valeur_inventes():
    sortie = {
        "intent": "diagnostic",
        "entities": [
            {"type": "MALADIE", "value": "grippe"},
            {"type": "MEDICAMENT", "value": "aspirine"},  # absent du texte
        ],
    }
    erreurs = " ".join(lp.validate_output(SCHEMA, "wach kayn doliprane", sortie))
    assert "intent inconnu" in erreurs
    assert "type d'entite inconnu" in erreurs
    assert "absente du texte" in erreurs


# ------------------------------------------------------- client LLM

class FausseReponse:
    def __init__(self, statut, contenu=None):
        self.status_code = statut
        self.ok = 200 <= statut < 300
        self.text = "erreur"
        self._contenu = contenu

    def json(self):
        return {"choices": [{"message": {"content": self._contenu}}]}


def test_reessaie_apres_une_surcharge_passagere(monkeypatch):
    reponses = iter([
        FausseReponse(503),
        FausseReponse(200, json.dumps({"intent": "salutation", "entities": []})),
    ])
    appels = []
    monkeypatch.setattr(lp.requests, "post", lambda *a, **k: appels.append(1) or next(reponses))
    monkeypatch.setattr(lp.time, "sleep", lambda s: None)

    assert lp.call_llm("cle", "prompt", "salam")["intent"] == "salutation"
    assert len(appels) == 2


def test_ne_reessaie_pas_une_erreur_definitive(monkeypatch):
    """Une cle invalide (401) echouera toujours : reessayer ferait juste attendre."""
    appels = []
    monkeypatch.setattr(lp.requests, "post", lambda *a, **k: appels.append(1) or FausseReponse(401))
    with pytest.raises(SystemExit):
        lp.call_llm("cle", "prompt", "salam")
    assert len(appels) == 1


def test_extrait_le_json_meme_entoure_de_texte(monkeypatch):
    bavard = 'Voici la reponse : {"intent": "autre", "entities": []} Bonne journee !'
    monkeypatch.setattr(lp.requests, "post", lambda *a, **k: FausseReponse(200, bavard))
    assert lp.call_llm("cle", "prompt", "?")["intent"] == "autre"
