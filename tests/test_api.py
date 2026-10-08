"""Scenarios de bout en bout sur l'API : analyse simulee, tout le reste reel
(bases de data/clean, outils, redaction)."""
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


def test_schema_expose_le_vocabulaire_de_l_analyse(client):
    schema = client.get("/schema").json()
    assert {"prix", "remboursement", "pharmacies_lieu", "posologie"} <= set(schema["demandes"])
    assert "urgence" in schema["situations"]
    # la posologie n'a besoin de rien : la reponse est toujours "demande a ton medecin"
    assert schema["demandes"]["posologie"]["besoin"] == []


def test_texte_vide_refuse(client):
    assert client.post("/chat", json={"text": "   "}).status_code == 400


# ------------------------------------------------------------- medicaments

def test_prix_seul_ne_parle_pas_de_remboursement(client, analyse):
    analyse(demandes=["prix"], medicaments=[{"nom": "doliprane", "dosage": "1g"}])
    d = poser(client, "prix du doliprane 1g")
    assert "13,10 DH" in d["reply"]
    assert "rembours" not in d["reply"].lower()
    assert d["medicament_matches"] == []          # plus de fiche complete dans le chat


def test_prix_sans_dosage_donne_le_prix_par_dosage(client, analyse):
    analyse(demandes=["prix"], medicaments=[{"nom": "doliprane"}])
    reply = poser(client, "prix du doliprane")["reply"]
    assert "selon le dosage" in reply
    assert "- 1 g : 13,10 DH a 13,70 DH" in reply


@pytest.mark.parametrize("dosage", ["1000", "1000mg", "1000g"])
def test_prix_dosage_ecrit_en_mg(client, analyse, dosage):
    """La base ecrit "1 G" : 1000 mg doit donner les memes prix, sans redemander."""
    analyse(demandes=["prix"], medicaments=[{"nom": "doliprane", "dosage": dosage}])
    reply = poser(client, f"chhal taman doliprane {dosage}")["reply"]
    assert "13,10 DH" in reply and "13,70 DH" in reply
    assert "selon le dosage" not in reply


def test_prix_dosage_trouve_liste_toutes_ses_formes(client, analyse):
    """Doliprane 500 mg a 4 formes : on les liste au lieu de redemander le dosage."""
    analyse(demandes=["prix"], medicaments=[{"nom": "doliprane", "dosage": "500mg"}])
    reply = poser(client, "prix du doliprane 500")["reply"]
    assert "9,60 DH" in reply and "14,80 DH" in reply
    assert "selon le dosage" not in reply


def test_prix_dosage_absent_le_dit_et_liste_les_dosages(client, analyse):
    analyse(demandes=["prix"], medicaments=[{"nom": "doliprane", "dosage": "2g"}])
    reply = poser(client, "prix du doliprane 2g")["reply"]
    assert "Je ne trouve pas Doliprane en 2g" in reply
    assert "- 1 g : 13,10 DH a 13,70 DH" in reply


def test_remboursement_demande_le_regime_puis_le_retient(client, analyse):
    analyse(situation="preciser", demandes=["remboursement"], medicaments=[{"nom": "augmentin", "dosage": "1g"}])
    d = poser(client, "augmentin 1g kayt3awed ?")
    assert "CNOPS" in d["reply"] and "CNSS" in d["reply"]
    assert d["attend"] == ["regime"]

    analyse(demandes=["remboursement"], medicaments=[{"nom": "augmentin", "dosage": "1g"}], regime="cnss")
    d = poser(client, "cnss", d["session_id"])
    assert "Remboursement CNSS" in d["reply"] and "70 %" in d["reply"]

    # le patient ne redit pas son regime : la conversation s'en souvient
    analyse(situation="preciser", demandes=["remboursement"], medicaments=[{"nom": "smecta"}])
    d = poser(client, "w smecta ?", d["session_id"])
    assert "Remboursement CNSS de Smecta" in d["reply"]
    assert d["attend"] == []


def test_sans_assurance_on_paie_le_prix_public(client, analyse):
    analyse(demandes=["remboursement"], medicaments=[{"nom": "doliprane"}], regime="aucun")
    assert "prix public" in poser(client, "ma3ndich tamin, doliprane kayt3awed?")["reply"]


def test_formes_et_dosages(client, analyse):
    analyse(demandes=["formes_dosages"], medicaments=[{"nom": "doliprane", "forme": "sirop"}])
    reply = poser(client, "doliprane sirop kayn ?")["reply"]
    assert "Je ne trouve pas Doliprane en sirop" in reply
    assert "suppositoire" in reply


def test_medicament_introuvable_n_invente_rien(client, analyse):
    analyse(demandes=["prix"], medicaments=[{"nom": "qwertyzol"}])
    reply = poser(client, "prix qwertyzol")["reply"]
    assert "Je ne trouve pas « qwertyzol »" in reply
    assert "DH" not in reply


