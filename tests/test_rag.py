"""Le RAG, etape par etape : fiches, comprehension, recherche, moteur.

LLM et embeddings simules (voir conftest.py) ; les bases de data/clean, les
fiches et les filtres de l'index sont reels.
"""
import pytest

from nlp.moteur import Session, repondre
from nlp.rag.comprendre import en_requete
from nlp.rag.fiches import telephone
from nlp.rag.recherche import Requete, chercher


def textes(trouve, type_=None):
    return [f["texte"] for f in trouve.fiches if type_ is None or f["type"] == type_]


# ------------------------------------------------------------------ fiches

def test_fiche_medicament_porte_prix_et_remboursement(fiches):
    doliprane = next(f for f in fiches if f["id"] == "med:DOLIPRANE")
    assert "Molécule (DCI) : PARACETAMOL" in doliprane["texte"]
    assert "prix public 13.10 DH" in doliprane["texte"]
    assert "par la CNOPS" in doliprane["texte"] and "par la CNSS" in doliprane["texte"]
    assert doliprane["meta"]["dci"] == "PARACETAMOL"


def test_notice_coupee_en_morceaux_titres(fiches):
    morceaux = [f for f in fiches if f["id"].startswith("notice:PARACETAMOL:effets_indesirables:")]
    assert len(morceaux) > 1
    for m in morceaux:
        assert m["texte"].startswith("Notice de la molécule PARACETAMOL — effets indésirables")
        assert len(m["texte"]) < 2500


def test_fiche_conseil_cite_des_noms_commerciaux_pour_adulte_et_enfant(fiches):
    fievre = next(f for f in fiches if f["id"] == "conseil:fievre_legere")["texte"]
    adulte, enfant = fievre.split("Médicaments à proposer pour un ENFANT")
    assert "DOLIPRANE (paracetamol)" in adulte and "grossesse : oui" in adulte
    # pour l'enfant : la presentation et son poids, lus dans la notice
    assert "DOLIPRANE" in enfant and "kg" in enfant and "(enfant," in enfant
    assert "Signes d'alerte" in fievre


def test_fiche_conseil_sans_medicament_pour_enfant_le_dit(fiches):
    rhume = next(f for f in fiches if f["id"] == "conseil:rhume")["texte"]
    assert "Pour un ENFANT : aucun médicament dans nos données" in rhume
    assert "prix absent de nos données" in rhume          # sprays hors de la base marocaine
    # les comprimes a la pseudoephedrine sont dans la proposition, jamais dans une fiche
    assert not any(nom in rhume for nom in ("DOLIRHUME", "RHUMAGRIP", "ACTIFED", "HUMEX RHUME"))


def test_aucune_fiche_conseil_ne_cite_un_medicament_a_verifier(fiches):
    conseils = " ".join(f["texte"] for f in fiches if f["type"] == "conseil")
    for interdit in ("FORTRANS", "AKINDEX", "DRILL TOUX SECHE", "A VERIFIER", "A RETIRER"):
        assert interdit not in conseils, interdit


def test_ids_uniques(fiches):
    assert len({f["id"] for f in fiches}) == len(fiches)


@pytest.mark.parametrize("brut, attendu", [("528842597", "0528842597"), ("0661234567", "0661234567"), (None, None)])
def test_telephone_retrouve_son_zero(brut, attendu):
    assert telephone(brut) == attendu


# ------------------------------------------------------------ comprehension

def test_json_du_llm_mal_forme_prend_les_valeurs_par_defaut():
    r = en_requete({"medicaments": "doliprane", "lieu": "  ", "pharmacies": "oui", "question": None},
                   "ch7al taman doliprane")
    assert r == Requete(question="ch7al taman doliprane")


def test_json_du_llm_bien_forme():
    r = en_requete({"question": "Pharmacie de nuit à Agdal ?", "medicaments": [" dolipran ", 3],
                    "lieu": "agdal rabat", "pharmacies": True, "garde": True}, "x")
    assert r.medicaments == ["dolipran"] and r.lieu == "agdal rabat" and r.garde and r.pharmacies


# ---------------------------------------------------------------- recherche

def test_medicament_reconnu_malgre_la_faute(index):
    trouve = chercher(Requete("Prix de Doliprane ?", medicaments=["dolipran"]))
    assert trouve.fiches[0]["id"] == "med:DOLIPRANE"
    # avec la notice de SA molecule
    assert any(f["id"].startswith("notice:PARACETAMOL:") for f in trouve.fiches)


def test_medicament_en_lettres_arabes(index):
    trouve = chercher(Requete("Prix de Doliprane ?", medicaments=["دوليبران"]))
    assert "med:DOLIPRANE" in [f["id"] for f in trouve.fiches]


