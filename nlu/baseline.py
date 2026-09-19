"""Baseline NLU classique, pour comparer au LLM few-shot (llm_prototype.py).

Deux briques volontairement simples, toutes deux entrainables ou applicables
en quelques millisecondes sur CPU, sans service externe :

  - Intent : TF-IDF sur n-grammes de caracteres + regression logistique.
    Les n-grammes de caracteres (et non de mots) encaissent les graphies
    variables de la darija latine ("chhal" / "ch7al", "3andkom" / "3ndkom") et
    les fautes de frappe, sans tokenisation specifique a une langue.

  - Entites : regles et lexiques (gazetteers). Aucun apprentissage.

Regle d'honnetete : les lexiques ci-dessous sont ecrits a partir de
connaissances generales (nombres en darija et en francais, formes galeniques,
grands quartiers marocains) et de la base de reference des medicaments -- JAMAIS
a partir des annotations de seed_dataset.jsonl, qui sert de jeu de test. Un
lexique construit sur les etiquettes de test ferait tricher la baseline.
"""
import re
import unicodedata

import pandas as pd
from rapidfuzz import fuzz, process
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

from entity_linking import ARABIC_TO_LATIN, REFERENCE_PATH


# ---------------------------------------------------------------- intents

def nouveau_classifieur_intent():
    """Hyperparametres fixes a priori (valeurs courantes pour du texte court),
    pas regles sur les resultats : les regler sur le jeu de test gonflerait
    artificiellement le score de la baseline."""
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, lowercase=True),
        LogisticRegression(C=10, max_iter=5000, class_weight="balanced"),
    )


# ---------------------------------------------------------------- entites

def _sans_accent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    return _sans_accent(s).upper()


NOMBRES = {
    # darija latine (chiffres arabizi compris)
    "wa7ed", "wahed", "wa7da", "wahda", "juj", "zouj", "zuj", "tlata", "tlatha",
    "rb3a", "reb3a", "arb3a", "khamsa", "sta", "seb3a", "sb3a", "tmnya", "ts3ud", "3chra",
    # francais
    "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
    # arabe
    "واحد", "واحدة", "جوج", "زوج", "ثلاثة", "تلاتة", "ربعة", "أربعة", "خمسة",
}

FORMES = {
    "comprime", "comprimes", "gelule", "gelules", "sirop", "sirops", "pommade", "creme",
    "boite", "boites", "flacon", "flacons", "sachet", "sachets", "suppositoire",
    "suppositoires", "ampoule", "ampoules", "gouttes", "spray", "injection",
    "3elba", "3olab", "3elab", "l3elba",
    "علبة", "علب", "شراب", "حبوب", "دوا",
}

QUARTIERS = {
    # grands quartiers, de notoriete publique -- pas tires du jeu de test
    "maarif", "agdal", "gueliz", "hay hassani", "hay riad", "ain diab", "anfa",
    "bourgogne", "oulfa", "sidi maarouf", "ain chock", "hay mohammadi", "derb sultan",
    "racine", "californie", "medina", "hivernage", "souissi", "hassan", "ocean",
    "belvedere", "sidi belyout", "bernoussi", "sbata", "ben msik", "mers sultan",
}

MOTS_VIDES = {
    # mots courants du domaine susceptibles de ressembler a un nom de medicament
    # en comparaison floue. Liste fixee a priori : l'enrichir en regardant les
    # erreurs sur le jeu de test reviendrait a regler la baseline sur ce jeu.
    "BGHIT", "KAYN", "KAYNA", "WACH", "CHHAL", "TAMAN", "DYAL", "BOITE", "BOITES",
    "COMPRIME", "SIROP", "BONJOUR", "MERCI", "COMMENT", "PRENDRE", "EFFETS",
    "SECONDAIRES", "PHARMACIE", "SIDALIA", "SAYDALIA", "RESERVER", "COMMANDER",
    "VOUDRAIS", "AVEZ", "VOUS", "EST", "QUEL", "PRIX", "COMBIEN",
}

