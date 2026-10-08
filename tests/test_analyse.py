"""Analyse : prompt, validation de la reponse du LLM, filet urgence, chaine de fournisseurs."""
import json

import pytest

import nlp.llm
from nlp.analyse.analyseur import charger_schema, construire_prompt
from nlp.analyse.urgence import detecter_urgence
from nlp.analyse.validation import valider
from nlp.llm import LLMIndisponible
# importe avant que le garde-fou de conftest ne le remplace
from nlp.llm import appeler_llm as vrai_appeler_llm


# ------------------------------------------------------------------- prompt

def test_le_prompt_n_a_plus_de_repere_a_remplacer():
    prompt = construire_prompt()
    assert "{{" not in prompt
    for demande in charger_schema()["demandes"]:
        assert f"- {demande} :" in prompt


def test_le_prompt_liste_les_symptomes_de_la_liste_blanche():
    assert "fievre_legere" in construire_prompt()


def test_la_posologie_n_a_besoin_de_rien():
    assert "posologie" in construire_prompt()
    assert charger_schema()["demandes"]["posologie"]["besoin"] == []


# --------------------------------------------------------------- validation

def test_une_analyse_correcte_passe_sans_correction():
    a = valider({"situation": "repondre", "demandes": ["prix"],
                 "medicaments": [{"nom": "dolipran", "dosage": "1g", "forme": None}],
                 "langue": "ary_lat"}, "chhal taman dolipran 1g")
    assert (a.situation, a.demandes, a.corrections) == ("repondre", ["prix"], [])
    assert a.medicaments[0].nom == "dolipran"


def test_situation_inventee_ramenee_a_pas_d_info():
    a = valider({"situation": "commande", "langue": "fr"}, "x")
    assert a.situation == "pas_d_info" and a.corrections


def test_demande_supprimee_retiree():
    """disponibilite et alternatives n'existent plus : DwaTalk ne connait aucun stock."""
    a = valider({"situation": "repondre", "demandes": ["disponibilite", "prix"],
                 "medicaments": ["doliprane"], "langue": "fr"}, "x")
    assert a.demandes == ["prix"]
    assert a.medicaments[0].nom == "doliprane"     # ["doliprane"] accepte comme [{"nom": ...}]


def test_besoin_manquant_passe_en_preciser():
    a = valider({"situation": "repondre", "demandes": ["remboursement"],
                 "medicaments": [{"nom": "smecta"}], "langue": "fr"}, "x")
    assert a.situation == "preciser" and a.manque == ["regime"]


def test_preciser_sans_rien_qui_manque_repasse_en_repondre():
    a = valider({"situation": "preciser", "demandes": ["posologie"], "langue": "fr"}, "x")
    assert a.situation == "repondre"


def test_pas_de_demande_pendant_une_urgence():
    a = valider({"situation": "urgence", "urgence_type": "bizarre", "demandes": ["prix"],
                 "langue": "fr"}, "x")
    assert a.demandes == [] and a.urgence_type == "detresse"


def test_symptome_inconnu_devient_autre():
    a = valider({"situation": "conseil_symptome", "symptomes": ["fievre_legere", "lepre"],
                 "langue": "fr"}, "x")
    assert a.symptomes == ["fievre_legere", "autre"]


@pytest.mark.parametrize("message, langue", [("واش كاين", "ary_ar"), ("bonjour", "fr")])
def test_langue_inconnue_devinee_par_la_graphie(message, langue):
    assert valider({"situation": "salutation", "langue": "klingon"}, message).langue == langue


def test_valeurs_hors_liste_ramenees_a_inconnu():
    a = valider({"situation": "salutation", "langue": "fr", "patient": "vieux",
                 "grossesse": "peut-etre", "regime": "AMO", "duree_jours": "abc"}, "x")
    assert (a.patient, a.grossesse, a.regime, a.duree_jours) == ("inconnu", "inconnu", "inconnu", None)


