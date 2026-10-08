"""Orchestrateur : un message du patient -> une reponse.

    filet urgence (mots-cles, sans LLM)
      -> analyse (le SEUL appel LLM) + validation
      -> medicaments et lieux retrouves dans les bases (linking/)
      -> outils (outils/) : seulement les demandes posees
      -> composeur (reponse/) : phrases courtes, dans la langue du patient

La conversation (Session) garde l'historique envoye au LLM, le regime
d'assurance et la derniere ville connue : le patient ne les redit pas a chaque
message.
"""
import logging
from dataclasses import dataclass, field

from nlp.analyse.analyseur import analyser, charger_schema
from nlp.analyse.urgence import detecter_urgence
from nlp.analyse.validation import Analyse, valider
from nlp.linking.lieux import resoudre_lieu
from nlp.llm import LLMIndisponible
from nlp.outils.conseil import conseil
from nlp.outils.medicament import formes_dosages
from nlp.outils.pharmacies import info_pharmacie, pharmacie_garde, pharmacies_lieu
from nlp.outils.prix import prix
from nlp.outils.resolution import resoudre_tous
from nlp.outils.securite import RUBRIQUES, securite
from nlp.reponse import composeur as c
from nlp.reponse.langues import detecter_langue

log = logging.getLogger(__name__)

# Ce que le bot garde de la conversation pour le LLM (messages, pas echanges).
HISTORIQUE_MAX = 12
# Une longue liste de pharmacies n'apprend rien de plus au LLM au tour suivant.
LONGUEUR_MAX_HISTORIQUE = 600
# Medicaments traites par message : au-dela, la reponse devient illisible.
MAX_MEDICAMENTS = 3

DEMANDES_MEDICAMENT = {"prix", "remboursement", "formes_dosages", *RUBRIQUES}
SITUATIONS_PHRASE = {"medical", "pas_d_info", "incompris", "salutation", "hors_sujet"}


@dataclass
class Session:
    historique: list[dict] = field(default_factory=list)   # [{"role", "contenu"}] pour le LLM
    regime: str | None = None                                # "cnops" | "cnss" | "aucun"
    ville: str | None = None                                 # derniere ville reconnue


@dataclass
class Reponse:
    texte: str                      # reponse complete
    texte_court: str                # sans les listes que l'interface affiche en fiches
    langue: str
    situation: str
    demandes: list[str] = field(default_factory=list)
    pharmacies: list[dict] = field(default_factory=list)   # fiches a afficher
    securite: dict | None = None                            # rubriques demandees, texte complet
    attend: list[str] = field(default_factory=list)         # ce que le bot vient de demander
    urgence: str | None = None
    analyse: dict | None = None     # pour les tests et le debogage
    fournisseur: str | None = None
    corrections: list[str] = field(default_factory=list)


def _assembler(blocs: list[c.Bloc], court: bool) -> str:
    return "\n\n".join(texte for b in blocs if (texte := b.texte(court)))


def _memoriser(session: Session, message: str, reponse: Reponse) -> Reponse:
    session.historique.append({"role": "user", "contenu": message})
    session.historique.append({"role": "assistant", "contenu": reponse.texte[:LONGUEUR_MAX_HISTORIQUE]})
    del session.historique[:-HISTORIQUE_MAX]
    return reponse


def _reponse(blocs: list[c.Bloc], langue: str, situation: str, **autres) -> Reponse:
    return Reponse(texte=_assembler(blocs, False), texte_court=_assembler(blocs, True),
                   langue=langue, situation=situation, **autres)


class _Tour:
    """Ce qu'on accumule pendant le traitement d'un message."""

    def __init__(self, analyse: Analyse, session: Session, langue: str):
        self.analyse, self.session, self.langue = analyse, session, langue
        self.blocs: list[c.Bloc] = []
        self.pharmacies: list[dict] = []
        self.securite: dict | None = None
        self.attend: list[str] = []

    def demander(self, besoin: str) -> None:
        if besoin not in self.attend:
            self.attend.append(besoin)

    def lieu(self):
        """Le lieu cite, resolu ; None s'il n'y en a pas. La ville connue de la
        conversation sert a departager un quartier present dans plusieurs villes."""
        if not self.analyse.lieu:
            return None
        lieu = resoudre_lieu(self.analyse.lieu, self.session.ville)
        if lieu.ville and lieu.statut in ("quartier", "ville"):
            self.session.ville = lieu.ville
        return lieu

    def pharmacies_trouvees(self, res: dict) -> None:
        if res.get("pharmacies"):
            self.pharmacies.extend(res["pharmacies"])
        if res["statut"] in ("lieu_inconnu", "preciser_ville", "preciser_quartier"):
            self.demander("lieu_precis")


