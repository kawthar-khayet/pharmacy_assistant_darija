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


@pytest.mark.parametrize("requete, attendu", [
    ("فولتارين", "VOLTARENE"),
    ("بانادول", "PANADOL"),
    ("كلاموكسيل", "CLAMOXYL"),
    ("إيموديوم", "IMODIUM"),
    ("أسبيجيك", "ASPEGIC"),
    ("الدوليبران", "DOLIPRANE"),      # avec l'article defini
    ("بغيت دوليبران", "DOLIPRANE"),    # nom noye dans une phrase dictee
])
def test_medicament_dicte_en_arabe_hors_table(meds, requete, attendu):
    """Graphies arabes absentes de la table de correspondances ecrite a la
    main : elles ne sont retrouvees que par la translitteration lettre a
    lettre et la cle phonetique. C'est le cas de figure d'une question posee
    a la voix, que Whisper transcrit en arabe faute de modele de darija."""
    premier = meds.match(requete, top_k=1)[0]
    assert premier["nom_candidat"] == attendu


def test_bruit_dicte_en_arabe_jamais_auto(meds):
    """La cle phonetique ecrase des distinctions : elle ne doit pas pour
    autant faire passer du charabia pour un medicament identifie."""
    assert all(r["confidence"] != "auto" for r in meds.match("بيدون إينكسيستانت", top_k=3))


def test_homophones_signales_comme_a_confirmer(meds):
    """Plusieurs produits peuvent sonner pareil une fois la cle calculee. Le
    matcher n'a alors aucun moyen de savoir lequel a ete dicte : il propose,
    il n'affirme pas."""
    resultats = meds.match("باراسيتامول", top_k=3)
    assert resultats and resultats[0]["confidence"] != "auto"


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


@pytest.mark.parametrize("ville_dite, attendue", [
    ("الدار البيضاء", "Casablanca"),
    ("كازا", "Casablanca"),
    ("casa", "Casablanca"),          # diminutif d'usage, a l'ecrit comme a l'oral
    ("الرباط", "Rabat"),
    ("مراكش", "Marrakech"),
    ("طنجة", "Tanger"),
])
def test_ville_dite_en_arabe_ou_en_diminutif(pharmas, ville_dite, attendue):
    """Un toponyme n'est pas la transcription sonore de l'autre : « الدار
    البيضاء » et « Casablanca » n'ont aucune lettre commune. Ces cas passent
    par la table d'alias, pas par la translitteration."""
    resultats = pharmas.match(location=ville_dite, top_k=3)
    assert resultats and {r["ville"] for r in resultats} == {attendue}


def test_nom_porte_par_plusieurs_villes_signale(pharmas):
    """Les noms d'officine sont tres repetitifs au Maroc. Sans ville, le
    matcher ne peut pas trancher : il doit le dire plutot que de renvoyer la
    premiere de la liste comme si c'etait la bonne."""
    pharmas.match(nom="Pharmacie Granada", top_k=3)
    note = pharmas.last_name_note
    assert note and "Nador" in note and "Al Hoceima" in note


def test_nom_avec_ville_ne_declenche_pas_l_alerte(pharmas):
    """Une fois la ville donnee, il n'y a plus d'ambiguite a signaler."""
    pharmas.match(nom="Granada", location="Nador", top_k=3)
    assert pharmas.last_name_note is None


def test_nom_unique_ne_declenche_pas_l_alerte(pharmas):
    pharmas.match(nom="Branes", top_k=3)
    assert pharmas.last_name_note is None


def test_nom_absurde_ne_declenche_pas_l_alerte(pharmas):
    pharmas.match(nom="Bidon Inexistante Xyz123", top_k=3)
    assert pharmas.last_name_note is None


def test_pharmacie_dictee_en_arabe(pharmas):
    """« صيدلية » (pharmacie) ouvre presque toutes les demandes dictees en
    arabe : comme « Pharmacie », il ne discrimine rien et doit etre ignore."""
    resultats = pharmas.match(nom="صيدلية ابن سينا", location="الرباط", top_k=3)
    assert resultats[0]["nom"] == "Pharmacie Ibn Sina"
    assert resultats[0]["ville"] == "Rabat"


def test_nom_absurde_dicte_en_arabe_jamais_fiable(pharmas):
    assert all(
        r["confidence"] == "non_fiable"
        for r in pharmas.match(nom="صيدلية بيدون إينكسيستانت", top_k=3)
    )


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