# ------------------------------------------------------------ filet urgence

@pytest.mark.parametrize("message, attendu", [
    ("wlidi bla3 chi 10 d l7bob dyal doliprane", "intoxication"),
    ("khdit bzaf dyal dwa", "intoxication"),
    ("mon fils a avale des comprimes", "intoxication"),
    ("تسمم", "intoxication"),
    ("ma kaytnfsch mzyan", "detresse"),
    ("il respire mal depuis tout a l'heure", "detresse"),
    ("ما بقاتش كتنفس", "detresse"),
    ("douleur dans la poitrine", "detresse"),
])
def test_urgence_detectee(message, attendu):
    assert detecter_urgence(message) == attendu


@pytest.mark.parametrize("message", [
    "chhal taman doliprane", "fin kayna pharmacie f maarif", "salam", "effets du spasfon",
])
def test_pas_d_urgence_dans_une_question_ordinaire(message):
    assert detecter_urgence(message) is None


# ------------------------------------------------------- chaine de fournisseurs

class FausseReponse:
    def __init__(self, statut, contenu=""):
        self.status_code = statut
        self.ok = 200 <= statut < 300
        self.text = "erreur"
        self._contenu = contenu

    def json(self):
        return {"choices": [{"message": {"content": self._contenu}}]}


@pytest.fixture
def groq_seul(monkeypatch):
    monkeypatch.setattr(nlp.llm, "LLM_ORDRE", ["groq"])
    monkeypatch.setattr(nlp.llm, "FOURNISSEURS", {"groq": {"cle": "cle", "modele": "m", "url": "http://x"}})
    monkeypatch.setattr(nlp.llm.time, "sleep", lambda s: None)


def test_reessaie_apres_une_surcharge_passagere(monkeypatch, groq_seul):
    reponses = iter([FausseReponse(503), FausseReponse(200, json.dumps({"situation": "salutation"}))])
    appels = []
    monkeypatch.setattr(nlp.llm.requests, "post", lambda *a, **k: appels.append(1) or next(reponses))
    r = vrai_appeler_llm("prompt JSON", [{"role": "user", "contenu": "salam"}])
    assert r.donnees["situation"] == "salutation" and r.fournisseur == "groq"
    assert len(appels) == 2


def test_ne_reessaie_pas_une_erreur_definitive(monkeypatch, groq_seul):
    """Une cle invalide (401) echouera toujours : reessayer ferait juste attendre."""
    appels = []
    monkeypatch.setattr(nlp.llm.requests, "post", lambda *a, **k: appels.append(1) or FausseReponse(401))
    with pytest.raises(LLMIndisponible):
        vrai_appeler_llm("prompt JSON", [{"role": "user", "contenu": "salam"}])
    assert len(appels) == 1


def test_passe_au_fournisseur_suivant(monkeypatch):
    monkeypatch.setattr(nlp.llm, "LLM_ORDRE", ["gemini", "groq"])
    monkeypatch.setattr(nlp.llm, "FOURNISSEURS", {
        "gemini": {"cle": "", "modele": "m", "url": "http://g"},      # pas de cle : ignore
        "groq": {"cle": "cle", "modele": "m", "url": "http://x"},
    })
    monkeypatch.setattr(nlp.llm.requests, "post",
                        lambda *a, **k: FausseReponse(200, '{"situation": "hors_sujet"}'))
    assert vrai_appeler_llm("JSON", [{"role": "user", "contenu": "?"}]).fournisseur == "groq"


def test_extrait_le_json_meme_entoure_de_texte(monkeypatch, groq_seul):
    bavard = 'Voici : {"situation": "hors_sujet"} Bonne journee !'
    monkeypatch.setattr(nlp.llm.requests, "post", lambda *a, **k: FausseReponse(200, bavard))
    assert vrai_appeler_llm("JSON", [{"role": "user", "contenu": "?"}]).donnees["situation"] == "hors_sujet"
