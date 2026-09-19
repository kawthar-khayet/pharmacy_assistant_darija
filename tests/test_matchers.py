"""Entity linking : resolution des noms de medicaments et de pharmacies."""
import pytest

from entity_linking import MedicamentMatcher
from pharmacy_linking import PharmacyMatcher


@pytest.fixture(scope="module")
def meds():
    return MedicamentMatcher()


@pytest.fixture(scope="module")
def pharmas():
    return PharmacyMatcher()


# ---------------------------------------------------------------- medicaments

@pytest.mark.parametrize("requete, attendu", [
    ("doliprane", "DOLIPRANE"),
    ("dolipran", "DOLIPRANE"),        # faute de frappe
    ("DOLIPRANE", "DOLIPRANE"),       # casse
    ("دوليبران", "DOLIPRANE"),         # graphie arabe
    ("spasfon", "SPASFON"),
    ("flagyl", "FLAGYL"),
])
def test_medicament_resolu(meds, requete, attendu):
    premier = meds.match(requete, top_k=1)[0]
    assert premier["nom_candidat"] == attendu
    assert premier["confidence"] == "auto"


def test_recherche_par_molecule(meds):
    """Une requete par DCI remonte des noms commerciaux sans ressemblance
    lexicale avec elle : le garde-fou anti-bruit ne doit pas les rejeter."""
    noms = {r["nom_candidat"]: r["confidence"] for r in meds.match("ibuprofene", top_k=5)}
    assert noms.get("ADFENE") == "auto"


@pytest.mark.parametrize("bruit", ["Bidon Inexistante Xyz123", "qwerty asdf", "Zzzzqqq"])
def test_requete_absurde_jamais_auto(meds, bruit):
    """Une requete absurde ne doit jamais produire un candidat 'auto', c'est-a-dire
    presente comme sur. 'a_confirmer' reste possible quand un mot ressemble
    vraiment a un medicament : 'Bidon' est a deux lettres de 'Bridion'."""
    assert all(r["confidence"] != "auto" for r in meds.match(bruit, top_k=3))


@pytest.mark.parametrize("bruit", ["qwerty asdf", "Zzzzqqq"])
def test_requete_sans_mot_approchant_toute_non_fiable(meds, bruit):
    assert all(r["confidence"] == "non_fiable" for r in meds.match(bruit, top_k=3))


def test_filtre_par_dosage(meds):
    variantes = meds.match("doliprane", dosage="1g", top_k=1)[0]["variantes"]
    assert variantes and all("1" in (v["dosage"] or "") for v in variantes)


def test_aucune_valeur_nan_dans_les_resultats(meds):
    """Une case vide doit sortir en None (null en JSON), jamais en NaN."""
    for r in meds.match("doliprane", top_k=3):
        for v in r["variantes"]:
            for valeur in v.values():
                assert not (isinstance(valeur, float) and valeur != valeur)


def test_requete_vide(meds):
    assert meds.match("   ") == []


# --------------------------------------------------------------- pharmacies

@pytest.mark.parametrize("nom, lieu, attendu", [
    ("Granada", "Nador", "Pharmacie Granada"),
    ("Grenada", "Nador", "Pharmacie Granada"),   # faute
    ("Al Hikmaa", "Rabat", "Pharmacie Al Hikma"),
])
def test_pharmacie_par_nom_et_lieu(pharmas, nom, lieu, attendu):
    premier = pharmas.match(nom=nom, location=lieu, top_k=1)[0]
    assert premier["nom"] == attendu


def test_quartier_resolu_vers_sa_ville(pharmas):
    resultats = pharmas.match(location="Maarif", top_k=5)
    assert resultats and {r["ville"] for r in resultats} == {"Casablanca"}


def test_quartier_ambigu_signale(pharmas):
    """'Maarif' existe dans plusieurs villes : le choix de la ville dominante
    doit etre signale, pas fait en silence."""
    pharmas.match(location="Maarif", top_k=3)
    assert pharmas.last_location_note and "Casablanca" in pharmas.last_location_note


def test_lieu_inconnu_ne_renvoie_rien(pharmas):
    assert pharmas.match(location="Zzzqqqville", top_k=3) == []


def test_nom_absurde_jamais_fiable(pharmas):
    assert all(r["confidence"] == "non_fiable" for r in pharmas.match(nom="Bidon Inexistante Xyz123", top_k=3))
