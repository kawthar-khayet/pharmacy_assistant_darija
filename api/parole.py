"""Reconnaissance vocale : transcription d'un enregistrement avec Whisper.

Modele : faster-whisper (reimplementation de Whisper sur CTranslate2), en local,
sur CPU, quantifie en int8. Pas de service externe ni de cout par requete.
Le modele est charge au premier appel puis garde en memoire : le premier appel
le telecharge si besoin (~460 Mo pour "small"), les suivants ne coutent que le
calcul.

Choix du modele (variable d'environnement WHISPER_MODEL) :
  - "small" (defaut) : bon compromis qualite / vitesse sur CPU pour l'arabe et
    le francais ;
  - "base" : ~3x plus rapide, nettement moins fiable sur l'arabe ;
  - "medium" : meilleur, mais lent sur CPU (plusieurs secondes par phrase).

Limite connue : Whisper n'a pas de darija a proprement parler. Il transcrit
la darija parlee comme de l'arabe (graphie arabe), ou comme du francais quand
la phrase alterne les deux langues. Le NLU en aval accepte les deux graphies,
et le texte transcrit est renvoye a l'interface pour que l'utilisateur puisse
le corriger avant envoi.
"""
import os
import tempfile
import threading
from dataclasses import dataclass

MODELE = os.environ.get("WHISPER_MODEL", "small")

# Sous Windows sans mode developpeur, huggingface_hub avertit a chaque
# telechargement qu'il ne peut pas creer de liens symboliques dans son cache.
# C'est sans consequence (le cache marche, en copiant) : on le fait taire pour
# ne pas noyer les journaux de l'API.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Au-dela, la transcription sur CPU devient trop longue pour une interface de
# chat ; une question de pharmacie tient largement en une minute.
DUREE_MAX_S = 60
TAILLE_MAX_OCTETS = 10 * 1024 * 1024

LANGUES_ACCEPTEES = {"ar", "fr"}

# Amorce donnee au decodeur (initial_prompt) : quelques noms de medicaments
# courants au Maroc et le vocabulaire du domaine. Whisper conditionne sa
# transcription sur ce texte, ce qui l'aide a orthographier des noms propres
# qu'il n'aurait sinon aucune raison de privilegier.
AMORCE = (
    "Doliprane, Panadol, Efferalgan, Spasfon, Smecta, Amoxicilline, Augmentin, "
    "Voltarene, pharmacie, صيدلية, دوا."
)

_modele = None
_verrou = threading.Lock()


class ErreurAudio(ValueError):
    """Entree audio inexploitable : vide, trop longue, trop lourde, illisible."""


@dataclass
class Transcription:
    texte: str
    langue: str
    confiance_langue: float
    duree_audio: float


def _charger():
    # Import differe : faster-whisper tire ctranslate2 et onnxruntime, qu'il est
    # inutile de charger si personne n'utilise la voix.
    global _modele
    if _modele is None:
        with _verrou:
            if _modele is None:
                from faster_whisper import WhisperModel

                _modele = WhisperModel(MODELE, device="cpu", compute_type="int8")
    return _modele


def transcrire(contenu: bytes, langue: str | None = None) -> Transcription:
    if not contenu:
        raise ErreurAudio("Enregistrement vide.")
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise ErreurAudio("Enregistrement trop volumineux (10 Mo maximum).")
    if langue is not None and langue not in LANGUES_ACCEPTEES:
        raise ErreurAudio(f"Langue non prise en charge : {langue!r} (attendu : ar ou fr).")

    modele = _charger()

    # PyAV lit le conteneur d'apres son contenu (webm/opus de Chrome, mp4 de
    # Safari, wav...) ; un fichier temporaire est plus fiable qu'un flux memoire
    # pour les formats dont l'index est en fin de fichier.
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as f:
        f.write(contenu)
        chemin = f.name
    try:
        try:
            segments, info = modele.transcribe(
                chemin,
                language=langue,
                beam_size=5,
                initial_prompt=AMORCE,
                # filtre la voix (Silero VAD) : evite que le silence en debut ou
                # fin d'enregistrement ne soit "transcrit" en mots inventes
                vad_filter=True,
                condition_on_previous_text=False,
            )
            if info.duration > DUREE_MAX_S:
                raise ErreurAudio(f"Enregistrement trop long ({info.duration:.0f} s, {DUREE_MAX_S} s maximum).")
            texte = " ".join(s.text.strip() for s in segments).strip()
        except ErreurAudio:
            raise
        except Exception as e:  # conteneur illisible, codec inconnu...
            raise ErreurAudio(f"Audio illisible : {e}") from e
    finally:
        try:
            os.unlink(chemin)
        except OSError:
            pass

    if not texte:
        raise ErreurAudio("Je n'ai rien entendu. Rapproche-toi du micro et reessaie.")

    return Transcription(
        texte=texte,
        langue=info.language,
        confiance_langue=round(float(info.language_probability), 3),
        duree_audio=round(float(info.duration), 2),
    )


def modele_charge() -> bool:
    return _modele is not None


__all__ = ["ErreurAudio", "Transcription", "transcrire", "modele_charge", "MODELE"]
