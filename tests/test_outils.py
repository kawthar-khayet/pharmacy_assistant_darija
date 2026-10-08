"""Outils (recherche dans data/) et composeur (redaction), sans LLM."""
import pytest

from nlp.analyse.validation import MedicamentCite
from nlp.linking.lieux import resoudre_lieu
from nlp.outils.conseil import conseil, libelles
from nlp.outils.medicament import formes_dosages
from nlp.outils.pharmacies import info_pharmacie, pharmacie_garde, pharmacies_lieu, type_ouverture
from nlp.outils.prix import prix
from nlp.outils.resolution import resoudre
from nlp.outils import securite as module_securite
from nlp.outils.securite import securite
from nlp.reponse import composeur as c


def med(nom, dosage=None, forme=None):
    return resoudre(MedicamentCite(nom=nom, dosage=dosage, forme=forme))


# ---------------------------------------------------------------- prix

def test_prix_par_presentation_et_remboursement_des_deux_regimes():
    r = prix(med("augmentin", "1g"))
    assert r["statut"] == "trouve" and r["presentations"]
    p = r["presentations"][0]
    assert {"ppv", "cnops", "cnss"} <= set(p)


def test_prix_produit_introuvable():
    assert prix(med("qwertyzol"))["statut"] == "introuvable"


def test_formes_et_dosages_disent_si_la_forme_existe():
    r = formes_dosages(med("doliprane", forme="sirop"))
    assert r["forme_existe"] is False and r["par_dosage"]


# ------------------------------------------------------------ securite

def test_securite_ne_renvoie_que_les_rubriques_demandees():
    r = securite(med("doliprane"), ["contre_indications"], "fr")
    assert list(r["rubriques"]) == ["contre_indications"]
    assert r["dci"] == "PARACETAMOL" and r["source_url"]


def test_securite_molecule_non_couverte():
    assert securite(med("smecta"), ["indications"], "fr")["statut"] == "pas_d_info"


def test_securite_donne_l_explication_simple_de_la_langue(monkeypatch):
    monkeypatch.setattr(module_securite, "_explications", lambda: {
        "PARACETAMOL|ary_lat": {"indications": "Kaydir l s-skhana w l-wja3."},
        "PARACETAMOL|fr": {"indications": "Contre la fievre et la douleur."},
    })
    r = securite(med("doliprane"), ["indications"], "ary_lat")
    assert r["explications"] == {"indications": "Kaydir l s-skhana w l-wja3."}
    bloc = c.composer_securite(r, "ary_lat").texte()
    assert "Kaydir l s-skhana" in bloc
    assert "notice" not in bloc.lower() and "Source" not in bloc


def test_securite_sans_explication_ne_montre_pas_le_texte_francais(monkeypatch):
    monkeypatch.setattr(module_securite, "_explications", lambda: {})
    r = securite(med("doliprane"), ["indications"], "ary_lat")
    bloc = c.composer_securite(r, "ary_lat").texte()
    assert "chr7 sahl" in bloc
    assert r["rubriques"]["indications"][:40] not in bloc


def test_molecule_citee_affichee_sans_la_marque():
    """"ibuprofene" ne doit pas devenir IBUPROFENE B-BRAUN (une perfusion)."""
    r = securite(med("ibuprofène"), ["indications"], "ary_lat")
    assert r["nom"] == "IBUPROFENE"
    assert securite(med("doliprane"), ["indications"], "fr")["nom"] == "DOLIPRANE"


# ------------------------------------------------------------- conseil

def test_conseil_ne_donne_que_des_molecules_commercialisees():
    r = conseil(["allergie_saisonniere"], "adulte")
    s = r["symptomes"][0]
    assert s["statut"] == "molecule"
    assert {"CETIRIZINE (DICHLORHYDRATE)", "LORATADINE"} <= set(s["molecules"])


def test_conseil_symptome_sans_molecule_oriente():
    s = conseil(["toux"])["symptomes"][0]
    assert s["statut"] == "orientation" and s["orientation"] == "PHARMACIEN"


def test_conseil_symptome_hors_liste():
    assert conseil(["autre"])["symptomes"][0]["statut"] == "inconnu"


def test_libelles_du_symptome_dans_chaque_langue():
    l = libelles("Fièvre légère, moins de 38,5 °C (skhana khfifa, سخانة خفيفة)")
    assert l == {"fr": "Fièvre légère, moins de 38,5 °C", "ary_lat": "skhana khfifa",
                 "ary_ar": "سخانة خفيفة", "ar": "سخانة خفيفة"}


# ------------------------------------------------------------ pharmacies

@pytest.mark.parametrize("horaires, attendu", [
    ("garde 24h/24", "24h"), ("24/7", "24h"), ("00H A 09H", "nuit"), ("23H A 09H", "nuit"),
    ("09H A 00H", None), ("Mo-Su 09:00-21:00", None), (None, None),
])
def test_type_ouverture(horaires, attendu):
    assert type_ouverture(horaires) == attendu


def test_petite_ville_listee_entierement():
    r = pharmacies_lieu(resoudre_lieu("Sidi Abdallah Ghiat"))
    assert r["statut"] == "trouve" and 0 < len(r["pharmacies"]) <= 5


def test_garde_seulement_24h_ou_nuit_dans_la_ville():
    r = pharmacie_garde(resoudre_lieu("tanger"))
    assert r["tour_de_garde_connu"] is False
    assert all(p["ville"] == "Tanger" and p["ouverture"] for p in r["pharmacies"])


def test_info_pharmacie_avec_lieu_inconnu_cherche_partout():
    r = info_pharmacie("ibn sina", resoudre_lieu("zzzqqq"))
    assert r["lieu_inconnu"] is True


# -------------------------------------------------------------- composeur

@pytest.mark.parametrize("brut, attendu", [
    ("539813017", "0539 81 30 17"), ("+212 5 22 25 05 71", "0522 25 05 71"),
    ("0661234567", "0661 23 45 67"), ("12", "12"), (None, None),
])
def test_telephone_mis_en_forme(brut, attendu):
    assert c.telephone_txt(brut) == attendu


def test_prix_et_distances_dans_chaque_langue():
    assert c.prix_txt(13.1, "fr") == "13,10 DH"
    assert c.prix_txt(13.1, "ary_ar") == "13.10 درهم"
    assert c.distance_txt(0.13, "fr") == "150 m"
    assert c.distance_txt(2.345, "fr") == "2,3 km"


def test_noms_et_molecules_lisibles():
    assert c.nom_txt("AUGMENTIN") == "Augmentin"
    assert c.molecule_txt("ALGINATE DE SODIUM // BICARBONATE DE SODIUM") == \
        "alginate de sodium + bicarbonate de sodium"


def test_bloc_court_sans_la_liste():
    b = c.Bloc(["tete"], ["- une", "- deux"], ["pied"])
    assert b.texte() == "tete\n- une\n- deux\npied"
    assert b.texte(court=True) == "tete\npied"


@pytest.mark.parametrize("langue", ["fr", "ary_lat", "ary_ar", "ar"])
def test_conseil_redige_dans_chaque_langue(langue):
    texte = c.composer_conseil(conseil(["fievre_legere"], "adulte"), langue).texte()
    assert "paracetamol" in texte


def test_remboursement_sans_aucun_taux_connu_en_une_phrase():
    r = prix(med("augmentin", "1g"))
    texte = c.composer_remboursement(r, "cnops", "fr").texte()
    assert texte == "Je n'ai pas le taux de remboursement CNOPS de Augmentin : demande a ton pharmacien."
