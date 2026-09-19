"""Scenarios de bout en bout sur l'API (NLU simule, tout le reste reel)."""
import json

import pytest


def json_strict(reponse):
    """Refuse NaN / Infinity, que json.dumps accepte mais que JSON interdit :
    un navigateur echouerait a lire la reponse."""
    def refuser(constante):
        raise ValueError(f"constante JSON invalide : {constante}")

    return json.loads(reponse.content, parse_constant=refuser)


# ------------------------------------------------------------------ sante

def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_schema_expose_les_8_intents(client):
    ids = {i["id"] for i in client.get("/schema").json()["intents"]}
    assert ids == {
        "disponibilite_medicament", "prix_remboursement", "alternative_moins_chere",
        "info_pharmacie", "posologie_information", "conseil_medical", "salutation", "hors_sujet",
    }


# ------------------------------------------------------------- scenarios chat

def test_texte_vide_refuse(client):
    assert client.post("/chat", json={"text": "   "}).status_code == 400


def test_prix_donne_prix_et_remboursement_des_deux_regimes(client, nlu):
    nlu("prix_remboursement", MEDICAMENT="doliprane", DOSAGE="1g")
    d = json_strict(client.post("/chat", json={"text": "chhal taman doliprane 1g"}))
    assert d["intent"] == "prix_remboursement"
    assert d["medicament_matches"][0]["nom_candidat"] == "DOLIPRANE"
    assert "DH" in d["reply"]
    assert "CNOPS" in d["reply"] and "CNSS" in d["reply"]


def test_disponibilite_sans_lieu_demande_la_ville_puis_propose_des_pharmacies(client, nlu):
    """Scenario multi-tours : la ville demandee au premier tour est comprise
    comme la reponse a cette question, pas comme une nouvelle demande."""
    nlu("disponibilite_medicament", MEDICAMENT="doliprane")
    tour1 = json_strict(client.post("/chat", json={"text": "wach kayn doliprane?"}))
    assert tour1["awaiting_localisation"] is True
    assert "ville" in tour1["reply"].lower()

    nlu("hors_sujet", LOCALISATION="Maarif")
    tour2 = json_strict(client.post(
        "/chat", json={"text": "Maarif", "session_id": tour1["session_id"]}
    ))
    assert tour2["awaiting_localisation"] is False
    assert len(tour2["pharmacie_matches"]) > 0
    assert {p["ville"] for p in tour2["pharmacie_matches"]} == {"Casablanca"}


def test_disponibilite_avec_lieu_repond_en_un_seul_tour(client, nlu):
    nlu("disponibilite_medicament", MEDICAMENT="doliprane", LOCALISATION="Rabat")
    d = json_strict(client.post("/chat", json={"text": "wach kayn doliprane f Rabat"}))
    assert d["awaiting_localisation"] is False
    assert d["pharmacie_matches"]


def test_question_hors_perimetre_avec_medicament_reconnu_montre_la_fiche(client, nlu):
    """'chno kaydir doliprane' peut etre classe hors sujet par le modele : le
    medicament reconnu ne doit pas etre jete au profit d'un refus."""
    nlu("hors_sujet", MEDICAMENT="Doliprane")
    d = json_strict(client.post("/chat", json={"text": "chno kaydir doliprane?"}))
    assert d["medicament_matches"]
    assert "DOLIPRANE" in d["reply"]
    assert "pas sur d'avoir bien compris" in d["reply"]


def test_medicament_introuvable_n_invente_pas_de_reponse(client, nlu):
    """Regression : 'qwerty' obtenait une reponse chiffree sur un vrai
    medicament, tire d'un rapprochement 'non_fiable'."""
    nlu("prix_remboursement", MEDICAMENT="qwerty")
    d = json_strict(client.post("/chat", json={"text": "chhal taman qwerty"}))
    assert d["medicament_matches"] == []
    assert "Je ne trouve pas" in d["reply"] and "DH" not in d["reply"]


