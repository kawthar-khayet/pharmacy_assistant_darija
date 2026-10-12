"""Scenarios de bout en bout sur l'API : LLM simule, tout le reste reel (bases
de data/clean, fiches, recherche). Les scenarios du chat sont dans test_rag.py."""
import json
import re

import pytest


def json_strict(reponse):
    """Refuse NaN / Infinity, que json.dumps accepte mais que JSON interdit :
    un navigateur echouerait a lire la reponse."""
    def refuser(constante):
        raise ValueError(f"constante JSON invalide : {constante}")

    return json.loads(reponse.content, parse_constant=refuser)


def poser(client, texte, session_id=None):
    r = client.post("/chat", json={"text": texte, "session_id": session_id})
    assert r.status_code == 200, r.text
    return json_strict(r)


# ------------------------------------------------------------------ sante

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_texte_vide_refuse(client):
    assert client.post("/chat", json={"text": "   "}).status_code == 400


# -------------------------------------------------------------------- chat

def test_chat_renvoie_la_reponse_du_llm_et_ses_sources(client, llm):
    llm(reponse="Doliprane 1 g : 13.10 DH", medicaments=["doliprane"], question="Prix de Doliprane 1 g ?")
    d = poser(client, "ch7al taman doliprane 1g")
    assert d["reply"] == "Doliprane 1 g : 13.10 DH"
    assert d["langue"] == "ary_lat" and d["situation"] == "repondre"
    assert "med:DOLIPRANE" in d["sources"]
    assert d["requete"]["medicaments"] == ["doliprane"]


def test_chat_pharmacies_en_fiches(client, llm):
    llm(lieu="maarif casa", pharmacies=True)
    d = poser(client, "fin kayna pharmacie f maarif casa")
    assert len(d["pharmacie_matches"]) == 5
    assert all(p["distance_km"] is not None for p in d["pharmacie_matches"])


def test_urgence_detectee_sans_appeler_le_llm(client):
    """Le filet de mots-cles repond seul : le garde-fou de conftest ferait
    echouer le test si le LLM etait appele."""
    d = poser(client, "wlidi bla3 chi 10 d l7bob dyal doliprane")
    assert d["urgence"] == "intoxication"
    assert "0801 000 180" in d["reply"]


def test_index_absent_renvoie_503(client, monkeypatch):
    import nlp.moteur

    class Vide:
        def count(self):
            return 0

    monkeypatch.setattr(nlp.moteur, "collection", lambda: Vide())
    r = client.post("/chat", json={"text": "prix doliprane"})
    assert r.status_code == 503 and "nlp.rag.index" in r.json()["detail"]


# --------------------------------------------------------- pages de l'interface

def test_recherche_medicament_tolere_les_fautes(client):
    d = json_strict(client.get("/medicaments", params={"q": "dolipran", "limit": 3}))
    assert d["resultats"][0]["nom_candidat"] == "DOLIPRANE"
    assert d["resultats"][0]["confidence"] == "auto"


def test_recherche_medicament_sans_resultat_non_fiable(client):
    resultats = client.get("/medicaments", params={"q": "doliprane"}).json()["resultats"]
    assert all(r["confidence"] != "non_fiable" for r in resultats)
    assert client.get("/medicaments", params={"q": "qwerty asdf"}).json()["resultats"] == []


def test_recherche_medicament_vide(client):
    assert client.get("/medicaments", params={"q": " "}).json()["resultats"] == []


def test_medicaments_portent_leur_classification_atc(client):
    resultat = client.get("/medicaments", params={"q": "doliprane"}).json()["resultats"][0]
    assert "N02BE" in [c["code"] for c in resultat["classes_atc"]]
    assert resultat["securite_disponible"] is True


def test_recherche_pharmacies_par_quartier(client):
    d = json_strict(client.get("/pharmacies", params={"ville": "Maarif", "limit": 5}))
    assert len(d["resultats"]) == 5
    assert all(p["ville"] == "Casablanca" for p in d["resultats"])


def test_recherche_pharmacies_par_nom_homonyme_les_montre_toutes(client):
    d = json_strict(client.get("/pharmacies", params={"q": "ibn sina", "limit": 30}))
    assert len({p["ville"] for p in d["resultats"]}) > 5
    assert "precise la ville" in d["note"]


def test_recherche_pharmacies_sans_critere(client):
    assert client.get("/pharmacies").json()["resultats"] == []


def test_pharmacies_lieu_inconnu(client):
    d = client.get("/pharmacies", params={"ville": "Zzzqqqville"}).json()
    assert d["resultats"] == [] and "non reconnu" in d["note"]


