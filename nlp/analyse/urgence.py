"""Filet de securite : detecte une urgence par mots-cles, sans LLM.

Tourne AVANT l'appel au LLM et meme s'il est en panne. Il suffit que le LLM OU
ce filet detecte une urgence pour que le bot affiche les numeros d'urgence.
La liste privilegie la prudence : mieux vaut afficher les numeros une fois de
trop que de rater une vraie urgence. A enrichir au fil des tests.
"""
import re
import unicodedata

# --- Normalisation ----------------------------------------------------------

_DIACRITIQUES_ARABES = re.compile(r"[ً-ْـ]")   # voyelles, tatwil
_CHIFFRES_ARABES = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_REPETITIONS = re.compile(r"(.)\1{2,}")                      # "bzaaaf" -> "bzaf"


def _normaliser(texte: str) -> str:
    texte = texte.lower().translate(_CHIFFRES_ARABES)
    # accents latins retires ("évanoui" -> "evanoui") ; les lettres arabes,
    # sans accent au sens Unicode, ne sont pas touchees
    texte = "".join(c for c in unicodedata.normalize("NFD", texte)
                    if unicodedata.category(c) != "Mn" or "؀" <= c <= "ۿ")
    texte = _DIACRITIQUES_ARABES.sub("", texte)
    texte = (texte.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
                  .replace("ى", "ي").replace("ة", "ه"))
    texte = texte.replace("sh", "ch")
    texte = _REPETITIONS.sub(r"\1", texte)
    return re.sub(r"\s+", " ", texte)


# --- Detresse : respiration, conscience, reaction grave, saignement ----------
# (textes normalises : sans accents, "sh" -> "ch", ة -> ه, ى -> ي, أ -> ا)

DETRESSE = [
    # darija, lettres latines (9 et q s'ecrivent indifferemment)
    r"\bma\s?k[a-z]{0,3}\s?t{0,2}n[ae]?f[ae]?s{1,2}ch",                  # ma kaytnfsch
    r"\bma\s?b[9q]a(t|ch|tch)?\s?k[a-z]{0,3}\s?t{0,2}n[ae]?f[ae]?s",     # ma b9ach kaytnfs
    r"\bma\s?[9q]adr(ach|atch|inch|ch)\s?[ynt]?t{0,2}n[ae]?f[ae]?s",     # ma 9adrach ytnfs
    r"\b(kay|kat|t)?kh[ae]?n[ae]?[9q]",                                  # tkhne9, kaytkhne9
    r"\bt?ghm(a|at|aw|ia)\b",                                            # ghma 3lih
    r"\bfa[9q]a?d(at|o|t)?\s?(l|el)?\s?w[ae]3[iy]",                      # fa9d lwa3i
    r"\bma\s?(b[9q]ach\s?)?k[a-z]{0,2}f[iy][9q]",                        # ma kayfi9ch
    r"\b(kay|kat|t)?sr[ae]3\b|kayrt[ae]3d",                              # convulsions
    r"(wjh|wajh|chf[ae]?y?f)[a-z]*\s(t|kay|kat)?n[ae]?f[ae]?kh",         # wjho tnfekh
    r"\bt?n[ae]?f[ae]?kh[a-z]*\s(lih|liha|lia\s)?\s?(wjh|wajh|chf[ae]?y?f)",
    r"\b(s[ae]?dr)[a-z]*\s(kay|kat)?(dr|der|7r[9q]|jr)",                 # sdri kaydrni
    r"\bd[ae]?m\s(bzaf|kaytl[ae][9q])",                                  # dem bzaf
    # francais
    r"respir(e|es|ent|er)?\s(plus|pas|mal|difficilement)",
    r"(mal|difficultes?|peine)\s(a|pour)\srespirer",
    r"etouff",
    r"(perte|perdu|perd)\s(de\s)?connaissance",
    r"evanoui|inconscient",
    r"reveille\s(plus|pas)",
    r"convuls|epilep",
    r"douleur\s(dans\s|a\s)?(la\s)?poitrine|douleur\sthoracique|mal\s(a|dans)\s(la\s)?poitrine",
    r"gonfle\w*\s(du\s|de\sla\s|des\s|au\s|aux\s)?(visage|levres?|gorge|langue|yeux)",
    r"(visage|levres?|gorge|langue|yeux)\s(\w+\s)?gonfl",               # levres gonflees
    r"anaphyla|quincke|hemorrag|\bavc\b|paralys",
    r"saigne\w*\s(beaucoup|enormement|abondamment|sans\sarret)",
    # darija / arabe, lettres arabes
    r"ما ?(ك|كي|كا)?(ي|ت)?تنفس",                                         # ما كيتنفسش
    r"ما ?(بقا|قادر)\S* ?(كي|ك|ي|ت)?(ي|ت)?تنفس",                         # ما بقاتش كتنفس
    r"(ضيق|صعوبه) ?(ف|في)? ?(التنفس|النفس)",
    r"اختناق|تخنق|مخنوق",
    r"غمي|اغماء",                                                        # غمى عليه (ى -> ي)
    r"فقد\S* ?(ال)?وعي",
    r"تشنج|صرع",
    r"(الم|وجع|حريق) ?(ف|في) ?(الصدر|صدري)",
    r"نزيف",
    r"تنفخ\S* ?\S* ?(وجه|الوجه|شفا|شفايف)|(وجه|شفايف)\S* ?تنفخ",
]

