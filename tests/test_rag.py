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


def test_fiche_conseil_cite_la_molecule_jamais_une_marque(fiches):
    fievre = next(f for f in fiches if f["id"] == "conseil:fievre_legere")
    assert "Molécule à demander au pharmacien : PARACETAMOL" in fievre["texte"]
    assert "DOLIPRANE" not in fievre["texte"]
    assert "Enfant, bébé ou femme enceinte" in fievre["texte"]


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


def test_question_sans_medicament_cherche_par_le_sens(index):
    trouve = chercher(Requete("J'ai mal à la tête, que puis-je prendre ?"))
    assert trouve.fiches and trouve.pharmacies == []


def test_pharmacies_les_plus_proches_d_un_quartier(index):
    trouve = chercher(Requete("Pharmacie à Maârif ?", lieu="maarif casa", pharmacies=True))
    assert len(trouve.pharmacies) == 5 and trouve.ville == "Casablanca"
    assert all("Distance du lieu demandé" in t for t in textes(trouve, "pharmacie"))


def test_pharmacie_et_symptome_dans_le_meme_message(index):
    trouve = chercher(Requete("J'ai mal à la tête. Pharmacie à Maârif ?", lieu="maarif casa", pharmacies=True))
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
