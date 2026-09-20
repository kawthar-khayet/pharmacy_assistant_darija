"""Reconnaissance vocale (Whisper)."""
import pytest

from api.parole import (
    SEUIL_CONFIANCE_LANGUE,
    TAILLE_MAX_OCTETS,
    ErreurAudio,
    avertissement_langue,
    transcrire,
)


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


# Avertissement de relecture : la darija n'a pas de modele Whisper, une
# transcription incertaine doit etre signalee, pas maquillee en certitude.

def test_langue_sure_pas_d_avertissement():
    assert avertissement_langue("fr", 0.98) is None


def test_confiance_basse_invite_a_relire():
    message = avertissement_langue("ar", SEUIL_CONFIANCE_LANGUE - 0.1)
    assert message and "relis" in message.lower()


def test_langue_inattendue_signalee():
    """Une phrase en darija se fait regulierement etiqueter persan ou ourdou :
    le texte reste rendu, mais l'utilisateur doit savoir qu'il est douteux."""
    message = avertissement_langue("fa", 0.95)
    assert message and "fa" in message


# Transcription reelle : charge le modele Whisper.

@pytest.mark.lent
def test_transcrit_une_vraie_question(audio_fr):
    t = transcrire(audio_fr)
    assert t.langue == "fr"
    assert "doliprane" in t.texte.lower()
    assert t.duree_audio == pytest.approx(3.86, abs=0.2)
    assert t.avertissement is None


@pytest.mark.lent
def test_fichier_qui_n_est_pas_de_l_audio():
    with pytest.raises(ErreurAudio, match="illisible"):
        transcrire(b"ceci n'est pas un son" * 50)