def test_nom_approchant_presente_comme_hypothese(client, nlu):
    nlu("prix_remboursement", MEDICAMENT="Bidon")
    d = json_strict(client.post("/chat", json={"text": "chhal taman bidon"}))
    assert d["medicament_matches"][0]["confidence"] == "a_confirmer"
    assert d["reply"].startswith("Tu parles peut-etre de")


def test_posologie_ne_donne_jamais_de_dose(client, nlu):
    nlu("posologie_information", MEDICAMENT="doliprane")
    d = json_strict(client.post("/chat", json={"text": "kifach nakhod doliprane"}))
    assert "posologie" in d["reply"].lower()
    assert "pharmacien" in d["reply"].lower()


def test_hors_sujet_presente_ce_que_dwatalk_sait_faire(client, nlu):
    """Hors sujet ne veut pas dire incompris : on dit ce qu'on sait faire."""
    nlu("hors_sujet")
    d = client.post("/chat", json={"text": "chno akhbar lyoum"}).json()
    assert "assistant pharmacie" in d["reply"]
    assert "pas bien compris" not in d["reply"]


# ------------------------------------------------------- taxonomie v2

def test_conseil_medical_oriente_vers_un_professionnel(client, nlu):
    nlu("conseil_medical")
    d = json_strict(client.post("/chat", json={"text": "3andi sda3, ach ndir?"}))
    assert "pharmacien" in d["reply"] and "medecin" in d["reply"]
    # numeros verifies (ambassade de France au Maroc)
    assert "SAMU 141" in d["reply"] and "Protection civile 15" in d["reply"]
    assert "0801 000 180" in d["reply"]


def test_conseil_medical_ne_montre_jamais_de_fiche(client, nlu):
    """Meme si un medicament est cite, afficher sa fiche en reponse a un
    symptome passerait pour une recommandation."""
    nlu("conseil_medical", MEDICAMENT="doliprane")
    d = json_strict(client.post("/chat", json={"text": "3andi sda3, doliprane mzyan?"}))
    assert d["medicament_matches"] == []
    assert "DH" not in d["reply"]


def test_equivalents_moins_chers(client, nlu):
    nlu("alternative_moins_chere", MEDICAMENT="doliprane", DOSAGE="500mg")
    d = json_strict(client.post("/chat", json={"text": "kayn chi haja bhal doliprane 500mg rkhis?"}))
    alt = d["alternatives"]
    assert alt["reference"]["nom"] == "DOLIPRANE"
    prix = [e["ppv"] for e in alt["equivalents"]]
    assert prix and prix == sorted(prix)
    assert all(e["nom"] != "DOLIPRANE" for e in alt["equivalents"])
    assert "pharmacien" in d["reply"]


def test_equivalent_sans_medicament_demande_lequel(client, nlu):
    nlu("alternative_moins_chere")
    d = client.post("/chat", json={"text": "kayn chi dwa rkhis?"}).json()
    assert d["alternatives"] is None
    assert "quel medicament" in d["reply"].lower()


def test_equivalent_introuvable_le_dit(client, nlu):
    nlu("alternative_moins_chere", MEDICAMENT="smecta")
    d = client.post("/chat", json={"text": "badil l smecta?"}).json()
    assert d["alternatives"]["equivalents"] == []
    assert "pas trouve d'autre medicament" in d["reply"]


@pytest.mark.parametrize("ancienne, nouvelle", [
    ("autre", "hors_sujet"),
    ("commande_reservation", "disponibilite_medicament"),
    ("diagnostic", "hors_sujet"),   # intention inventee par le modele
])
def test_intention_inconnue_ou_ancienne_rabattue(client, nlu, ancienne, nouvelle):
    nlu(ancienne)
    assert client.post("/chat", json={"text": "?"}).json()["intent"] == nouvelle


def test_avertissement_sur_les_gardes(client, nlu):
    """L'annuaire est un instantane : toute reponse sur une garde doit inviter
    a confirmer par telephone."""
    nlu("info_pharmacie", LOCALISATION="Maarif")
    d = client.post("/chat", json={"text": "pharmacie de garde a Maarif"}).json()
    assert "garde changent chaque jour" in d["reply"]


