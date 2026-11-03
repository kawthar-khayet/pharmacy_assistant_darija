"""Dataset synthetique de boites de medicaments, pour evaluer le pipeline de
reconnaissance du Challenge #2 (OCR + matching, voir nlp/vision/).

Pourquoi synthetique : il n'existe pas de jeu de photos de boites marocaines
telechargeable ni scrapable legalement (la vente de medicaments en ligne est
interdite au Maroc par la loi 17-04 -- pas de site a scraper -- et la BDPM
francaise, qui documente les memes specialites, ne publie pas de photos
d'emballage). Les datasets Kaggle/Roboflow existants portent sur des marques
internationales sans correspondance avec data/clean/medicaments_reference.csv,
et servent a la detection de boite, pas a l'OCR. On genere donc des mockups a
partir de nos propres donnees, avec une verite terrain exacte (la ligne du CSV
qui a produit l'image), ce qui permet de chiffrer une accuracy reelle --
voir scripts/evaluer_reconnaissance.py.

Limite assumee : un mockup rendu au clavier n'a ni le graphisme, ni les
logos, ni le texte arabe d'une vraie boite. Il mesure la robustesse du
pipeline (OCR + fuzzy matching) au bruit visuel (flou, rotation, luminosite,
compression), pas la reconnaissance visuelle d'une vraie photo -- pour ca,
constituer en plus un petit jeu de vraies photos (voir data/vision/README.md).

Sortie :
  - data/vision/synthetique/images/*.jpg
  - data/vision/synthetique/manifest.csv (verite terrain : fichier -> produit)

Usage :
    py scripts/generer_boites_synthetiques.py
    py scripts/generer_boites_synthetiques.py --n 500 --seed 7
"""
import argparse
import io
import random
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nlp.linking.medicaments import STATUTS_EN_OFFICINE  # noqa: E402

REFERENCE = ROOT / "data" / "clean" / "medicaments_reference.csv"
SORTIE_DEFAUT = ROOT / "data" / "vision" / "synthetique"

TAILLE_CANEVAS = (640, 420)
# Fonds pastel courants sur les boites marocaines (blanc, bleu pharma, vert) ;
# le texte reste toujours en noir ou bleu fonce, jamais sur un fond proche.
FONDS = [(255, 255, 255), (235, 244, 250), (233, 245, 236), (250, 247, 232)]
POLICES_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def slug(texte: str) -> str:
    sans_accents = "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", sans_accents.lower()).strip("_")[:40]


def _police(taille: int) -> ImageFont.FreeTypeFont:
    for chemin in POLICES_CANDIDATES:
        if Path(chemin).exists():
            return ImageFont.truetype(chemin, taille)
    return ImageFont.load_default(size=taille)   # boites de test sans police systeme (CI)


def charger_produits(n: int, graine: int) -> pd.DataFrame:
    df = pd.read_csv(REFERENCE, dtype=str)
    # meme regle de disponibilite que le matcher (voir nlp/linking/medicaments.py) :
    # une ligne sans statut vient des listes de remboursement, consideree disponible
    disponible = df["statut_commercialisation"].isin(STATUTS_EN_OFFICINE) | df["statut_commercialisation"].isna()
    df = df[disponible & df["nom"].notna()].drop_duplicates(subset="nom")
    n = min(n, len(df))
    return df.sample(n=n, random_state=graine).reset_index(drop=True)


def dessiner_boite(produit: pd.Series, alea: random.Random) -> Image.Image:
    image = Image.new("RGB", TAILLE_CANEVAS, alea.choice(FONDS))
    dessin = ImageDraw.Draw(image)
    marge = 36

    dessin.rectangle([marge // 2, marge // 2, TAILLE_CANEVAS[0] - marge // 2, TAILLE_CANEVAS[1] - marge // 2],
                      outline=(60, 60, 60), width=3)

    nom = str(produit["nom"])
    police_nom = _police(42 if len(nom) < 22 else 30)
    dessin.text((marge, 70), nom, font=police_nom, fill=(15, 15, 90))

    ligne_dosage = " — ".join(x for x in [produit.get("dosage"), produit.get("forme")] if isinstance(x, str) and x)
    if ligne_dosage:
        dessin.text((marge, 150), ligne_dosage[:60], font=_police(26), fill=(20, 20, 20))

    dci = produit.get("dci")
    if isinstance(dci, str) and dci:
        dessin.text((marge, 195), dci[:60], font=_police(20), fill=(70, 70, 70))

    labo = produit.get("laboratoire")
    if isinstance(labo, str) and labo:
        dessin.text((marge, TAILLE_CANEVAS[1] - 60), labo[:40], font=_police(18), fill=(90, 90, 90))

    return image


def degrader(image: Image.Image, alea: random.Random) -> bytes:
    """Rotation, flou, luminosite/contraste, compression JPEG : les
    conditions realistes citees par l'enonce du Challenge #2 (flou, eclairage,
    visibilite partielle de la boite)."""
    image = image.rotate(alea.uniform(-6, 6), expand=True, fillcolor=(255, 255, 255))

    rayon_flou = alea.uniform(0, 1.4)
    if rayon_flou > 0.15:
        image = image.filter(ImageFilter.GaussianBlur(rayon_flou))

    image = ImageEnhance.Brightness(image).enhance(alea.uniform(0.75, 1.25))
    image = ImageEnhance.Contrast(image).enhance(alea.uniform(0.8, 1.2))

    # boite partiellement visible : on rogne jusqu'a 8% d'un cote au hasard
    if alea.random() < 0.3:
        largeur, hauteur = image.size
        cote = alea.choice(["gauche", "droite", "haut", "bas"])
        part = alea.uniform(0.0, 0.08)
        if cote == "gauche":
            image = image.crop((int(largeur * part), 0, largeur, hauteur))
        elif cote == "droite":
            image = image.crop((0, 0, int(largeur * (1 - part)), hauteur))
        elif cote == "haut":
            image = image.crop((0, int(hauteur * part), largeur, hauteur))
        else:
            image = image.crop((0, 0, largeur, int(hauteur * (1 - part))))

    tampon = io.BytesIO()
    image.convert("RGB").save(tampon, format="JPEG", quality=alea.randint(40, 90))
    return tampon.getvalue()


def main(n: int, graine: int, sortie: Path) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    produits = charger_produits(n, graine)
    dossier_images = sortie / "images"
    dossier_images.mkdir(parents=True, exist_ok=True)

    lignes = []
    for i, produit in produits.iterrows():
        alea = random.Random(graine * 100_003 + i)
        image = dessiner_boite(produit, alea)
        contenu = degrader(image, alea)
        fichier = f"{i:04d}_{slug(str(produit['nom']))}.jpg"
        (dossier_images / fichier).write_bytes(contenu)
        lignes.append({
            "fichier": fichier, "nom": produit["nom"], "dci": produit.get("dci"),
            "dosage": produit.get("dosage"), "forme": produit.get("forme"),
            "laboratoire": produit.get("laboratoire"),
        })

    manifest = pd.DataFrame(lignes)
    manifest.to_csv(sortie / "manifest.csv", index=False)
    print(f"{len(manifest)} boites synthetiques -> {dossier_images}")
    print(f"verite terrain -> {sortie / 'manifest.csv'}")


if __name__ == "__main__":
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--n", type=int, default=300, help="nombre de boites a generer")
    analyseur.add_argument("--seed", type=int, default=42, help="graine aleatoire (reproductibilite)")
    analyseur.add_argument("--sortie", type=Path, default=SORTIE_DEFAUT)
    arguments = analyseur.parse_args()
    main(arguments.n, arguments.seed, arguments.sortie)