def test_medicament_non_nomme_le_bot_demande_lequel(client, analyse):
    analyse(situation="preciser", demandes=["prix"], langue="ary_lat")
    d = poser(client, "chhal taman had dwa ?")
    assert d["attend"] == ["medicament"]
    assert "ina dwa" in d["reply"]


# ----------------------------------------------------------------- posologie

def test_posologie_renvoie_toujours_au_medecin(client, analyse):
    analyse(demandes=["posologie"], medicaments=[{"nom": "amoxil", "dosage": "1g"}])
    reply = poser(client, "comment prendre amoxil 1g ?")["reply"]
    assert "pose la question a ton medecin" in reply
    assert not re.search(r"\d+\s*(fois|comprim|mg|g\b)", reply)


def test_posologie_ne_bloque_pas_les_autres_demandes(client, analyse):
    analyse(demandes=["prix", "posologie"], medicaments=[{"nom": "doliprane", "dosage": "1g"}])
    reply = poser(client, "taman doliprane w kifach nakhdo ?")["reply"]
    assert "DH" in reply and "medecin" in reply


# ------------------------------------------------------------------- notice

def test_effets_indesirables_seulement_la_rubrique_demandee(client, analyse):
    analyse(demandes=["effets_indesirables"], medicaments=[{"nom": "doliprane"}])
    d = poser(client, "effets secondaires du doliprane ?")
    assert "Effets indesirables de Doliprane" in d["reply"]
    assert list(d["securite"]["rubriques"]) == ["effets_indesirables"]
    assert "signalement.social-sante" not in d["reply"]


def test_molecule_sans_notice_renvoie_au_pharmacien(client, analyse):
    analyse(demandes=["indications"], medicaments=[{"nom": "smecta"}])
    d = poser(client, "chno kaydir smecta ?")
    assert "pharmacien" in d["reply"]
    assert d["securite"] is None


# ---------------------------------------------------------------- pharmacies

def test_pharmacies_les_plus_proches_d_un_quartier(client, analyse):
    analyse(demandes=["pharmacies_lieu"], lieu="f m3arif", langue="ary_lat")
    d = poser(client, "fin kayna pharmacie f m3arif ?")
    cartes = d["pharmacie_matches"]
    assert len(cartes) == 5
    assert all(c["ville"] == "Casablanca" for c in cartes)
    distances = [c["distance_km"] for c in cartes]
    assert distances == sorted(distances) and distances[0] < 1
    # la version courte laisse la liste aux fiches
    assert cartes[0]["nom"] in d["reply"] and cartes[0]["nom"] not in d["reply_court"]
    assert not any(n.startswith(("Para", "Drogu")) for n in (c["nom"] for c in cartes))


def test_grande_ville_sans_quartier_demande_le_quartier(client, analyse):
    analyse(demandes=["pharmacies_lieu"], lieu="casa")
    d = poser(client, "pharmacie a casa")
    assert "quel quartier" in d["reply"]
    assert d["pharmacie_matches"] == [] and d["awaiting_localisation"] is True


def test_quartier_homonyme_demande_la_ville_puis_se_souvient(client, analyse):
    analyse(demandes=["pharmacies_lieu"], lieu="agdal")
    d = poser(client, "pharmacie agdal")
    assert "Rabat" in d["reply"] and "laquelle" in d["reply"]

    analyse(demandes=["pharmacies_lieu"], lieu="rabat")
    d = poser(client, "rabat", d["session_id"])          # ville retenue par la session
    analyse(demandes=["pharmacies_lieu"], lieu="agdal")
    d = poser(client, "f agdal", d["session_id"])
    assert d["pharmacie_matches"] and d["pharmacie_matches"][0]["ville"] == "Rabat"


def test_garde_avoue_ne_pas_connaitre_le_tour_de_garde(client, analyse):
    analyse(demandes=["pharmacie_garde"], lieu="casa")
    d = poser(client, "pharmacie de garde casa")
    assert "tour de garde" in d["reply"]
    assert "141" not in d["reply"]          # le 141 est le SAMU, pas un service de garde
    assert d["pharmacie_matches"] and all(c["garde"] for c in d["pharmacie_matches"])


def test_pharmacie_homonyme_demande_la_ville(client, analyse):
    analyse(demandes=["info_pharmacie"], pharmacie="ibn sina")
    d = poser(client, "fin kayna pharmacie ibn sina ?")
    assert "plusieurs villes" in d["reply"]
    assert d["pharmacie_matches"] == []


def test_pharmacie_avec_sa_ville_repond_directement(client, analyse):
    analyse(demandes=["info_pharmacie"], pharmacie="ibn sina", lieu="rabat")
    d = poser(client, "pharmacie ibn sina a rabat")
    assert d["pharmacie_matches"][0]["nom"] == "Pharmacie Ibn Sina"
    assert d["pharmacie_matches"][0]["ville"] == "Rabat"