def test_medicament_inconnu_le_dit_au_llm(index):
    trouve = chercher(Requete("Prix de zzzqqq ?", medicaments=["zzzqqq"]))
    assert "« zzzqqq » n'existe pas dans nos données" in textes(trouve, "note")[0]
    assert textes(trouve, "medicament") == []


def test_molecule_donne_ses_marques_les_plus_connues_et_sa_notice(index):
    trouve = chercher(Requete("Effets du paracétamol ?", medicaments=["paracetamol"]))
    note = textes(trouve, "note")[0]
    assert "est une molécule (PARACETAMOL)" in note and "autres marques dans nos données" in note
    marques = [f["meta"]["nom"] for f in trouve.fiches if f["type"] == "medicament"]
    # le princeps d'abord, pas l'ordre alphabetique ; toutes les fiches d'une meme marque
    assert marques[0] == "DOLIPRANE" and 0 < len(marques) <= 6
    assert {m.split()[0] for m in marques} == {"DOLIPRANE", "CALPOL", "PANADOL"}
    assert textes(trouve, "notice")


def test_symptome_reconnu_par_le_llm_donne_sa_fiche(index):
    trouve = chercher(Requete("J'ai mal à la tête, que puis-je prendre ?", symptomes=["mal_de_tete"]))
    assert [f["id"] for f in trouve.fiches] == ["conseil:mal_de_tete"] and trouve.pharmacies == []


def test_sans_symptome_reconnu_aucune_fiche_conseil(index):
    # eczema : hors de la liste blanche, le bot n'a rien a proposer
    assert chercher(Requete("J'ai de l'eczéma, que mettre ?")).fiches == []


def test_symptome_invente_par_le_llm_ignore():
    r = en_requete({"symptomes": ["mal_de_tete", "eczema", "mal_de_tete", 3]}, "x")
    assert r.symptomes == ["mal_de_tete"]


def test_le_prompt_de_comprehension_liste_les_symptomes():
    from nlp.rag.comprendre import construire_prompt

    prompt = construire_prompt()
    assert "{{SYMPTOMES}}" not in prompt
    assert "- mal_de_tete :" in prompt and "- toux_seche :" in prompt


def test_pharmacies_les_plus_proches_d_un_quartier(index):
    trouve = chercher(Requete("Pharmacie à Maârif ?", lieu="maarif casa", pharmacies=True))
    assert len(trouve.pharmacies) == 5 and trouve.ville == "Casablanca"
    assert all("Distance du lieu demandé" in t for t in textes(trouve, "pharmacie"))


def test_pharmacie_et_symptome_dans_le_meme_message(index):
    trouve = chercher(Requete("J'ai mal à la tête. Pharmacie à Maârif ?", lieu="maarif casa", pharmacies=True,
                              symptomes=["mal_de_tete"]))
    assert textes(trouve, "pharmacie") and textes(trouve, "conseil")


def test_grande_ville_sans_quartier_fait_demander_le_quartier(index):
    trouve = chercher(Requete("Pharmacie à Casablanca ?", lieu="casa", pharmacies=True))
    assert "demander au patient son quartier" in textes(trouve, "note")[0]
    assert trouve.pharmacies == []


def test_quartier_homonyme_fait_demander_la_ville_sauf_si_connue(index):
    trouve = chercher(Requete("Pharmacie à Agdal ?", lieu="agdal", pharmacies=True))
    assert "existe dans plusieurs villes" in textes(trouve, "note")[0]
    trouve = chercher(Requete("Pharmacie à Agdal ?", lieu="agdal", pharmacies=True), ville_connue="Rabat")
    assert len(trouve.pharmacies) == 5


def test_pharmacie_sans_lieu_fait_demander_le_lieu(index):
    trouve = chercher(Requete("Où trouver une pharmacie ?", pharmacies=True))
    assert "lui demander sa ville ou son quartier" in textes(trouve, "note")[0]


def test_garde_avoue_ne_pas_connaitre_le_tour_de_garde(index):
    trouve = chercher(Requete("Pharmacie de garde à Tanger ?", lieu="tanger", pharmacies=True, garde=True))
    assert any("tour de garde du jour n'est pas dans nos données" in t for t in textes(trouve, "note"))
    assert all(p["ville"] == "Tanger" for p in trouve.pharmacies)


def test_pharmacie_inconnue_le_dit_au_llm(index):
    trouve = chercher(Requete("Où est la pharmacie zzzqqq ?", pharmacie="zzzqqq", pharmacies=True))
    assert "« zzzqqq » n'existe pas dans nos données" in textes(trouve, "note")[0]


