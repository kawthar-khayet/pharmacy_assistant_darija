"""Linking : retrouver medicaments, lieux et pharmacies malgre les fautes."""
import pytest

from nlp.linking.lieux import est_pharmacie, resoudre_lieu
from nlp.linking.medicaments import MedicamentMatcher, dose_mg, famille_forme, filtrer_dosage
from nlp.linking.pharmacies import chercher_pharmacie


@pytest.fixture(scope="module")
def meds():
    return MedicamentMatcher()


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



@pytest.mark.parametrize("dosage, mg", [
    ("1000", 1000), ("1000mg", 1000), ("1g", 1000), ("1 G", 1000), ("1 gr", 1000),
    ("12,5 MG", 12.5), ("500 µg", 0.5), ("1000 UI", None), ("5 %", None),
])
def test_dose_en_mg(dosage, mg):
    assert dose_mg(dosage) == mg


@pytest.mark.parametrize("dosage", ["1000", "1000mg", "1g", "1000g"])  # 1000g : faute pour mg
def test_doliprane_1000_trouve_1_g(meds, dosage):
    lignes = meds.df[meds.df["nom_norm"] == "DOLIPRANE"]
    assert set(filtrer_dosage(lignes, dosage)["dosage"]) == {"1 G"}

def test_aucune_valeur_nan_dans_les_resultats(meds):
    """Une case vide doit sortir en None (null en JSON), jamais en NaN."""
    for r in meds.match("doliprane", top_k=3):
        for v in r["variantes"]:
            for valeur in v.values():
                assert not (isinstance(valeur, float) and valeur != valeur)


def test_requete_vide(meds):
    assert meds.match("   ") == []

# ---------------------------------------------------------------------- lieux

@pytest.mark.parametrize("ecrit", ["maarif", "f m3arif", "Maârif", "المعاريف", "فالمعاريف", "maarif casa"])
def test_quartier_ecrit_de_plusieurs_facons(ecrit):
    """Preposition, arabizi, accents, graphie arabe, ville ajoutee : meme quartier."""
    lieu = resoudre_lieu(ecrit)
    assert (lieu.statut, lieu.ville) == ("quartier", "Casablanca")
    assert lieu.latitude and lieu.longitude


@pytest.mark.parametrize("ecrit, ville", [
    ("casa", "Casablanca"), ("كازا", "Casablanca"), ("الدار البيضاء", "Casablanca"),
    ("rbat", "Rabat"), ("الرباط", "Rabat"), ("tanja", "Tanger"), ("fes", "Fès"),
])
def test_ville_ecrite_en_darija_ou_en_arabe(ecrit, ville):
    lieu = resoudre_lieu(ecrit)
    assert (lieu.statut, lieu.ville) == ("ville", ville)


def test_quartier_homonyme_ambigu_sauf_ville_connue():
    lieu = resoudre_lieu("agdal")
    assert lieu.statut == "ambigu" and {"Rabat", "Fès"} <= set(lieu.villes_possibles)
    assert resoudre_lieu("agdal", ville_connue="Rabat").ville == "Rabat"


def test_quartier_absent_d_osm_retrouve_par_les_adresses():
    """Beaucoup de quartiers manquent dans OSM ; l'annuaire les cite dans ses adresses."""
    lieu = resoudre_lieu("daoudiate")
    assert (lieu.statut, lieu.ville, lieu.source) == ("quartier", "Marrakech", "adresses")


def test_osm_et_annuaire_sont_reunis():
    """OSM ne connait que le Oulfa d'El Jadida ; l'annuaire cite celui de
    Casablanca. Le patient doit pouvoir choisir, pas etre envoye a El Jadida."""
    assert set(resoudre_lieu("oulfa").villes_possibles) == {"Casablanca", "El Jadida"}
    assert resoudre_lieu("oulfa casa").ville == "Casablanca"


def test_un_quartier_n_est_pas_pris_pour_une_commune_voisine():
    """« yacoub el mansour » (Rabat) contient presque le nom de la commune El Mansouria."""
    lieu = resoudre_lieu("yacoub el mansour")
    assert lieu.ville != "El Mansouria"
    # c'est aussi un boulevard de Casablanca : demander la ville est legitime
    assert lieu.ville == "Rabat" or "Rabat" in lieu.villes_possibles
    assert resoudre_lieu("yacoub el mansour", ville_connue="Rabat").ville == "Rabat"


def test_quartier_inconnu_dans_une_ville_connue():
    lieu = resoudre_lieu("xyzzy casa")
    assert (lieu.statut, lieu.ville, lieu.quartier_inconnu) == ("ville", "Casablanca", "Xyzzy")


@pytest.mark.parametrize("bruit", ["qwerty", "zzzqqqville", ""])
def test_lieu_inconnu(bruit):
    assert resoudre_lieu(bruit).statut == "introuvable"


# ----------------------------------------------------------------- pharmacies

@pytest.mark.parametrize("nom, attendu", [
    ("Parapharmacie Ibn Rochd", False), ("Droguerie Al Mal", False), ("Big Para", False),
    ("Pharmacie Ibn Sina", True), ("Para & Pharmacie Benzit", True), ("صيدلية النخيل", True),
])
def test_parapharmacies_et_drogueries_ecartees(nom, attendu):
    assert est_pharmacie(nom) is attendu


def test_pharmacie_par_nom_et_ville():
    r = chercher_pharmacie("ibn sina", ville="Rabat")
    assert r.statut == "trouve" and r.pharmacies[0]["ville"] == "Rabat"


def test_nom_present_dans_plusieurs_villes_ambigu():
    r = chercher_pharmacie("ibn sina")
    assert r.statut == "ambigu" and len(r.villes_possibles) > 10
    assert chercher_pharmacie("ibn sina", ville_connue="Fès").pharmacies[0]["ville"] == "Fès"


def test_pharmacie_dictee_en_arabe():
    r = chercher_pharmacie("صيدلية النخيل")
    assert r.statut in ("trouve", "ambigu") and "NAKHIL" in r.nom.upper()


def test_un_mot_court_commun_ne_suffit_pas():
    """« IBN » figure dans des centaines de noms : seul, il faisait proposer
    Ibn Rochd ou Lina a qui cherchait Ibn Sina."""
    r = chercher_pharmacie("ibn sina", ville="Casablanca")
    assert all("SINA" in p["nom"].upper() for p in r.pharmacies)


@pytest.mark.parametrize("bruit", ["Bidon Inexistante Xyz123", "qwerty asdf"])
def test_nom_absurde_introuvable(bruit):
    assert chercher_pharmacie(bruit).statut == "introuvable"


def test_fiche_sans_nan():
    r = chercher_pharmacie("ibn sina", ville="Rabat", pres_de=(34.0, -6.8))
    for valeur in r.pharmacies[0].values():
        assert not (isinstance(valeur, float) and valeur != valeur)


# ---------------------------------------------------------------- formes

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
