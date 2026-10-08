"""Translitteration arabe -> latin et cle phonetique.

Ces tests fixent le comportement dont depend tout le matching d'une question
dictee a la voix : Whisper rend la darija en graphie arabe, la base est en
latin. Ils verifient le pont entre les deux, pas la qualite de Whisper.
"""
import pytest

from nlp.linking.translitteration import cle_phonetique, contient_arabe, translitterer


@pytest.mark.parametrize("texte, attendu", [
    ("دوليبران", True),
    ("doliprane", False),
    ("بغيت doliprane", True),   # phrase melangee
    ("", False),
])
def test_detection_graphie_arabe(texte, attendu):
    assert contient_arabe(texte) is attendu


@pytest.mark.parametrize("arabe, latin", [
    ("دوليبران", "doulibran"),
    ("سميكتا", "smikta"),
    ("فلاجيل", "flajil"),
])
def test_translitteration_lettre_a_lettre(arabe, latin):
    assert translitterer(arabe) == latin


def test_translitteration_laisse_le_latin_intact():
    """Les patients melangent les graphies dans une meme phrase : la partie
    deja en latin ne doit pas etre touchee."""
    assert translitterer("بغيت doliprane 1000") == "bghit doliprane 1000"


def test_article_defini_retire():
    """« الدوليبران » (le Doliprane) doit se ramener au nom du produit."""
    assert translitterer("الدوليبران") == translitterer("دوليبران")


def test_article_defini_garde_sur_un_mot_court():
    """Un mot court qui commence par ces deux lettres ne doit pas etre ampute :
    « الم » (douleur) n'est pas « l'M »."""
    assert translitterer("الم") == "alm"


def test_diacritiques_ignorees():
    """Les harakat sont ornementales : deux graphies du meme mot convergent."""
    assert translitterer("دُولِيبْران") == translitterer("دوليبران")


@pytest.mark.parametrize("arabe, nom_base", [
    ("دوليبران", "DOLIPRANE"),      # p ecrit avec un ب, -e final muet
    ("فولتارين", "VOLTARENE"),      # v ecrit avec un ف
    ("سبازفون", "SPASFON"),         # s/z indistincts
    ("بانادول", "PANADOL"),
    ("أوميبرازول", "OMEPRAZOLE"),   # hamza initiale devant و : pas de syllabe en plus
    ("كلاموكسيل", "CLAMOXYL"),      # k/c et x/ks
])
def test_cle_phonetique_rapproche_les_deux_graphies(arabe, nom_base):
    assert cle_phonetique(arabe) == cle_phonetique(nom_base)


@pytest.mark.parametrize("variante", ["DOLIPRANE", "doliprane", "Dolipranne", "DOLIPRÂNE"])
def test_cle_phonetique_stable_en_latin(variante):
    """Casse, accents et gemination ne changent pas la sonorite."""
    assert cle_phonetique(variante) == "dolibran"


def test_cle_phonetique_distingue_encore_des_noms_differents():
    """La cle rapproche, elle n'aplatit pas tout : deux produits sans rapport
    gardent des cles distinctes."""
    assert cle_phonetique("SMECTA") != cle_phonetique("VOLTARENE")


def test_cle_phonetique_texte_vide():
    assert cle_phonetique("") == ""
    assert cle_phonetique("...") == ""