# ------------------------------------------------------------------- moteur

def test_le_llm_recoit_la_question_et_les_fiches(llm):
    appels = llm(reponse="13.10 DH", medicaments=["doliprane"], question="Prix de Doliprane 1 g ?")
    r = repondre("ch7al taman doliprane 1g", Session())
    assert r.texte == "13.10 DH" and r.situation == "repondre"
    comprendre, rediger = appels
    assert comprendre["en_json"] and not rediger["en_json"]
    dernier = rediger["messages"][-1]["contenu"]
    assert "Message du patient : ch7al taman doliprane 1g" in dernier
    assert "Question comprise : Prix de Doliprane 1 g ?" in dernier
    assert "Médicament : DOLIPRANE" in dernier and "prix public 13.10 DH" in dernier


def test_le_prompt_impose_la_langue_du_patient_et_nos_donnees(llm):
    appels = llm()
    repondre("ch7al taman doliprane", Session())
    assert "darija marocaine écrite en lettres latines" in appels[1]["systeme"]
    assert "{{LANGUE}}" not in appels[1]["systeme"]
    assert "n'existe pas dans nos données" in appels[1]["systeme"]
    appels.clear()
    repondre("شحال تمن دوليبران؟", Session())
    assert "darija marocaine écrite en lettres arabes" in appels[1]["systeme"]


def test_l_historique_est_transmis_aux_deux_appels(llm):
    appels = llm(reponse="CNOPS wla CNSS ?", medicaments=["doliprane"])
    session = Session()
    repondre("wach doliprane kayt3awed ?", session)
    repondre("cnops", session)
    for appel in appels[2:]:
        contenus = [m["contenu"] for m in appel["messages"]]
        assert contenus[:2] == ["wach doliprane kayt3awed ?", "CNOPS wla CNSS ?"]


def test_la_ville_est_retenue_pour_la_suite(llm):
    session = Session()
    llm(lieu="rabat", pharmacies=True)
    repondre("pharmacie f rabat", session)
    assert session.ville == "Rabat"
    llm(lieu="agdal", pharmacies=True)
    assert len(repondre("f agdal", session).pharmacies) == 5


def test_urgence_par_mots_cles_sans_llm(index):
    r = repondre("wlidi bla3 chi 10 d l7bob dyal doliprane", Session())
    assert r.urgence == "intoxication" and "0801 000 180" in r.texte


def test_urgence_reconnue_par_le_llm_sans_second_appel(llm):
    appels = llm(urgence="detresse", medicaments=["doliprane"])
    r = repondre("mon pere a du mal, il ne va pas bien du tout", Session())
    assert r.urgence == "detresse" and "141" in r.texte
    assert len(appels) == 1


def test_llm_indisponible_reste_poli_et_donne_les_urgences(index, monkeypatch):
    import nlp.rag.comprendre
    from nlp.llm import LLMIndisponible

    def panne(*a, **k):
        raise LLMIndisponible("gemini : quota ; groq : pas de cle")

    monkeypatch.setattr(nlp.rag.comprendre, "appeler_llm", panne)
    session = Session()
    r = repondre("prix doliprane", session)
    assert r.situation == "indisponible"
    assert "Reessaie" in r.texte and "141" in r.texte
    assert session.historique == []      # un message sans reponse n'entre pas dans la conversation


# -------------------------------------------------------------------- cache

def test_meme_premiere_question_resservie_sans_llm(llm):
    appels = llm(reponse="13.10 DH", medicaments=["doliprane"])
    premiere = repondre("Ch7al taman doliprane ?", Session())
    assert len(appels) == 2
    seconde = repondre("  ch7al  taman doliprane", Session())      # majuscules, espaces, "?"
    assert len(appels) == 2                                         # aucun nouvel appel
    assert seconde.texte == premiere.texte == "13.10 DH"
    assert seconde.fournisseur == "cache" and seconde.sources == premiere.sources


def test_question_en_cours_de_conversation_jamais_resservie(llm):
    appels = llm(reponse="13.10 DH", medicaments=["doliprane"])
    repondre("ch7al taman doliprane", Session())
    session = Session()
    repondre("salam", session)
    avant = len(appels)
    repondre("ch7al taman doliprane", session)       # meme texte, mais pas en debut de conversation
    assert len(appels) == avant + 2


def test_garde_et_urgence_jamais_retenues(llm):
    appels = llm(lieu="tanger", pharmacies=True, garde=True)
    repondre("pharmacie de garde f tanger", Session())
    repondre("pharmacie de garde f tanger", Session())
    assert len(appels) == 4
    appels.clear()
    llm(urgence="detresse")
    repondre("mon pere ne va pas bien du tout", Session())
    repondre("mon pere ne va pas bien du tout", Session())
    assert len(appels) == 2


