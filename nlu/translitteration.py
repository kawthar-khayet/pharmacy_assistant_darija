"""Translitteration arabe -> latin et cle phonetique, pour le matching.

Pourquoi ce module. Whisper n'a pas de modele de darija : une question posee
a la voix en darija ressort le plus souvent en **graphie arabe**. Les bases de
reference marocaines (AMMPS, CNOPS, CNSS, saydalia), elles, sont ecrites en
latin a la francaise. Sans pont entre les deux graphies, "دوليبران" ne
ressemble litteralement a rien dans la table et le matching renvoie zero
resultat -- c'etait la limite principale de l'entity linking, jusqu'ici
contournee par une table de correspondances ecrite a la main (8 entrees).

Le pont se fait en deux temps :

1. `translitterer` transcrit la graphie arabe en latin lisible, lettre par
   lettre (دوليبران -> "doulibran"). C'est une approximation : l'arabe note
   mal les voyelles breves et n'a ni p ni v.

2. `cle_phonetique` reduit une chaine latine -- la translitteration comme le
   nom de reference -- a un squelette sonore commun ou les distinctions que
   l'arabe ne fait pas disparaissent : p/b, v/f, s/z, k/q/c, i/e/y, o/u/w.
   "doulibran" et "DOLIPRANE" donnent tous deux `dolibran`, donc un match
   exact la ou la comparaison lettre a lettre plafonnait a 66 %.

La cle est volontairement grossiere : elle sert a **rapprocher** des candidats
(RapidFuzz departage ensuite), pas a decider seule. Deux medicaments aux noms
phonetiquement proches restent donc a confirmer par l'utilisateur -- c'est le
role des paliers de confiance de l'entity linking.
"""
import re
import unicodedata

# Diacritiques arabes (harakat, shadda, sukun) et tatweel : purement
# ornementaux ou prosodiques ici, jamais distinctifs dans un nom de produit.
_DIACRITIQUES = re.compile(r"[ً-ْٰـ]")

# Formes de la hamza et variantes de lettres, ramenees a leur support.
_NORMALISATIONS = {
    "آ": "a",   # آ
    "أ": "a",   # أ
    "إ": "i",   # إ
    "ؤ": "ou",  # ؤ
    "ئ": "i",   # ئ
    "ء": "",    # ء (hamza isolee : pas de son rendu en latin)
    "ى": "a",   # ى (alif maqsura)
    "ة": "a",   # ة (ta marbuta, prononce -a en finale)
}

# Une lettre arabe -> sa transcription latine la plus courante au Maroc.
# Les emphatiques (ص ض ط ظ) sont rendues comme leurs equivalents simples :
# la distinction existe en arabe mais pas dans les noms de marque latins.
_LETTRES = {
    "ا": "a",   # ا
    "ب": "b",   # ب
    "ت": "t",   # ت
    "ث": "t",   # ث
    "ج": "j",   # ج
    "ح": "h",   # ح
    "خ": "kh",  # خ
    "د": "d",   # د
    "ذ": "z",   # ذ
    "ر": "r",   # ر
    "ز": "z",   # ز
    "س": "s",   # س
    "ش": "ch",  # ش
    "ص": "s",   # ص
    "ض": "d",   # ض
    "ط": "t",   # ط
    "ظ": "z",   # ظ
    "ع": "",    # ع (pas de rendu latin : le plus souvent elide)
    "غ": "gh",  # غ
    "ف": "f",   # ف
    "ق": "k",   # ق
    "ك": "k",   # ك
    "ل": "l",   # ل
    "م": "m",   # م
    "ن": "n",   # ن
    "ه": "h",   # ه
    "و": "ou",  # و
    "ي": "i",   # ي
    # lettres ajoutees pour les sons absents de l'arabe classique, utilisees
    # en darija et dans les transcriptions de marques etrangeres
    "پ": "p",   # پ
    "ڤ": "v",   # ڤ
    "گ": "g",   # گ
    "چ": "ch",  # چ
    "ژ": "j",   # ژ
    "ڢ": "v",   # ڢ (variante maghrebine)
    "ڡ": "f",   # ڡ (variante maghrebine)
}

# Chiffres arabo-indiens (dosages dictes : "٥٠٠ ملغ").
_CHIFFRES = {chr(0x0660 + i): str(i) for i in range(10)}
_CHIFFRES.update({chr(0x06F0 + i): str(i) for i in range(10)})

_ARABE = re.compile(r"[؀-ۿݐ-ݿ]")


