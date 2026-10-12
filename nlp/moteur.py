"""Orchestrateur : un message du patient -> une reponse (RAG).

    filet urgence (mots-cles, sans LLM)
      -> comprendre (1er appel LLM) : quoi chercher, question reformulee
      -> recherche (code) : les fiches de nos donnees qui repondent
      -> reponse (2e appel LLM) : redigee avec ces fiches SEULEMENT, dans la
         langue du patient ; rien dans les fiches -> "cette information
         n'existe pas dans nos donnees"

La conversation (Session) garde l'historique envoye au LLM et la derniere
ville connue : le patient ne les redit pas a chaque message.
"""
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from nlp.analyse.urgence import detecter_urgence
from nlp.llm import LLMIndisponible, appeler_llm
from nlp.rag.comprendre import comprendre, conversation
from nlp.rag.index import collection
from nlp.rag.recherche import chercher
from nlp.reponse.langues import detecter_langue
from nlp.reponse.phrases import t

log = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent / "rag" / "repondre.md"

# Ce que le bot garde de la conversation pour le LLM (messages, pas echanges).
HISTORIQUE_MAX = 12
# Une longue liste de pharmacies n'apprend rien de plus au LLM au tour suivant.
LONGUEUR_MAX_HISTORIQUE = 600
# Un medicament a 40 presentations ferait exploser le prompt.
LONGUEUR_MAX_FICHE = 6000

NOMS_LANGUES = {
    "fr": "français",
    "ary_lat": "darija marocaine écrite en lettres latines (arabizi)",
    "ary_ar": "darija marocaine écrite en lettres arabes",
    "ar": "arabe standard",
}


class IndexAbsent(RuntimeError):
    """L'index du RAG n'a pas ete construit sur cette machine."""


@dataclass
class Session:
    historique: list[dict] = field(default_factory=list)   # [{"role", "contenu"}] pour le LLM
    ville: str | None = None                                 # derniere ville reconnue


@dataclass
class Reponse:
    texte: str
    langue: str
    situation: str                  # "repondre" | "urgence" | "indisponible"
    pharmacies: list[dict] = field(default_factory=list)   # fiches a afficher
    urgence: str | None = None
    requete: dict | None = None     # ce que le LLM a compris, pour les tests et le debogage
    sources: list[str] = field(default_factory=list)       # ids des fiches donnees au LLM
    fournisseur: str | None = None


def _memoriser(session: Session, message: str, reponse: Reponse) -> Reponse:
    session.historique.append({"role": "user", "contenu": message})
    session.historique.append({"role": "assistant", "contenu": reponse.texte[:LONGUEUR_MAX_HISTORIQUE]})
    del session.historique[:-HISTORIQUE_MAX]
    return reponse


def _urgence(session: Session, message: str, langue: str, type_: str, **autres) -> Reponse:
    """Les numeros d'urgence, rien d'autre : une phrase fixe, pas une redaction du LLM."""
    return _memoriser(session, message, Reponse(
        t(langue, f"urgence_{type_}"), langue, "urgence", urgence=type_, **autres))


def _indisponible(langue: str, erreur: Exception) -> Reponse:
    log.error("LLM indisponible : %s", erreur)
    return Reponse(t(langue, "llm_indisponible"), langue, "indisponible")


def _question_avec_fiches(message: str, question: str, fiches: list[dict]) -> str:
    """Le dernier message tel que le LLM le recoit : la question, puis les fiches."""
    blocs = [f"[{i}] ({f['type']})\n{f['texte'][:LONGUEUR_MAX_FICHE]}"
             for i, f in enumerate(fiches, start=1)]
    return (f"Message du patient : {message}\n"
            f"Question comprise : {question}\n\n"
            "FICHES trouvées dans nos données :\n\n"
            + ("\n\n".join(blocs) or "(aucune fiche)"))


def repondre(message: str, session: Session) -> Reponse:
    """Reponse au dernier message du patient. Met la session a jour."""
    message = message.strip()
    langue = detecter_langue(message)

    # 1. Filet de securite : une urgence passe avant tout, meme si le LLM est en panne.
    filet = detecter_urgence(message)
    if filet:
        return _urgence(session, message, langue, filet)

    if collection().count() == 0:
        raise IndexAbsent("index du RAG vide : lance  py -m nlp.rag.fiches  puis  py -m nlp.rag.index")

    # 2. Premier appel LLM : que faut-il chercher ?
    try:
        compris = comprendre(message, session.historique)
    except LLMIndisponible as e:
        return _indisponible(langue, e)
    commun = {"requete": asdict(compris.requete), "fournisseur": compris.fournisseur}
    if compris.urgence:
        return _urgence(session, message, langue, compris.urgence, **commun)

    # 3. Recherche dans nos donnees.
    trouve = chercher(compris.requete, session.ville)
    session.ville = trouve.ville

    # 4. Second appel LLM : la reponse, avec les fiches seulement.
    systeme = PROMPT_PATH.read_text(encoding="utf-8").replace("{{LANGUE}}", NOMS_LANGUES[langue])
    messages = conversation(session.historique)
    messages.append({"role": "user", "contenu": _question_avec_fiches(
        message, compris.requete.question, trouve.fiches)})
    try:
        rep = appeler_llm(systeme, messages, en_json=False)
    except LLMIndisponible as e:
        return _indisponible(langue, e)

    return _memoriser(session, message, Reponse(
        rep.texte, langue, "repondre", pharmacies=trouve.pharmacies,
        sources=[f["id"] for f in trouve.fiches if f["type"] != "note"],
        requete=commun["requete"], fournisseur=rep.fournisseur))


__all__ = ["IndexAbsent", "Reponse", "Session", "repondre"]
