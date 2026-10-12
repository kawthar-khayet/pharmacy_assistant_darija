"""Orchestrateur : un message du patient -> une reponse (RAG).

    filet urgence (mots-cles, sans LLM)
      -> comprendre (1er appel LLM) : quoi chercher, question reformulee
      -> recherche (code) : les fiches de nos donnees qui repondent
      -> reponse (2e appel LLM) : redigee avec ces fiches SEULEMENT, dans la
         langue du patient ; rien dans les fiches -> "cette information
         n'existe pas dans nos donnees"

La conversation (Session) garde l'historique envoye au LLM et la derniere
ville connue : le patient ne les redit pas a chaque message.

Cache : la reponse a une question qui OUVRE une conversation est retenue 24 h
et resservie sans appel LLM a qui repose exactement la meme (voir _Cache).
"""
import logging
import os
import re
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from nlp.analyse.urgence import detecter_urgence
from nlp.llm import LLMIndisponible, appeler_llm
from nlp.rag.comprendre import comprendre, conversation
from nlp.rag.index import INDEX_PATH, collection
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


# Cache des reponses : CACHE_REPONSES=0 dans le .env le coupe.
CACHE_ACTIF = os.environ.get("CACHE_REPONSES", "1") != "0"
CACHE_DUREE = 24 * 3600     # secondes
CACHE_MAX = 500             # questions retenues ; les plus anciennes sortent


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


class _Cache:
    """Reponses aux questions frequentes, pour ne pas payer deux appels LLM a
    chaque « ch7al taman doliprane ? ».

    Prudent : seulement le premier message d'une conversation (la reponse a
    « w taman dyalo ? » depend de ce qui precede), ecrit pareil aux majuscules,
    espaces et ponctuation finale pres. Jamais une urgence, jamais une question
    de garde (elle change chaque jour), jamais une panne du LLM.

    Le cache se vide des que les prompts ou l'index changent : une reponse
    redigee avec d'anciennes regles ou d'anciens prix ne doit pas ressortir.
    """

    def __init__(self):
        self._reponses: "OrderedDict[str, tuple[float, Reponse, str | None]]" = OrderedDict()
        self._version = None

    @staticmethod
    def _cle(message: str) -> str:
        return re.sub(r"\s+", " ", message.lower()).strip(" ?!.؟")

    @staticmethod
    def _version_actuelle() -> tuple:
        fichiers = (PROMPT_PATH, PROMPT_PATH.with_name("comprendre.md"), INDEX_PATH / "chroma.sqlite3")
        return tuple(f.stat().st_mtime if f.exists() else 0 for f in fichiers)

    def _verifier_version(self) -> None:
        version = self._version_actuelle()
        if version != self._version:
            self._reponses.clear()
            self._version = version

    def lire(self, message: str) -> tuple[Reponse, str | None] | None:
        """(reponse, ville reconnue) si la question est connue et encore fraiche."""
        self._verifier_version()
        cle = self._cle(message)
        trouvee = self._reponses.get(cle)
        if trouvee is None:
            return None
        expire, reponse, ville = trouvee
        if expire < time.time():
            del self._reponses[cle]
            return None
        self._reponses.move_to_end(cle)
        return reponse, ville

    def ecrire(self, message: str, reponse: Reponse, ville: str | None) -> None:
        self._verifier_version()
        self._reponses[self._cle(message)] = (time.time() + CACHE_DUREE, reponse, ville)
        while len(self._reponses) > CACHE_MAX:
            self._reponses.popitem(last=False)

    def vider(self) -> None:
        self._reponses.clear()


cache = _Cache()


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

    # Question deja posee en debut de conversation : meme reponse, sans LLM.
    debut = CACHE_ACTIF and not session.historique and session.ville is None
    if debut and (connue := cache.lire(message)):
        reponse, session.ville = connue
        return _memoriser(session, message, replace(reponse, fournisseur="cache"))

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

    reponse = Reponse(
        rep.texte, langue, "repondre", pharmacies=trouve.pharmacies,
        sources=[f["id"] for f in trouve.fiches if f["type"] != "note"],
        requete=commun["requete"], fournisseur=rep.fournisseur)
    if debut and not compris.requete.garde:
        cache.ecrire(message, reponse, trouve.ville)
    return _memoriser(session, message, reponse)


__all__ = ["IndexAbsent", "Reponse", "Session", "cache", "repondre"]
