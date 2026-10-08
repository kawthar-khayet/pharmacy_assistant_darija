"""Le bot repond dans la langue et la graphie de la question."""
import re

import pytest

from nlp.reponse.langues import LANGUES, detecter_langue
from nlp.reponse.phrases import TEXTES, t


# ------------------------------------------------------------ detection

@pytest.mark.parametrize("texte, attendu", [
    ("salam", "ary_lat"),
    ("wach kayn doliprane 1g?", "ary_lat"),
    ("3andkom smecta dyal drari sghar?", "ary_lat"),
    ("chhal taman panadol", "ary_lat"),
    ("واش كاين دوليبران؟", "ary_ar"),
    ("شحال تمن دوليبران؟", "ary_ar"),
    ("Bonjour, est-ce que vous avez du Doliprane ?", "fr"),
    ("prix du doliprane 1g", "fr"),
])
def test_detection_sans_avis_du_modele(texte, attendu):
    assert detecter_langue(texte) == attendu


def test_le_modele_tranche_entre_darija_et_arabe_standard():
    assert detecter_langue("هل يوجد دواء دوليبران؟", "ar") == "ar"
    assert detecter_langue("واش كاين دوليبران؟", "ary_ar") == "ary_ar"


def test_une_langue_contraire_a_la_graphie_est_ignoree():
    assert detecter_langue("wach kayn doliprane", "ar") == "ary_lat"
    assert detecter_langue("واش كاين دوليبران", "fr") == "ary_ar"
    assert detecter_langue("bonjour", "klingon") == "fr"


# -------------------------------------------------------------- phrases

def test_chaque_phrase_existe_dans_les_quatre_langues():
    manquants = [(cle, l) for cle, v in TEXTES.items() for l in LANGUES if not v.get(l)]
    assert manquants == []


def test_memes_parametres_dans_toutes_les_langues():
    """Une traduction qui oublie {nom} ou {ville} perdrait une information.
    Exception voulue : les signes d'alerte de la liste conseil sont ecrits en
    francais, les autres langues ont une phrase d'alerte generale."""
    for cle, variantes in TEXTES.items():
        if cle == "conseil_alerte":
            continue
        attendus = set(re.findall(r"{(\w+)}", variantes["fr"]))
        for langue in LANGUES:
            assert set(re.findall(r"{(\w+)}", variantes[langue])) == attendus, (cle, langue)


@pytest.mark.parametrize("cle, numeros", [
    ("urgence_detresse", ("141", "15")),
    ("urgence_intoxication", ("0801 000 180", "141", "15")),
    ("llm_indisponible", ("141", "15", "0801 000 180")),
])
def test_les_numeros_d_urgence_sont_dans_toutes_les_langues(cle, numeros):
    for langue in LANGUES:
        for numero in numeros:
            assert numero in TEXTES[cle][langue], (cle, langue, numero)


def test_posologie_renvoie_au_medecin_dans_toutes_les_langues():
    mots = {"fr": "medecin", "ary_lat": "tbib", "ary_ar": "الطبيب", "ar": "طبيب"}
    for langue, mot in mots.items():
        assert mot in t(langue, "posologie")


def test_phrase_absente_retombe_sur_le_francais(monkeypatch):
    monkeypatch.setitem(TEXTES, "essai", {"fr": "Bonjour {nom}"})
    assert t("ary_ar", "essai", nom="Sara") == "Bonjour Sara"