def test_pharmacies_autour_d_un_point_sont_triees_par_distance(client):
    resultats = json_strict(client.get(
        "/pharmacies", params={"lat": 33.5731, "lon": -7.5898, "limit": 5}))["resultats"]
    assert len(resultats) == 5
    distances = [p["distance_km"] for p in resultats]
    assert distances == sorted(distances) and distances[0] < 5


def test_securite_renvoie_les_rubriques_d_une_molecule(client):
    r = client.get("/securite", params={"dci": "PARACETAMOL"})
    assert r.status_code == 200
    corps = r.json()
    assert corps["code_atc"] == "N02BE01"
    assert "contre_indications" in corps["rubriques"]
    assert corps["source_url"].startswith("https://base-donnees-publique.medicaments.gouv.fr")
    assert "signalement.social-sante" not in corps["rubriques"]["effets_indesirables"]


def test_securite_404_sur_une_molecule_inconnue(client):
    assert client.get("/securite", params={"dci": "QWERTYZOL"}).status_code == 404


def test_la_fiche_de_securite_repond_meme_sans_resume(client, monkeypatch):
    from api import resume

    monkeypatch.setattr(resume, "resumer", lambda *a, **k: None)
    corps = client.get("/securite", params={"dci": "PARACETAMOL", "langue": "ary_lat"}).json()
    assert corps["resume"] is None
    assert corps["rubriques"]["contre_indications"]


# --------------------------------------------------------------- voix

def test_transcription_renvoie_le_texte(client, api, monkeypatch, audio_fr):
    from api.parole import Transcription

    monkeypatch.setattr(
        api, "transcrire",
        lambda contenu, langue=None: Transcription("wach kayn doliprane", "ar", 0.9, 2.1),
    )
    r = client.post("/transcription", files={"fichier": ("q.wav", audio_fr, "audio/wav")})
    assert r.status_code == 200
    assert r.json()["texte"] == "wach kayn doliprane"


def test_transcription_remonte_l_avertissement(client, api, monkeypatch, audio_fr):
    """Une transcription douteuse reste rendue, mais l'interface doit pouvoir
    inviter a la relire : c'est le cas courant en darija."""
    from api.parole import Transcription

    monkeypatch.setattr(
        api, "transcrire",
        lambda contenu, langue=None: Transcription(
            "wach kayn doliprane", "ar", 0.3, 2.1, avertissement="Transcription incertaine : relis le texte.",
        ),
    )
    d = client.post("/transcription", files={"fichier": ("q.wav", audio_fr, "audio/wav")}).json()
    assert "relis" in d["avertissement"].lower()


def test_audio_inexploitable_renvoie_422(client, api, monkeypatch):
    from api.parole import ErreurAudio

    def refuser(contenu, langue=None):
        raise ErreurAudio("Je n'ai rien entendu.")

    monkeypatch.setattr(api, "transcrire", refuser)
    r = client.post("/transcription", files={"fichier": ("q.wav", b"x", "audio/wav")})
    assert r.status_code == 422
    assert "rien entendu" in r.json()["detail"]


def test_chat_audio_enchaine_transcription_et_reponse(client, api, llm, monkeypatch, audio_fr):
    from api.parole import Transcription

    monkeypatch.setattr(
        api, "transcrire",
        lambda contenu, langue=None: Transcription("chhal taman doliprane 1g", "fr", 0.9, 2.0),
    )
    llm(reponse="Doliprane 1 g : 13.10 DH", medicaments=["doliprane"])
    d = client.post("/chat/audio", files={"fichier": ("q.wav", audio_fr, "audio/wav")}).json()
    assert d["transcription"]["texte"] == "chhal taman doliprane 1g"
    assert d["input"] == "chhal taman doliprane 1g"
    assert "DH" in d["reply"]


# ---------------------------------------------------------------- CORS

def test_cors_autorise_le_front(client):
    r = client.options("/chat", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
    })
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_refuse_un_site_quelconque(client):
    r = client.options("/chat", headers={
        "Origin": "https://site-malveillant.example", "Access-Control-Request-Method": "POST",
    })
    assert "access-control-allow-origin" not in r.headers


# ------------------------------------------------------- resume de la notice