# --- Intoxication : surdosage, prise accidentelle, produit avale -------------

INTOXICATION = [
    # darija, lettres latines
    r"\bt?bl[ae]?3\w*\s.{0,40}(bzaf|kaml|kolchi|l?[3a]o?lba|\b([5-9]|[1-9]\d+)\b)",  # bla3 chi 10 d l7bob
    r"\b(khd|kl)(it|a|at|ina|o|aw)?\s.{0,15}bzaf\s(dyal|d|mn)\s?(l|el)?\s?(dwa|7bob|7ba|comprim|dwaya)",
    r"\bz[ae]?dt?\s?f\s?(dwa|dose|l7bob)",                               # zdt f dwa
    r"\bt?s[ae]?m[ae]?m|msmou?m",                                        # tsmem, msmom
    r"(chr[ae]?b|bl[ae]?3)\w*\s.{0,25}(jav[ae]l|jaf[ie]l|dwa\s?(d|dyal)\s?(l|el)?\s?(fir|far|ghsil|tsbin))",
    # francais
    r"surdos|sur-dos|overdose|intoxi|empoisonn|poison",
    r"avale\w*\s.{0,30}(comprim|cachet|pilule|gelule|medicament|sirop|boite|flacon|produit|javel|pile)",
    r"trop\sde\s(comprim|cachet|pilule|gelule|medicament|sirop|doliprane)",
    r"(bu|boit|ingere)\w*\s.{0,15}(javel|detergent|produit\s(menager|de\smenage)|essence|petrole)",
    # darija / arabe, lettres arabes
    r"تسمم|مسموم|سموم",
    r"جرعه ?(زايده|زائده|كبيره)",
    r"بلع\S*.{0,30}(بزاف|كامل|العلبه|\d{2,}|\b[5-9]\b)",
    r"شرب\S*.{0,25}(جافيل|جافال)",
    r"(خدا|كلا|خديت|كليت|خدات|كلات)\S* ?بزاف ?(د|ديال|من) ?(ال)?(دوا|حبوب|فنيد)",
]

_DETRESSE = [re.compile(p) for p in DETRESSE]
_INTOXICATION = [re.compile(p) for p in INTOXICATION]


def detecter_urgence(message: str) -> str | None:
    """'detresse', 'intoxication' ou None.

    Si les deux se retrouvent dans le message (surdosage ET perte de
    connaissance), detresse l'emporte : le SAMU passe avant le centre
    anti-poison quand la vie est menacee tout de suite.
    """
    texte = _normaliser(message)
    if any(p.search(texte) for p in _DETRESSE):
        return "detresse"
    if any(p.search(texte) for p in _INTOXICATION):
        return "intoxication"
    return None