def test_lieu_inconnu_ne_renvoie_pas_une_liste_au_hasard(client, analyse):
    analyse(demandes=["pharmacies_lieu"], lieu="zzzqqqville")
    d = poser(client, "pharmacie a zzzqqqville")
    assert d["pharmacie_matches"] == []
    assert "Je ne connais pas" in d["reply"]


# ------------------------------------------------------------ conseil symptome

def test_conseil_cite_la_molecule_jamais_une_marque(client, analyse):
    analyse(situation="conseil_symptome", symptomes=["fievre_legere"], patient="adulte")
    reply = poser(client, "j'ai un peu de fievre")["reply"]
    assert "paracetamol" in reply and "3 jours" in reply
    assert "DOLIPRANE" not in reply.upper()


@pytest.mark.parametrize("champs", [{"patient": "enfant"}, {"patient": "bebe"}, {"grossesse": "oui"}])
def test_conseil_enfant_bebe_grossesse_vers_un_professionnel(client, analyse, champs):
    analyse(situation="conseil_symptome", symptomes=["fievre_legere"], **champs)
    reply = poser(client, "fievre")["reply"]
    assert "paracetamol" not in reply
    assert "pharmacien" in reply or "medecin" in reply


def test_conseil_symptome_qui_dure_vers_le_medecin(client, analyse):
    analyse(situation="conseil_symptome", symptomes=["mal_de_tete"], duree_jours=10)
    reply = poser(client, "mal de tete depuis 10 jours")["reply"]
    assert "medecin" in reply and "paracetamol" not in reply


# ------------------------------------------------------------------ urgences

def test_urgence_detectee_sans_appeler_le_llm(client):
    """Le filet de mots-cles repond seul : le garde-fou de conftest ferait
    echouer le test si le LLM etait appele."""
    d = poser(client, "wlidi bla3 chi 10 d l7bob dyal doliprane")
    assert d["urgence"] == "intoxication"
    assert "0801 000 180" in d["reply"]


def test_urgence_reconnue_par_le_llm(client, analyse):
    analyse(situation="urgence", urgence_type="detresse", demandes=["prix"])
    d = poser(client, "mon pere a du mal, il ne va pas bien du tout")
    assert d["urgence"] == "detresse" and "141" in d["reply"]
    assert "DH" not in d["reply"]


def test_llm_indisponible_reste_poli_et_donne_les_urgences(client, monkeypatch):
    import nlp.moteur
    from nlp.llm import LLMIndisponible

    def panne(*a, **k):
        raise LLMIndisponible("gemini : quota ; groq : pas de cle")

    monkeypatch.setattr(nlp.moteur, "analyser", panne)
    d = poser(client, "prix doliprane")
    assert d["situation"] == "indisponible"
    assert "Reessaie" in d["reply"] and "141" in d["reply"]


# -------------------------------------------------------- situations simples

@pytest.mark.parametrize("situation, extrait", [
    ("salutation", "Bonjour"),
    ("hors_sujet", "assistant pharmacie"),
    ("pas_d_info", "Je ne suis pas une pharmacie"),
    ("incompris", "reformuler"),
    ("medical", "medecin"),
])
def test_situations_sans_demande(client, analyse, situation, extrait):
    analyse(situation=situation)
    assert extrait in poser(client, "message")["reply"]


def test_reponse_dans_la_langue_de_la_question(client, analyse):
    analyse(demandes=["prix"], medicaments=[{"nom": "دوليبران", "dosage": "1g"}], langue="ary_ar")
    d = poser(client, "شحال تمن دوليبران 1g ؟")
    assert d["langue"] == "ary_ar"
    assert "درهم" in d["reply"]


def test_l_historique_est_transmis_a_l_analyse(client, analyse):
    appels = analyse(situation="salutation", langue="ary_lat")
    d = poser(client, "salam")
    poser(client, "f maarif", d["session_id"])
    assert appels[1]["historique"][0] == {"role": "user", "contenu": "salam"}
    assert appels[1]["historique"][1]["role"] == "assistant"


def test_une_analyse_invalide_est_corrigee_et_signalee(client, analyse):
    analyse(situation="repondre", demandes=["disponibilite"], medicaments=[{"nom": "doliprane"}])
    d = poser(client, "wach kayn doliprane")
    assert d["situation"] == "pas_d_info"
    assert any("disponibilite" in c for c in d["validation_errors"])


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


def test_chat_audio_enchaine_transcription_et_reponse(client, api, analyse, monkeypatch, audio_fr):
    from api.parole import Transcription

    monkeypatch.setattr(
        api, "transcrire",
        lambda contenu, langue=None: Transcription("chhal taman doliprane 1g", "fr", 0.9, 2.0),
    )
    analyse(demandes=["prix"], medicaments=[{"nom": "doliprane", "dosage": "1g"}], langue="ary_lat")
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
