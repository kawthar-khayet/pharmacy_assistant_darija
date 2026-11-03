"""Extraction de texte sur une photo de boite (EasyOCR), Challenge #2.

L'arabe et le francais ne peuvent pas partager un meme lecteur EasyOCR (jeux
de caracteres incompatibles) : comme Whisper n'a pas de darija (voir
api/parole.py), on fait deux passes separees et on fusionne les lignes
retenues, dans le meme esprit que la voix.
"""
import threading

import numpy as np

SEUIL_CONFIANCE = 0.3
LANGUES = {"ar": ["ar", "en"], "fr": ["fr"]}

_lecteurs: dict[str, object] = {}
_verrou = threading.Lock()


def _charger(langue: str):
    # Import differe : EasyOCR tire torch et charge ses modeles de
    # detection/reconnaissance au premier appel (quelques dizaines de Mo par
    # langue), inutile tant que personne ne scanne de boite.
    if langue not in _lecteurs:
        with _verrou:
            if langue not in _lecteurs:
                import easyocr

                _lecteurs[langue] = easyocr.Reader(LANGUES[langue], gpu=False, verbose=False)
    return _lecteurs[langue]


def extraire_texte(image: np.ndarray) -> dict:
    """Image RGB pretraitee -> lignes de texte retenues (passe AR puis FR).

    Une ligne deja retenue par une passe n'est pas redemandee a l'autre : deux
    lecteurs qui lisent la meme boite retrouvent souvent les memes chiffres
    (dosage) ou le meme mot latin, qu'il est inutile de dupliquer."""
    textes: list[str] = []
    langues: list[str] = []
    for langue in ("ar", "fr"):
        lecteur = _charger(langue)
        for _, texte, confiance in lecteur.readtext(image):
            texte = texte.strip()
            if confiance >= SEUIL_CONFIANCE and texte and texte not in textes:
                textes.append(texte)
                if langue not in langues:
                    langues.append(langue)
    return {"textes": textes, "langues": langues}


def lecteurs_charges() -> bool:
    return bool(_lecteurs)


__all__ = ["SEUIL_CONFIANCE", "LANGUES", "extraire_texte", "lecteurs_charges"]