RE_DOSAGE = re.compile(r"\b\d+(?:[.,]\d+)?\s?(?:mg|g|ml|mcg|µg|ui)\b", re.IGNORECASE)
RE_CHIFFRE = re.compile(r"^\d+$")
RE_PHARMACIE = re.compile(
    r"(?:pharmacie|sidalia|saydalia)\s+((?:[A-Z][\w']+)(?:\s+[A-Z][\w']+)*)"
)
RE_MOT = re.compile(r"[\w']+", re.UNICODE)


class ExtracteurRegles:
    def __init__(self):
        df = pd.read_csv(REFERENCE_PATH, usecols=["nom", "dci"], dtype=str)
        noms = set()
        for nom in df["nom"].dropna():
            premier = _norm(str(nom)).split()[0] if str(nom).strip() else ""
            if len(premier) >= 5 and premier.isalpha():
                noms.add(premier)
        for dci in df["dci"].dropna():
            premier = _norm(str(dci)).split()[0] if str(dci).strip() else ""
            if len(premier) >= 5 and premier.isalpha():
                noms.add(premier)
        self.noms = sorted(noms - MOTS_VIDES)
        self.noms_set = set(self.noms)

        villes = pd.read_csv(REFERENCE_PATH.parent / "pharmacies_reference.csv", usecols=["ville"], dtype=str)
        self.lieux = {_sans_accent(v).lower() for v in villes["ville"].dropna()} | QUARTIERS

    def _medicament(self, mot: str) -> str | None:
        """Renvoie le nom de medicament contenu dans `mot`, ou None.

        L'article elide francais ("l'", "d'") est retire avant la comparaison
        ET dans la valeur renvoyee : l'entite est le nom du produit, pas le
        groupe nominal ("amoxicilline", pas "l'amoxicilline")."""
        brut = mot
        for prefixe in ("l'", "d'"):
            if brut.lower().startswith(prefixe):
                brut = brut[len(prefixe):]
        if brut in ARABIC_TO_LATIN:
            return brut
        cle = _norm(brut)
        if len(cle) < 5 or not cle.isalpha() or cle in MOTS_VIDES:
            return None
        if cle in self.noms_set:
            return brut
        meilleur = process.extractOne(cle, self.noms, scorer=fuzz.ratio, score_cutoff=88)
        return brut if meilleur is not None else None

    def extraire(self, texte: str) -> list[dict]:
        entites: list[dict] = []
        vus: set[tuple[str, str]] = set()

        def ajouter(type_, valeur):
            cle = (type_, valeur.lower())
            if valeur and cle not in vus and valeur in texte:
                vus.add(cle)
                entites.append({"type": type_, "value": valeur})

        for m in RE_DOSAGE.finditer(texte):
            ajouter("DOSAGE", m.group(0))

        m = RE_PHARMACIE.search(texte)
        if m:
            ajouter("PHARMACIE", m.group(1))

        bas = _sans_accent(texte).lower()
        for lieu in sorted(self.lieux, key=len, reverse=True):
            if len(lieu) >= 4 and re.search(rf"(?<!\w){re.escape(lieu)}(?!\w)", bas):
                debut = bas.index(lieu)
                ajouter("LOCALISATION", texte[debut:debut + len(lieu)])

        mots = [(m.group(0), m.start()) for m in RE_MOT.finditer(texte)]
        for i, (mot, _) in enumerate(mots):
            bas_mot = _sans_accent(mot).lower()
            suivant = _sans_accent(mots[i + 1][0]).lower() if i + 1 < len(mots) else ""

            if bas_mot in FORMES:
                ajouter("FORME", mot)
            # une quantite n'est retenue que devant une forme ("juj boites") :
            # isole, "wa7ed" ou "deux" est bien trop souvent autre chose
            elif (bas_mot in NOMBRES or RE_CHIFFRE.match(bas_mot)) and suivant in FORMES:
                ajouter("QUANTITE", mot)
            elif (nom := self._medicament(mot)):
                ajouter("MEDICAMENT", nom)

        return entites