def test_salutation(client, nlu):
    nlu("salutation")
    assert "Bonjour" in client.post("/chat", json={"text": "salam"}).json()["reply"]


def test_nlu_indisponible_renvoie_500_explicite(client, api, monkeypatch):
    def en_panne(texte):
        raise SystemExit("Le modele est momentanement surcharge. Reessaie dans quelques instants.")

    monkeypatch.setattr(api, "run_nlu", en_panne)
    r = client.post("/chat", json={"text": "wach kayn doliprane"})
    assert r.status_code == 500
    assert "surcharge" in r.json()["detail"]


# ---------------------------------------------------------- recherches

def test_recherche_medicament_tolere_les_fautes(client):
    d = json_strict(client.get("/medicaments", params={"q": "dolipran", "limit": 3}))
    assert d["resultats"][0]["nom_candidat"] == "DOLIPRANE"
    assert d["resultats"][0]["confidence"] == "auto"


def test_recherche_medicament_vide(client):
    assert client.get("/medicaments", params={"q": " "}).json()["resultats"] == []


def test_recherche_pharmacies_par_quartier(client):
    d = json_strict(client.get("/pharmacies", params={"ville": "Maarif", "limit": 5}))
    assert d["resultats"]
    assert all(p["ville"] == "Casablanca" for p in d["resultats"])


def test_recherche_pharmacies_sans_critere(client):
    assert client.get("/pharmacies").json()["resultats"] == []


def test_lieu_inconnu_ne_renvoie_pas_une_liste_au_hasard(client):
    d = client.get("/pharmacies", params={"ville": "Zzzqqqville"}).json()
    assert d["resultats"] == []


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


def test_audio_inexploitable_renvoie_422(client, api, monkeypatch):
    from api.parole import ErreurAudio

    def refuser(contenu, langue=None):
        raise ErreurAudio("Je n'ai rien entendu.")

    monkeypatch.setattr(api, "transcrire", refuser)
    r = client.post("/transcription", files={"fichier": ("q.wav", b"x", "audio/wav")})
    assert r.status_code == 422
    assert "rien entendu" in r.json()["detail"]


def test_chat_audio_enchaine_transcription_et_nlu(client, api, nlu, monkeypatch, audio_fr):
    from api.parole import Transcription

    monkeypatch.setattr(
        api, "transcrire",
        lambda contenu, langue=None: Transcription("chhal taman doliprane", "fr", 0.9, 2.0),
    )
    nlu("prix_remboursement", MEDICAMENT="doliprane")
    d = client.post("/chat/audio", files={"fichier": ("q.wav", audio_fr, "audio/wav")}).json()
    assert d["transcription"]["texte"] == "chhal taman doliprane"
    assert d["input"] == "chhal taman doliprane"
    assert d["intent"] == "prix_remboursement"


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


# ------------------------------------------------------- formulation

@pytest.mark.parametrize("variante, attendu", [
    ({}, None),
    ({"taux_remboursement_cnss": 70.0}, "rembourse a 70% (CNSS)"),
    ({"taux_remboursement_cnops": 70.0, "taux_remboursement_cnss": 70.0}, "rembourse a 70% (CNOPS et CNSS)"),
    ({"taux_remboursement_cnss": 0.0}, "non rembourse (CNSS)"),
    ({"taux_remboursement_cnops": 70.0, "taux_remboursement_cnss": 0.0}, "remboursement : CNOPS 70%, CNSS 0%"),
])
def test_formulation_du_remboursement(api, variante, attendu):
    assert api.remboursement_phrase(variante, {}) == attendu


def test_formulation_du_remboursement_ignore_nan(api):
    """pandas represente une case vide par NaN : elle ne doit pas etre lue
    comme un taux, et on se rabat sur l'autre variante."""
    assert api.remboursement_phrase(
        {"taux_remboursement_cnss": float("nan")}, {"taux_remboursement_cnss": 70.0}
    ) == "rembourse a 70% (CNSS)"
