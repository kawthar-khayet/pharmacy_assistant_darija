"""Pretraitement d'une photo de boite et extraction de texte (Challenge #2)."""
import io

import numpy as np
import pytest
from PIL import Image

from nlp.outils.resolution import reconnaitre_depuis_lignes
from nlp.vision.ocr import extraire_texte
from nlp.vision.pretraitement import LARGEUR_MAX, TAILLE_MAX_OCTETS, ErreurImage, pretraiter


def _jpeg(largeur=200, hauteur=100):
    tampon = io.BytesIO()
    Image.new("RGB", (largeur, hauteur), (250, 250, 250)).save(tampon, format="JPEG")
    return tampon.getvalue()


# ---------------------------------------------------------------- pretraitement

def test_image_vide_refusee():
    with pytest.raises(ErreurImage, match="vide"):
        pretraiter(b"")


def test_image_trop_lourde_refusee():
    with pytest.raises(ErreurImage, match="grande"):
        pretraiter(b"0" * (TAILLE_MAX_OCTETS + 1))


def test_contenu_non_image_refuse():
    with pytest.raises(ErreurImage, match="illisible"):
        pretraiter(b"ceci n'est pas une image" * 50)


def test_image_valide_pretraitee():
    resultat = pretraiter(_jpeg())
    assert resultat.ndim == 3 and resultat.shape[2] == 3   # RGB, pas binarisee


def test_grande_image_redimensionnee():
    resultat = pretraiter(_jpeg(largeur=3000, hauteur=1000))
    assert resultat.shape[1] == LARGEUR_MAX


# ------------------------------------------------------------------------ OCR

def test_lignes_peu_fiables_ecartees(monkeypatch):
    import nlp.vision.ocr as module

    class FauxLecteur:
        def readtext(self, image):
            return [([], "DOLIPRANE", 0.9), ([], "bruit illisible", 0.1)]

    monkeypatch.setattr(module, "_charger", lambda langue: FauxLecteur())
    resultat = extraire_texte(np.zeros((10, 10, 3), dtype="uint8"))
    assert resultat["textes"] == ["DOLIPRANE"]


def test_lignes_dupliquees_entre_passes_fusionnees(monkeypatch):
    import nlp.vision.ocr as module

    class FauxLecteur:
        def readtext(self, image):
            return [([], "1000 MG", 0.95)]

    monkeypatch.setattr(module, "_charger", lambda langue: FauxLecteur())
    resultat = extraire_texte(np.zeros((10, 10, 3), dtype="uint8"))
    assert resultat["textes"] == ["1000 MG"]   # pas deux fois, une passe par langue


# ---------------------------------------------------------- reconnaissance

def test_reconnaissance_ligne_par_ligne_resiste_au_bruit_des_autres_lignes():
    """Une boite melange nom, dosage et labo sur des lignes separees : les
    joindre en une seule requete ferait decrocher le matcher sur un faux
    candidat ; ligne par ligne, le nom se retrouve avec un score parfait."""
    lignes = ["HEVAZ", "600 MG", "COMPRIME PELLICULE", "EFAVIRENZ", "GENPHARMA"]
    resultats = reconnaitre_depuis_lignes(lignes)
    assert resultats[0]["nom_candidat"] == "HEVAZ"
    assert resultats[0]["score"] == 100.0


def test_reconnaissance_aucune_ligne_ne_matche():
    assert reconnaitre_depuis_lignes(["XYZ BIDON INEXISTANT 123"]) == []


def test_reconnaissance_ligne_dci_n_introduit_pas_d_autres_marques():
    """Une ligne qui ne porte que la DCI (souvent imprimee sur la boite,
    ex. "PARACETAMOL") ne doit pas faire apparaitre une AUTRE marque
    partageant la meme molecule : ca conviendrait a une recherche tapee au
    clavier, mais pas a la reconnaissance d'UNE boite precise."""
    resultats = reconnaitre_depuis_lignes(["DOLIPRANE", "PARACETAMOL"])
    assert all("DOLIPRANE" in r["nom_candidat"] for r in resultats)


def test_reconnaissance_ligne_dosage_seule_ignoree():
    """Une ligne qui ne porte qu'un dosage ("1000 MG") ne peut distinguer
    aucun produit : elle ne doit pas introduire de bruit."""
    resultats = reconnaitre_depuis_lignes(["DOLIPRANE", "1000 MG"])
    assert all("DOLIPRANE" in r["nom_candidat"] for r in resultats)


def test_reconnaissance_ligne_forme_generique_seule_ignoree():
    """Une ligne qui ne porte qu'un mot de vocabulaire pharmaceutique
    generique ("COMPRIME", "SOLUTION INJECTABLE") ne doit pas introduire de
    bruit : presque toute boite de comprimes le dit."""
    resultats = reconnaitre_depuis_lignes(["DOLIPRANE", "COMPRIME", "SOLUTION INJECTABLE"])
    assert all("DOLIPRANE" in r["nom_candidat"] for r in resultats)


# -------------------------------------------------------------------- API

def test_reconnaissance_image_vide_refusee(client):
    r = client.post("/reconnaissance", files={"fichier": ("boite.jpg", b"", "image/jpeg")})
    assert r.status_code == 422


def test_reconnaissance_sans_texte_detecte(client, ocr):
    ocr([])
    r = client.post("/reconnaissance", files={"fichier": ("boite.jpg", _jpeg(), "image/jpeg")})
    d = r.json()
    assert r.status_code == 200
    assert d["reussite"] is False
    assert d["resultats"] == []


def test_reconnaissance_bout_en_bout(client, ocr):
    ocr(["DOLIPRANE", "1000 MG"], langues=["fr"])
    r = client.post("/reconnaissance", files={"fichier": ("boite.jpg", _jpeg(), "image/jpeg")})
    assert r.status_code == 200
    d = r.json()
    assert d["reussite"] is True
    assert d["resultats"][0]["nom_candidat"] == "DOLIPRANE"
    assert d["resultats"][0]["confidence"] == "auto"
    # memes champs que GET /medicaments, pour reutiliser MedicineCard/MedicineDetails
    assert "securite_disponible" in d["resultats"][0]
    assert d["texte_detecte"] == ["DOLIPRANE", "1000 MG"]


def test_reconnaissance_texte_sans_medicament(client, ocr):
    ocr(["XYZ BIDON INEXISTANT 123"])
    r = client.post("/reconnaissance", files={"fichier": ("boite.jpg", _jpeg(), "image/jpeg")})
    d = r.json()
    assert d["reussite"] is True
    assert d["resultats"] == []
    assert "aucun medicament" in d["message"].lower()
