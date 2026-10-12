"""Outils pharmacies (recherche dans data/), sans LLM."""
import pytest

from api.main import telephone_txt
from nlp.linking.lieux import resoudre_lieu
from nlp.outils.pharmacies import info_pharmacie, pharmacie_garde, pharmacies_lieu, type_ouverture


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


# -------------------------------------------------------------- telephone

@pytest.mark.parametrize("brut, attendu", [
    ("539813017", "0539 81 30 17"), ("+212 5 22 25 05 71", "0522 25 05 71"),
    ("0661234567", "0661 23 45 67"), ("12", "12"), (None, None),
])
def test_telephone_mis_en_forme(brut, attendu):
    assert telephone_txt(brut) == attendu
