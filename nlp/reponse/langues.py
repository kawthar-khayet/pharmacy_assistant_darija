"""Langue de la reponse : celle et la graphie de la question.

Quatre langues :
  fr       francais
  ary_lat  darija en graphie latine (arabizi : "wach kayn doliprane?")
  ary_ar   darija en graphie arabe ("واش كاين دوليبران؟")
  ar       arabe standard ("هل يوجد دواء دوليبران؟")

L'analyse (LLM) propose une langue ; `detecter_langue` la verifie contre la
graphie reelle du message et prend le relais quand elle manque ou ne colle
pas.
"""
import re

LANGUES = ("fr", "ary_lat", "ary_ar", "ar")
LANGUE_PAR_DEFAUT = "fr"
LANGUES_ARABES = {"ary_ar", "ar"}

_LETTRE_ARABE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
_LETTRE_LATINE = re.compile(r"[A-Za-zÀ-ÿ]")
# Arabizi : chiffres qui notent des sons arabes, colles a des lettres
# (3andkom, 7alla, 9rib, ch7al). "1g" ou "500mg" n'en sont pas : 1, 5 et 0
# ne servent pas de lettres.
_CHIFFRE_ARABIZI = re.compile(r"[a-z][2379]|[2379][a-z]", re.IGNORECASE)
_MOT = re.compile(r"[a-zà-ÿ]+", re.IGNORECASE)

# Mots courants de la darija ecrite en lettres latines. Les mots ambigus avec
# le francais ("la", "ma", "fin" au sens "fin du mois"...) sont volontairement
# absents, sauf "fin" que les patients emploient massivement pour "ou".
MOTS_DARIJA = {
    "wach", "wash", "ach", "achno", "chno", "chnou", "chnowa", "kayn", "kayna", "kaynin",
    "kayen", "kain", "3andkom", "andkom", "3ndkom", "3andek", "3ndk", "bghit", "bghina",
    "bghiti", "chhal", "ch7al", "shhal", "sh7al", "fin", "fine", "feen", "fyn", "dyal",
    "dial", "taman", "tamane", "thaman", "rkhis", "rkhes", "bhal", "b7al", "chi", "shi",
    "salam", "slm", "labas", "chokran", "choukran", "shukran", "sidalia", "saydalia",
    "drari", "sghar", "sghir", "kifach", "kifash", "nakhod", "nakhed", "daba", "lyoum",
    "ghir", "bzaf", "mzyan", "wakha", "afak", "3afak", "3tini", "atini", "nta", "nti",
    "dwa", "dwaya", "ila", "wla", "walakin", "fih", "fiha", "hna", "m3a", "3la", "mn",
    "kidayr", "kidayra", "n7goz", "nchri", "tbib", "sbitar", "ras", "kerch", "kansel",
    "kay9oulo", "kaydir", "katdir", "rah", "raha", "hadak", "hadik", "hada", "hadi",
    "khoya", "khti", "lah", "llah", "inchallah", "mabrouk", "zwin", "7alla", "m7lola",
}


def ressemble_darija_latine(texte: str) -> bool:
    if _CHIFFRE_ARABIZI.search(texte):
        return True
    return any(m.lower() in MOTS_DARIJA for m in _MOT.findall(texte))


def detecter_langue(texte: str, proposition: str | None = None) -> str:
    """Langue dans laquelle repondre a `texte`.

    `proposition` est la langue annoncee par le NLU ; elle n'est retenue que si
    elle correspond a la graphie du message (un modele qui annonce "ar" pour
    "wach kayn doliprane" se trompe forcement)."""
    arabe = len(_LETTRE_ARABE.findall(texte))
    latin = len(_LETTRE_LATINE.findall(texte))

    if arabe == 0 and latin == 0:
        # que des chiffres ou de la ponctuation : rien a lire
        return proposition if proposition in LANGUES else LANGUE_PAR_DEFAUT
    if arabe >= latin:
        # au Maroc, un message en lettres arabes est bien plus souvent de la
        # darija que de l'arabe standard : c'est le repli par defaut
        return proposition if proposition in LANGUES_ARABES else "ary_ar"
    if proposition in {"fr", "ary_lat"}:
        return proposition
    return "ary_lat" if ressemble_darija_latine(texte) else "fr"
