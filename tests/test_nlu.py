"""Coherence du jeu de donnees, du schema et du client LLM (sans appel reel)."""
import json
import re
from collections import Counter

import pytest

import llm_prototype as lp

SCHEMA = lp.load_schema()
EXEMPLES = lp.load_seed_examples()
INTENTS = {i["id"] for i in SCHEMA["intents"]}
TYPES = {e["id"] for e in SCHEMA["entities"]}

TAXONOMIE_V2 = {
    "disponibilite_medicament", "prix_remboursement", "alternative_moins_chere",
    "info_pharmacie", "posologie_information", "conseil_medical", "salutation", "hors_sujet",
}

# verbes qui definissaient l'ancienne intention commande_reservation
VERBES_COMMANDE = re.compile(r"n?7goz|reserv|command|nchri|achet", re.IGNORECASE)


# ------------------------------------------------------------- dataset

@pytest.mark.parametrize("ex", EXEMPLES.values(), ids=lambda ex: ex["id"])
def test_exemple_coherent_avec_le_schema(ex):
    assert ex["intent"] in INTENTS
    for e in ex["entities"]:
        assert e["type"] in TYPES
        # les offsets doivent designer exactement la valeur annotee
        assert ex["text"][e["start"]:e["end"]] == e["value"]


def test_taxonomie_v2():
    assert INTENTS == TAXONOMIE_V2


def test_plus_aucune_ancienne_intention_dans_le_jeu():
    anciennes = {"autre", "commande_reservation"}
    assert not [ex["id"] for ex in EXEMPLES.values() if ex["intent"] in anciennes]


def test_ex_commandes_sont_des_demandes_de_medicament():
    """Depuis la fusion, une phrase avec un verbe de reservation ou d'achat est
    une demande de medicament comme les autres."""
    fautifs = [
        ex["id"] for ex in EXEMPLES.values()
        if VERBES_COMMANDE.search(ex["text"]) and ex["intent"] != "disponibilite_medicament"
    ]
    assert not fautifs, fautifs


def test_chaque_intention_a_assez_d_exemples():
    """En dessous de ~8 exemples, une intention est trop fragile pour etre
    apprise ou evaluee : c'etait le cas de commande_reservation."""
    compte = Counter(ex["intent"] for ex in EXEMPLES.values())
    assert min(compte[i] for i in INTENTS) >= 8, compte


def test_questions_de_sante_et_hors_sujet_sans_entite():
    for ex in EXEMPLES.values():
        if ex["intent"] in {"conseil_medical", "hors_sujet"}:
            assert ex["entities"] == [], ex["id"]


def test_demandes_d_equivalent_citent_un_medicament():
    for ex in EXEMPLES.values():
        if ex["intent"] == "alternative_moins_chere":
            assert any(e["type"] == "MEDICAMENT" for e in ex["entities"]), ex["id"]


def test_few_shot_existent_et_couvrent_tous_les_intents():
    assert all(i in EXEMPLES for i in lp.FEW_SHOT_IDS)
    assert {EXEMPLES[i]["intent"] for i in lp.FEW_SHOT_IDS} == INTENTS


# -------------------------------------------------------------- prompt

def _prompt():
    return lp.build_system_prompt(SCHEMA, [EXEMPLES[i] for i in lp.FEW_SHOT_IDS])


def test_prompt_contient_la_regle_sidalia():
    prompt = _prompt()
    assert "sidalia" in prompt and "noms COMMUNS" in prompt


def test_prompt_explique_la_fusion_de_la_commande():
    assert "n7goz" in _prompt()


def test_prompt_distingue_sante_et_hors_sujet():
    prompt = _prompt()
    assert "conseil_medical" in prompt and "hors_sujet" in prompt
    assert '"autre"' not in prompt


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
    bavard = 'Voici la reponse : {"intent": "hors_sujet", "entities": []} Bonne journee !'
    monkeypatch.setattr(lp.requests, "post", lambda *a, **k: FausseReponse(200, bavard))
    assert lp.call_llm("cle", "prompt", "?")["intent"] == "hors_sujet"
