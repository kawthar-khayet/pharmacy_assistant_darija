"""Pretraitement d'une photo de boite avant OCR (Challenge #2).

Redimensionnement, amelioration du contraste (CLAHE) et redressement (deskew) :
les corrections qui aident le plus une photo prise a main levee (eclairage
inegal, leger flou, boite un peu inclinee). Pas de binarisation (Otsu) : utile
pour Tesseract, elle nuirait ici a EasyOCR, entraine sur des photos naturelles
et non sur du texte noir et blanc.
"""
import cv2
import numpy as np

TAILLE_MAX_OCTETS = 10 * 1024 * 1024
LARGEUR_MAX = 1600


class ErreurImage(ValueError):
    """Image inexploitable : vide, trop lourde, corrompue."""


def _deskew(gris: np.ndarray) -> np.ndarray:
    """Corrige une inclinaison legere (photo a main levee) ; au-dela de 15
    degres, le cadrage est deja trop different d'une photo de boite bien
    tenue pour qu'une rotation automatique fasse plus de bien que de mal."""
    inverse = cv2.bitwise_not(gris)
    seuil = cv2.threshold(inverse, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(seuil > 0))
    if len(coords) < 100:
        return gris

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle += 90
    if abs(angle) < 0.5 or abs(angle) > 15:
        return gris

    centre = (gris.shape[1] // 2, gris.shape[0] // 2)
    rotation = cv2.getRotationMatrix2D(centre, angle, 1.0)
    return cv2.warpAffine(
        gris, rotation, (gris.shape[1], gris.shape[0]),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )


def pretraiter(contenu: bytes) -> np.ndarray:
    """bytes JPEG/PNG/WEBP -> image RGB pretraitee, prete pour l'OCR."""
    if not contenu:
        raise ErreurImage("Image vide.")
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise ErreurImage("Image trop grande (10 Mo maximum).")

    tableau = np.frombuffer(contenu, np.uint8)
    image = cv2.imdecode(tableau, cv2.IMREAD_COLOR)
    if image is None:
        raise ErreurImage("Image illisible ou format non supporte (JPEG, PNG ou WEBP attendu).")

    hauteur, largeur = image.shape[:2]
    if largeur > LARGEUR_MAX:
        echelle = LARGEUR_MAX / largeur
        image = cv2.resize(
            image, (LARGEUR_MAX, max(1, int(hauteur * echelle))), interpolation=cv2.INTER_AREA,
        )

    gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gris = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gris)
    gris = _deskew(gris)

    return cv2.cvtColor(gris, cv2.COLOR_GRAY2RGB)


__all__ = ["ErreurImage", "TAILLE_MAX_OCTETS", "LARGEUR_MAX", "pretraiter"]