def contient_arabe(s: str) -> bool:
    return bool(_ARABE.search(str(s)))


def _sans_article(mot: str) -> str:
    """Retire l'article defini « ال » en tete de mot.

    « الدوليبران » (le Doliprane) doit matcher DOLIPRANE. On ne le retire que
    s'il reste assez de lettres derriere : sinon on ampute un mot qui commence
    reellement par ces deux lettres (ex. « الم », douleur)."""
    if mot.startswith("ال") and len(mot) >= 5:
        return mot[2:]
    return mot


def translitterer(texte: str) -> str:
    """Transcrit la graphie arabe d'un texte en latin lisible.

    Les portions deja en latin sont laissees telles quelles : les patients
    melangent les deux graphies dans une meme phrase ("بغيت doliprane")."""
    texte = _DIACRITIQUES.sub("", str(texte))
    sortie = []
    for mot in texte.split():
        if not contient_arabe(mot):
            sortie.append(mot)
            continue
        mot = _sans_article(mot)
        # Une hamza initiale devant و ou ي ne porte pas de voyelle propre :
        # elle amorce la voyelle longue qui suit. La rendre quand meme
        # ajouterait une syllabe parasite (أوميبرازول -> « aoumibrazoul »
        # au lieu de « oumibrazoul », qui est le bon OMEPRAZOLE).
        if len(mot) > 2 and mot[0] in _NORMALISATIONS and mot[1] in ("و", "ي"):
            mot = mot[1:]
        lettres = []
        for ch in mot:
            if ch in _NORMALISATIONS:
                lettres.append(_NORMALISATIONS[ch])
            elif ch in _LETTRES:
                lettres.append(_LETTRES[ch])
            elif ch in _CHIFFRES:
                lettres.append(_CHIFFRES[ch])
            elif _ARABE.match(ch):
                pass  # lettre arabe hors table : ignoree plutot qu'inventee
            else:
                lettres.append(ch)
        translit = "".join(lettres)
        sortie.append(translit if translit else mot)
    return " ".join(sortie)


def _sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# Reductions appliquees dans l'ordre. Les digrammes passent d'abord par une
# majuscule de travail (C, K, G) pour ne pas etre re-decoupes par les regles
# suivantes : sans cela le « c » de « ch » deviendrait un « k » isole.
_REDUCTIONS = [
    (r"sch", "C"), (r"sh", "C"), (r"ch", "C"),
    (r"kh", "K"), (r"gh", "G"),
    (r"ph", "f"), (r"th", "t"),
    (r"qu", "k"), (r"ck", "k"), (r"q", "k"),
    (r"c(?=[eiy])", "s"), (r"c", "k"),
    (r"x", "ks"),
    (r"gu", "g"), (r"g(?=[eiy])", "j"),
    (r"ou", "o"), (r"w", "o"),
    (r"v", "f"),   # l'arabe n'a pas de v : VOLTARENE est entendu « foltaren »
    (r"p", "b"),   # ni de p : « doliprane » s'ecrit avec un ب
    (r"z", "s"),
    (r"y", "i"), (r"e", "i"), (r"u", "o"),
    (r"h", ""),    # h muet en francais, h/ح indistincts a l'oreille ici
]

_SANS_LETTRE = re.compile(r"[^a-z0-9 ]")
_DOUBLES = re.compile(r"(.)\1+")


def cle_phonetique(texte: str) -> str:
    """Squelette sonore d'une chaine : deux graphies du meme nom convergent.

    S'applique indifferemment a une translitteration ("doulibran") et a un nom
    de la base ("DOLIPRANE") -- les deux donnent `dolibran`."""
    s = translitterer(texte) if contient_arabe(texte) else str(texte)
    s = _sans_accents(s.lower())
    s = _SANS_LETTRE.sub(" ", s)
    mots = []
    for mot in s.split():
        for motif, remplacement in _REDUCTIONS:
            mot = re.sub(motif, remplacement, mot)
        mot = mot.lower()
        mot = _DOUBLES.sub(r"\1", mot)  # gemination non distinctive
        # « -e » final muet en francais (DOLIPRANE), jamais note en arabe ; il
        # est devenu « i » plus haut, d'ou le retrait ici, sur les mots assez
        # longs pour que la finale ne porte pas l'essentiel du mot.
        if len(mot) > 3 and mot.endswith("i"):
            mot = mot[:-1]
        if mot:
            mots.append(mot)
    return " ".join(mots)


__all__ = ["translitterer", "cle_phonetique", "contient_arabe"]