def test_le_resume_vient_du_cache_sans_appeler_le_modele(monkeypatch, tmp_path):
    """Une molecule a un texte stable : le resume est paye une fois, puis relu."""
    from api import resume

    cache = tmp_path / "resumes.json"
    cache.write_text('{"PARACETAMOL|ary_lat": "Ila 3andek maradh d lkebda, ma takhdoch."}',
                     encoding="utf-8")
    monkeypatch.setattr(resume, "CACHE_PATH", cache)
    monkeypatch.setattr(resume, "_appeler_gemini",
                        lambda *a: pytest.fail("le cache aurait du suffire"))

    produit = resume.resumer(
        {"dci": "PARACETAMOL", "rubriques": {"contre_indications": "Ne prenez jamais…"}},
        "ary_lat",
    )
    assert produit.startswith("Ila 3andek")


def test_pas_de_resume_sans_cle_api(monkeypatch, tmp_path):
    from api import resume

    monkeypatch.setattr(resume, "CACHE_PATH", tmp_path / "vide.json")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert resume.resumer(
        {"dci": "X", "rubriques": {"contre_indications": "Ne prenez jamais…"}}, "ary_lat"
    ) is None


def test_un_modele_qui_repond_rien_ne_produit_pas_de_resume(monkeypatch, tmp_path):
    from api import resume

    monkeypatch.setattr(resume, "CACHE_PATH", tmp_path / "vide.json")
    monkeypatch.setenv("GEMINI_API_KEY", "cle-de-test")
    monkeypatch.setattr(resume, "_appeler_gemini", lambda *a: "RIEN")
    assert resume.resumer(
        {"dci": "X", "rubriques": {"contre_indications": "texte"}}, "ary_lat"
    ) is None


def test_le_resume_ne_recoit_que_le_texte_officiel(monkeypatch, tmp_path):
    """Le modele ne voit que les rubriques : rien de la question du patient."""
    from api import resume

    vus = {}
    monkeypatch.setattr(resume, "CACHE_PATH", tmp_path / "vide.json")
    monkeypatch.setenv("GEMINI_API_KEY", "cle-de-test")
    monkeypatch.setattr(
        resume, "_appeler_gemini",
        lambda cle, consigne, texte: vus.update(consigne=consigne, texte=texte) or "Resume.",
    )
    resume.resumer(
        {"dci": "X", "rubriques": {"contre_indications": "allergie au paracetamol"}}, "ary_lat"
    )
    assert vus["texte"] == "[contre_indications]\nallergie au paracetamol"
    assert "darija" in vus["consigne"]


# --------------------------------------------- explications simples (chat)

def test_l_explication_vient_du_cache_sans_appeler_le_modele(monkeypatch, tmp_path):
    from api import resume

    cache = tmp_path / "explications.json"
    cache.write_text('{"PARACETAMOL|ary_lat": {"indications": "Kaydir l s-skhana."}}', encoding="utf-8")
    monkeypatch.setattr(resume, "EXPLICATIONS_PATH", cache)
    monkeypatch.setattr(resume, "_appeler_gemini",
                        lambda *a, **k: pytest.fail("le cache aurait du suffire"))
    produit = resume.expliquer({"dci": "PARACETAMOL", "rubriques": {"indications": "Fievre."}}, "ary_lat")
    assert produit == {"indications": "Kaydir l s-skhana."}


def test_l_explication_ne_garde_que_les_rubriques_fournies(monkeypatch, tmp_path):
    from api import resume

    monkeypatch.setattr(resume, "EXPLICATIONS_PATH", tmp_path / "vide.json")
    monkeypatch.setenv("GEMINI_API_KEY", "cle-de-test")
    monkeypatch.setattr(resume, "_appeler_gemini", lambda *a, **k: json.dumps(
        {"indications": "Kaydir l s-skhana.", "posologie": "2 comprimes", "precautions": None}))
    produit = resume.expliquer({"dci": "X", "rubriques": {"indications": "Fievre.",
                                                          "precautions": "Foie."}}, "ary_lat")
    assert produit == {"indications": "Kaydir l s-skhana."}
    assert json.loads((tmp_path / "vide.json").read_text(encoding="utf-8")) == {"X|ary_lat": produit}


def test_une_explication_illisible_n_est_pas_gardee(monkeypatch, tmp_path):
    from api import resume

    monkeypatch.setattr(resume, "EXPLICATIONS_PATH", tmp_path / "vide.json")
    monkeypatch.setenv("GEMINI_API_KEY", "cle-de-test")
    monkeypatch.setattr(resume, "_appeler_gemini", lambda *a, **k: "pas du json")
    assert resume.expliquer({"dci": "X", "rubriques": {"indications": "Fievre."}}, "ary_lat") is None
    assert not (tmp_path / "vide.json").exists()
