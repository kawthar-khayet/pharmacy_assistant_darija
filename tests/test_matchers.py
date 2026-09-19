"""Entity linking : resolution des noms de medicaments et de pharmacies."""
import pytest

from entity_linking import MedicamentMatcher, equivalents, famille_forme, normalize
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


# ------------------------------------------------------------ equivalents

def _lignes(meds, nom):
    return meds.df[meds.df["nom_norm"] == normalize(nom)]


def test_equivalents_du_moins_cher_au_plus_cher(meds):
    r = equivalents(meds, "DOLIPRANE", "500mg")
    prix = [e["ppv"] for e in r["equivalents"]]
    assert prix and prix == sorted(prix)
    assert all(e["nom"] != "DOLIPRANE" for e in r["equivalents"])


def test_equivalents_meme_molecule_et_meme_dosage(meds):
    r = equivalents(meds, "DOLIPRANE", "500mg")
    for e in r["equivalents"]:
        lignes = _lignes(meds, e["nom"])
        assert (lignes["dci_norm"] == "PARACETAMOL").any(), e["nom"]
        assert normalize(e["dosage"]).replace(" ", "") == "500MG", e


def test_association_jamais_remplacee_par_une_seule_molecule(meds):
    """Regression : la liste CNSS decoupe l'Augmentin (amoxicilline + acide
    clavulanique) en une ligne par molecule, et le premier prototype proposait
    NEOMOX -- de l'amoxicilline seule, injectable."""
    r = equivalents(meds, "AUGMENTIN")
    assert "CLAVULANIQUE" in normalize(r["reference"]["dci"])
    assert r["equivalents"]
    for e in r["equivalents"]:
        assert "NEOMOX" not in e["nom"]
        assert _lignes(meds, e["nom"])["dci_norm"].str.contains("CLAVULANIQUE").any(), e["nom"]


def test_meme_voie_d_administration(meds):
    """Regression : un suppositoire etait propose a la place d'un comprime."""
    for nom in ["DOLIPRANE", "AUGMENTIN", "VOLTARENE"]:
        r = equivalents(meds, nom)
        famille = famille_forme(r["reference"]["forme"])
        for e in r["equivalents"]:
            assert famille_forme(e["forme"]) == famille, (nom, e)


def test_jamais_de_produit_retire_ou_non_commercialise(meds):
    for nom in ["DOLIPRANE", "AUGMENTIN", "VOLTARENE", "CLAMOXYL"]:
        for e in equivalents(meds, nom)["equivalents"]:
            statuts = set(_lignes(meds, e["nom"])["statut_commercialisation"].dropna())
            assert not statuts or "Commercialisé" in statuts, (e["nom"], statuts)


def test_forme_orale_preferee_sans_precision(meds):
    """Sans precision, "Spasfon" designe le comprime, pas le suppositoire."""
    assert famille_forme(equivalents(meds, "SPASFON")["reference"]["forme"]) == "orale_solide"


@pytest.mark.parametrize("forme, famille", [
    ("COMPRIME EFFERVESCENT", "orale_solide"),
    ("GELULE", "orale_solide"),
    ("SACHET", "orale_poudre"),
    ("POUDRE POUR SUSPENSION BUVABLE", "orale_liquide"),
    ("POUDRE POUR SOLUTION INJECTABLE", "injectable"),
    ("SUPPOSITOIRE", "rectale"),
    ("GEL", "cutanee"),
])
def test_familles_de_formes(forme, famille):
    assert famille_forme(forme) == famille