def test_la_reponse_resservie_entre_dans_la_conversation(llm):
    llm(reponse="Hahoma.", lieu="maarif casa", pharmacies=True)
    repondre("pharmacie f maarif casa", Session())
    session = Session()
    r = repondre("pharmacie f maarif casa", session)
    assert r.fournisseur == "cache" and len(r.pharmacies) == 5
    assert session.ville == "Casablanca" and len(session.historique) == 2


def test_le_cache_se_vide_quand_un_prompt_change(llm, monkeypatch):
    import nlp.moteur

    appels = llm(medicaments=["doliprane"])
    repondre("ch7al taman doliprane", Session())
    monkeypatch.setattr(nlp.moteur._Cache, "_version_actuelle", staticmethod(lambda: ("autre",)))
    repondre("ch7al taman doliprane", Session())
    assert len(appels) == 4


# ---------------------------------------------------------- garde du jour

GARDE_TANGER = {"ville": "Tanger", "date": "2026-10-12", "source": "Telecontact", "pharmacies": [
    {"nom": f"Pharmacie {i}", "adresse": f"{i} rue de Fès", "ville": "Tanger", "quartier": "Centre",
     "telephone": "05 39 00 00 00", "latitude": 35.77 + i / 1000, "longitude": -5.80,
     "ouverture": "nuit" if i % 2 else "jour"}
    for i in range(1, 9)]}


def test_garde_du_jour_remplace_les_horaires(index, monkeypatch):
    import nlp.rag.recherche as recherche

    monkeypatch.setattr(recherche, "garde_du_jour", lambda ville: GARDE_TANGER if ville == "Tanger" else None)
    trouve = chercher(Requete("Pharmacie de garde ?", lieu="tanger", pharmacies=True, garde=True))
    # grande liste sans quartier : on demande le quartier, sans dire "tour de garde inconnu"
    notes = textes(trouve, "note")
    assert "8 pharmacies de garde le 2026-10-12" in notes[0] and "quartier" in notes[0]
    assert not any("n'est pas dans nos données" in n for n in notes)
    assert trouve.pharmacies == []


def test_garde_du_jour_les_plus_proches_du_quartier(index, monkeypatch):
    import nlp.rag.recherche as recherche
    from nlp.linking.lieux import Lieu

    monkeypatch.setattr(recherche, "garde_du_jour", lambda ville: GARDE_TANGER)
    monkeypatch.setattr(recherche, "resoudre_lieu", lambda cite, ville_connue=None: Lieu(
        cite, "quartier", nom="Centre", ville="Tanger", latitude=35.771, longitude=-5.80))
    trouve = chercher(Requete("Pharmacie de garde ?", lieu="centre tanger", pharmacies=True, garde=True))
    assert [p["nom"] for p in trouve.pharmacies][:2] == ["Pharmacie 1", "Pharmacie 2"]
    assert len(trouve.pharmacies) == 5 and trouve.pharmacies[0]["garde_du_jour"] == "2026-10-12"
    assert "d'après Telecontact" in textes(trouve, "note")[0]
    assert "De garde le 2026-10-12 : de nuit" in textes(trouve, "pharmacie")[0]


def test_lecture_d_une_page_telecontact():
    from bs4 import BeautifulSoup

    from nlp.outils.garde import _date, _pharmacies, _quartiers

    page = BeautifulSoup("""
      <script type="application/ld+json">{"@type": "DataFeedItem", "dateModified": "2026-10-12"}</script>
      <script type="application/ld+json">{"@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "item": {"@type": "Pharmacy", "name": "Pharmacie Addoha",
          "address": {"streetAddress": "  avenue  Stendahl ", "addressLocality": "Casablanca"},
          "telephone": "05 22 25 96 69", "geo": {"latitude": "33.57", "longitude": "-7.63"}}},
        {"@type": "ListItem", "name": "Pharmacie de garde Maarif Casablanca",
          "url": "https://www.telecontact.ma/pharmacie-de-garde-zone/casablanca/maarif.html"}]}</script>
    """, "html.parser")
    assert _date(page) == "2026-10-12"
    assert _pharmacies(page) == [{"nom": "Pharmacie Addoha", "adresse": "avenue Stendahl",
                                  "ville": "Casablanca", "telephone": "05 22 25 96 69",
                                  "latitude": 33.57, "longitude": -7.63}]
    assert _quartiers(page) == [("Maarif Casablanca", "casablanca", "maarif")]
