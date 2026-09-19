"""Baseline classique (regles + TF-IDF), utilisee pour la comparaison au LLM."""
import pytest

from baseline import ExtracteurRegles, nouveau_classifieur_intent


@pytest.fixture(scope="module")
def regles():
    return ExtracteurRegles()


def couples(entites):
    return {(e["type"], e["value"]) for e in entites}


def test_phrase_complete(regles):
    assert couples(regles.extraire("wach kayn doliprane 1g? bghit juj boites")) == {
        ("MEDICAMENT", "doliprane"), ("DOSAGE", "1g"), ("QUANTITE", "juj"), ("FORME", "boites"),
    }


def test_article_elide_retire(regles):
    assert ("MEDICAMENT", "amoxicilline") in couples(regles.extraire("comment prendre l'amoxicilline"))


def test_sidalia_seul_n_est_pas_une_pharmacie(regles):
    assert not any(e["type"] == "PHARMACIE" for e in regles.extraire("fin kayna sidalia?"))


def test_nom_propre_apres_sidalia(regles):
    assert ("PHARMACIE", "Ibn Sina") in couples(regles.extraire("wach sidalia Ibn Sina 7alla?"))


def test_nombre_isole_n_est_pas_une_quantite(regles):
    """'wa7ed' seul veut souvent dire 'quelqu'un' : une quantite n'est retenue
    que devant une forme galenique."""
    assert not any(e["type"] == "QUANTITE" for e in regles.extraire("wa7ed sa7bi mrid"))


def test_toute_valeur_est_une_sous_chaine_du_texte(regles):
    for texte in ["wach kayn doliprane 1g?", "fin kayna sidalia f Maarif?", "بغيت جوج علب دوليبران"]:
        for e in regles.extraire(texte):
            assert e["value"] in texte


def test_classifieur_s_entraine_et_predit():
    clf = nouveau_classifieur_intent()
    clf.fit(
        ["wach kayn doliprane", "chhal taman panadol", "salam", "fin kayna sidalia"],
        ["disponibilite_medicament", "prix_remboursement", "salutation", "info_pharmacie"],
    )
    assert clf.predict(["chhal taman doliprane"])[0] == "prix_remboursement"