def _medicaments(tour: _Tour, demandes: list[str]) -> None:
    a, langue = tour.analyse, tour.langue
    if not a.medicaments:
        tour.demander("medicament")
        return
    rubriques = [d for d in demandes if d in RUBRIQUES]
    regime = a.regime if a.regime != "inconnu" else tour.session.regime
    for resolu in resoudre_tous(a.medicaments[:MAX_MEDICAMENTS]):
        if (entete := c.med_entete(resolu, langue)):
            tour.blocs.append(entete)
        if resolu.statut == "introuvable":
            continue
        if "prix" in demandes or "remboursement" in demandes:
            res = prix(resolu)
            if res.get("dosage_absent"):
                tour.blocs.append(c.dosage_absent(res, langue))
            if res["statut"] == "plus_commercialise":
                tour.blocs.append(c.composer_prix(res, langue))
                continue
            if "prix" in demandes:
                tour.blocs.append(c.composer_prix(res, langue))
            if "remboursement" in demandes:
                if regime:
                    tour.blocs.append(c.composer_remboursement(res, regime, langue))
                else:
                    tour.demander("regime")
        if "formes_dosages" in demandes:
            tour.blocs.append(c.composer_formes(formes_dosages(resolu), langue))
        if rubriques:
            res = securite(resolu, rubriques, langue)
            tour.blocs.append(c.composer_securite(res, langue))
            if tour.securite is None and res.get("rubriques"):
                # Le texte officiel des rubriques demandees, replie sous la reponse
                # (l'explication simple, elle, est deja dans la reponse).
                tour.securite = {k: res[k] for k in ("dci", "rubriques", "specialite_source", "source_url")}


def _pharmacies(tour: _Tour, demandes: list[str]) -> None:
    a, langue = tour.analyse, tour.langue
    if "pharmacies_lieu" in demandes or "pharmacie_garde" in demandes:
        lieu = tour.lieu()
        if lieu is None:
            tour.demander("lieu")
        else:
            if "pharmacies_lieu" in demandes and "pharmacie_garde" not in demandes:
                res = pharmacies_lieu(lieu)
                tour.blocs.append(c.composer_pharmacies_lieu(res, langue))
                tour.pharmacies_trouvees(res)
            if "pharmacie_garde" in demandes:
                res = pharmacie_garde(lieu)
                tour.blocs.append(c.composer_garde(res, langue))
                tour.pharmacies_trouvees(res)
    if "info_pharmacie" in demandes:
        if not a.pharmacie:
            tour.demander("pharmacie")
            return
        lieu = tour.lieu()
        res = info_pharmacie(a.pharmacie, lieu, tour.session.ville)
        tour.blocs.append(c.composer_info_pharmacie(res, langue, a.lieu))
        tour.pharmacies_trouvees(res)


# Questions posees a la fin de la reponse, dans cet ordre.
QUESTIONS = {"medicament": "demander_medicament", "regime": "demander_regime",
             "pharmacie": "demander_pharmacie", "lieu": "demander_lieu"}


def _demandes(tour: _Tour) -> None:
    demandes = tour.analyse.demandes
    if DEMANDES_MEDICAMENT & set(demandes):
        _medicaments(tour, demandes)
    _pharmacies(tour, demandes)
    if "posologie" in demandes:
        tour.blocs.append(c.phrase(tour.langue, "posologie"))
    for besoin, cle in QUESTIONS.items():
        if besoin in tour.attend:
            tour.blocs.append(c.phrase(tour.langue, cle))


def repondre(message: str, session: Session) -> Reponse:
    """Reponse au dernier message du patient. Met la session a jour."""
    message = message.strip()

    # 1. Filet de securite : une urgence passe avant tout, meme si le LLM est en panne.
    filet = detecter_urgence(message)
    if filet:
        langue = detecter_langue(message)
        return _memoriser(session, message, _reponse(
            [c.phrase(langue, f"urgence_{filet}")], langue, "urgence", urgence=filet))

    # 2. Le seul appel LLM.
    try:
        reponse_llm = analyser(message, session.historique)
    except LLMIndisponible as e:
        log.error("analyse impossible : %s", e)
        langue = detecter_langue(message)
        return _reponse([c.phrase(langue, "llm_indisponible")], langue, "indisponible")
    analyse = valider(reponse_llm.donnees, message)
    langue = detecter_langue(message, analyse.langue)
    if analyse.regime != "inconnu":
        session.regime = analyse.regime
    commun = {"analyse": analyse.model_dump(), "fournisseur": reponse_llm.fournisseur,
              "corrections": analyse.corrections}

    situation = analyse.situation
    if situation == "urgence":
        reponse = _reponse([c.phrase(langue, f"urgence_{analyse.urgence_type}")], langue, situation,
                           urgence=analyse.urgence_type, **commun)
    elif situation in SITUATIONS_PHRASE:
        reponse = _reponse([c.phrase(langue, situation)], langue, situation, **commun)
    elif situation == "conseil_symptome":
        res = conseil(analyse.symptomes, analyse.patient, analyse.grossesse, analyse.duree_jours)
        reponse = _reponse([c.composer_conseil(res, langue)], langue, situation, **commun)
    else:   # repondre / preciser : chaque demande, puis ce qui manque
        tour = _Tour(analyse, session, langue)
        _demandes(tour)
        if not tour.blocs:
            tour.blocs.append(c.phrase(langue, "incompris"))
        reponse = _reponse(tour.blocs, langue, situation, demandes=analyse.demandes,
                           pharmacies=tour.pharmacies, securite=tour.securite,
                           attend=tour.attend, **commun)
    return _memoriser(session, message, reponse)


__all__ = ["Reponse", "Session", "repondre", "charger_schema"]
