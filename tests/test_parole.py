"""Reconnaissance vocale (Whisper)."""
import pytest

from api.parole import TAILLE_MAX_OCTETS, ErreurAudio, transcrire


# Controles faits AVANT le chargement du modele : rapides, toujours executes.

def test_audio_vide_refuse():
    with pytest.raises(ErreurAudio, match="vide"):
        transcrire(b"")


def test_audio_trop_lourd_refuse():
    with pytest.raises(ErreurAudio, match="volumineux"):
        transcrire(b"0" * (TAILLE_MAX_OCTETS + 1))


def test_langue_non_prise_en_charge_refusee(audio_fr):
    with pytest.raises(ErreurAudio, match="Langue"):
        transcrire(audio_fr, langue="en")


# Transcription reelle : charge le modele Whisper.

@pytest.mark.lent
def test_transcrit_une_vraie_question(audio_fr):
    t = transcrire(audio_fr)
    assert t.langue == "fr"
    assert "doliprane" in t.texte.lower()
    assert t.duree_audio == pytest.approx(3.86, abs=0.2)


@pytest.mark.lent
def test_fichier_qui_n_est_pas_de_l_audio():
    with pytest.raises(ErreurAudio, match="illisible"):
        transcrire(b"ceci n'est pas un son" * 50)
