"""Lieux : du lieu ecrit par le patient a un point sur la carte.

Le patient cite une ville ("casa"), un quartier ("f m3arif", "المعاريف") ou
les deux ("maarif casa"). On le ramene a une ville ou un quartier connus, avec
une position GPS, pour que l'outil pharmacies donne les plus proches.

Sources, dans cet ordre :
  1. les villes de data/clean/pharmacies_fusion.csv (nom latin et arabe) ;
  2. les quartiers OSM de data/clean/quartiers.csv ;
  3. a defaut, les adresses de la fusion : beaucoup de quartiers manquent
     dans OSM (Sidi Maarouf, Ain Chok...) mais figurent dans l'annuaire.

Le resultat dit seulement ce qu'on a compris. C'est l'outil pharmacies qui
decide de demander la ville, le quartier, ou de repondre.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd
from rapidfuzz import fuzz, process

from nlp.config import DATA_CLEAN
from nlp.linking.translitteration import contient_arabe, translitterer

PHARMACIES_PATH = DATA_CLEAN / "pharmacies_fusion.csv"
QUARTIERS_PATH = DATA_CLEAN / "quartiers.csv"

# Ressemblance minimale (0-100) entre le lieu cite et un nom connu. Elevee car
# les noms de lieux sont courts : a 75, Taza et Tata se confondraient deja.
# "RBAT" -> "RABAT" passe encore (89).
SEUIL_NOM = 88

# Chercher un mot trop court dans les adresses trouve n'importe quoi.
LONGUEUR_MIN_ADRESSE = 4

# Seules ces positions situent l'officine ; "ville" ne situe que la ville.
PRECISIONS_FIABLES = {"exacte", "rue", "quartier"}

# Surnoms et ecritures darija des villes. Ce ne sont pas des fautes de frappe
# qu'une comparaison approchee rattraperait : "casa" n'a que 4 lettres de
# "Casablanca", "tanja" et "Tanger" ne se ressemblent qu'a 73.
SURNOMS_VILLES = {
    "casa": "Casablanca", "dar lbida": "Casablanca", "dar bida": "Casablanca",
    "كازا": "Casablanca", "كازابلانكا": "Casablanca", "الدار البيضا": "Casablanca",
    "البيضاء": "Casablanca",
    "mrakch": "Marrakech", "marrakesh": "Marrakech", "fas": "Fès", "meknas": "Meknès",
    "tanja": "Tanger", "titwan": "Tétouan", "sla": "Salé", "9nitra": "Kénitra",
    "jdida": "El Jadida", "ljdida": "El Jadida",
}

# Mots qui introduisent un lieu et n'en font pas partie ("f m3arif").
PREPOSITIONS_LATIN = re.compile(
    r"^(F|FI|FE|FL|B|BI|DYAL|DIAL|D|3ND|3AND|AND|HDA|7DA|9RIB MN|QRIB MN|PRES DE|PRES|"
    r"DANS|A|AU|AUX|EN|DE|DU|LA|LE|L)\s+"
)
PREPOSITIONS_ARABE = re.compile(r"^(في|ف|ب|عند|قرب|حدا|حدى|جنب|ديال|د)\s+")
_PREPOSITION_COLLEE = re.compile(r"^[فب](?=ال)")      # "فالمعاريف" -> "المعاريف"
# Restes en fin de texte une fois la ville retiree ("maarif f casa" -> "MAARIF F").
_PREPOSITIONS_FIN = {"F", "FI", "FE", "B", "BI", "A", "AU", "EN", "DE", "DU", "D", "DANS",
                     "في", "ف", "ب"}

# Mots generiques en tete d'un nom de quartier : "Hay Agdal" et "Agdal" sont
# le meme lieu pour le patient.
GENERIQUES_LATIN = {"HAY", "QUARTIER", "QRT"}
GENERIQUES_ARABE = {"حي"}

# Chiffres de l'arabizi, seulement colles a des lettres : "m3arif" est Maarif.
ARABIZI = {"2": "A", "3": "A", "5": "KH", "7": "H", "8": "H", "9": "Q"}
_CHIFFRE_COLLE = re.compile(r"(?<=[A-Z])([235789])|([235789])(?=[A-Z])")

_DIACRITIQUES_AR = re.compile(r"[ً-ْٰـ]")
_UNIFIER_AR = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي",
                             "ی": "ي", "گ": "ك", "ڭ": "ك", "ک": "ك"})


def _sans_generique(mots: list[str], generiques: set[str]) -> str:
    if len(mots) > 1 and mots[0] in generiques:
        mots = mots[1:]
    return " ".join(mots)


def _latin(texte: str) -> str:
    """Majuscules sans accents ni ponctuation : "Maârif" -> "MAARIF"."""
    s = "".join(c for c in unicodedata.normalize("NFD", str(texte)) if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^A-Z0-9 ]", " ", s.upper())
    return re.sub(r"\s+", " ", s).strip()


def _cle_latine(texte: str) -> str:
    s = PREPOSITIONS_LATIN.sub("", _latin(texte))
    s = _CHIFFRE_COLLE.sub(lambda m: ARABIZI[m.group(0)], s)
    return _sans_generique(s.split(), GENERIQUES_LATIN)


def _cle_arabe(texte: str) -> str:
    """Les variantes d'ecriture (أ/ا, ة/ه, گ/ك) et l'article sont effaces :
    "فالمعاريف" et "المعاريف" donnent tous deux "معاريف"."""
    s = _DIACRITIQUES_AR.sub("", str(texte)).translate(_UNIFIER_AR)
    s = re.sub(r"[^ء-ي ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = _PREPOSITION_COLLEE.sub("", PREPOSITIONS_ARABE.sub("", s))
    mots = [m[2:] if m.startswith("ال") and len(m) >= 4 else m for m in s.split()]
    return _sans_generique(mots, GENERIQUES_ARABE)


def _cle(texte) -> str:
    """Forme de comparaison d'un nom de lieu, dans sa propre graphie."""
    if texte is None or pd.isna(texte) or not str(texte).strip():
        return ""
    return _cle_arabe(texte) if contient_arabe(texte) else _cle_latine(texte)


# OSM classe aussi en "pharmacy" des parapharmacies, drogueries et
# herboristeries, qui ne vendent pas de medicaments. On les ecarte, sauf si le
# nom contient le mot "pharmacie" seul ("Para & Pharmacie Benzit" en est une).
_PAS_PHARMACIE = re.compile(r"para|drogu|herbor|v[ée]t[ée]rin", re.IGNORECASE)
_MOT_PHARMACIE = re.compile(r"\bpharmac(ie|y)\b|صيدلي", re.IGNORECASE)


def est_pharmacie(nom) -> bool:
    nom = "" if pd.isna(nom) else str(nom)
    return not _PAS_PHARMACIE.search(nom) or bool(_MOT_PHARMACIE.search(nom))


@lru_cache(maxsize=1)
def charger_pharmacies() -> pd.DataFrame:
    """La fusion OSM + annuaire, chargee une fois par serveur et partagee avec
    linking/pharmacies.py."""
    df = pd.read_csv(PHARMACIES_PATH, dtype={"id": str, "telephone": str})
    df = df[df["nom"].map(est_pharmacie)].reset_index(drop=True)
    df["position_fiable"] = df["precision_gps"].isin(PRECISIONS_FIABLES) & df["latitude"].notna()
    return df


@dataclass
class Lieu:
    cite: str                                   # tel qu'ecrit par le patient
    statut: str = "introuvable"                 # "quartier" | "ville" | "ambigu" | "introuvable"
    nom: str | None = None                      # quartier (ou ville) retenu, pour le redire
    ville: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source: str | None = None                   # "osm" | "adresses" : d'ou vient la position du quartier
    villes_possibles: list[str] = field(default_factory=list)   # si ambigu
    quartier_inconnu: str | None = None         # "xyz casa" : ville reconnue, quartier non


@dataclass
class _Connu:
    nom: str
    ville: str
    latitude: float
    longitude: float


def _centre(connus: list[_Connu]) -> _Connu:
    """Un meme quartier peut figurer deux fois dans OSM (deux points)."""
    return _Connu(connus[0].nom, connus[0].ville,
                  sum(c.latitude for c in connus) / len(connus),
                  sum(c.longitude for c in connus) / len(connus))


class _Index:
    def __init__(self):
        ph = charger_pharmacies()

        # Centre de chaque ville : mediane des officines bien placees, que
        # quelques points aberrants ne deplacent pas.
        self.villes: dict[str, _Connu] = {}
        for ville, groupe in ph[ph["latitude"].notna()].groupby("ville"):
            base = groupe[groupe["position_fiable"]]
            base = base if not base.empty else groupe
            self.villes[ville] = _Connu(ville, ville, float(base["latitude"].median()),
                                        float(base["longitude"].median()))

        self.formes_villes: dict[str, str] = {}          # cle -> ville
        for ville, ville_ar in ph[["ville", "ville_ar"]].drop_duplicates().itertuples(index=False):
            for forme in (ville, ville_ar):
                if (cle := _cle(forme)):
                    self.formes_villes.setdefault(cle, ville)
        for surnom, ville in SURNOMS_VILLES.items():
            if ville in self.villes:
                self.formes_villes.setdefault(_cle(surnom), ville)
        self.cles_villes = list(self.formes_villes)

        self.formes_quartiers: dict[str, list[_Connu]] = {}
        for r in pd.read_csv(QUARTIERS_PATH).itertuples(index=False):
            nom = r.nom if pd.notna(r.nom) else r.nom_ar
            connu = _Connu(nom, r.ville, float(r.latitude), float(r.longitude))
            autres = str(r.autres_noms).split("|") if pd.notna(r.autres_noms) else []
            for forme in (r.nom, r.nom_ar, *autres):
                if (cle := _cle(forme)):
                    self.formes_quartiers.setdefault(cle, []).append(connu)
        self.cles_quartiers = list(self.formes_quartiers)

        # Adresses en latin simple, sans arabizi : leurs chiffres sont de
        # vrais numeros ("imm. A3").
        self.adresses = ph[ph["adresse"].notna() & ph["position_fiable"]].copy()
        self.adresses["adresse_cle"] = self.adresses["adresse"].apply(_latin)

    def separer_ville(self, cle: str) -> tuple[str | None, str]:
        """"MAARIF CASA" -> ("Casablanca", "MAARIF"). La ville est cherchee
        parmi les groupes de 1 a 3 mots : le plus ressemblant, puis le plus long."""
        mots = cle.split()
        meilleur = None                                   # (score, nb_mots, ville, debut, fin)
        for n in range(min(3, len(mots)), 0, -1):
            for i in range(len(mots) - n + 1):
                hit = process.extractOne(" ".join(mots[i:i + n]), self.cles_villes,
                                         scorer=fuzz.ratio, score_cutoff=SEUIL_NOM)
                if hit and (meilleur is None or (hit[1], n) > meilleur[:2]):
                    meilleur = (hit[1], n, self.formes_villes[hit[0]], i, i + n)
        if not meilleur:
            return None, cle
        _, _, ville, i, j = meilleur
        reste = mots[:i] + mots[j:]
        while reste and reste[-1] in _PREPOSITIONS_FIN:
            reste = reste[:-1]
        generiques = GENERIQUES_ARABE if contient_arabe(cle) else GENERIQUES_LATIN
        return ville, _sans_generique(reste, generiques)

    def quartiers(self, cle: str) -> dict[str, _Connu]:
        """Quartiers OSM ressemblant a `cle`, un par ville (le plus ressemblant)."""
        if not cle:
            return {}
        par_ville: dict[str, tuple[float, list[_Connu]]] = {}
        for forme, score, _ in process.extract(cle, self.cles_quartiers, scorer=fuzz.ratio,
                                               score_cutoff=SEUIL_NOM, limit=None):
            for connu in self.formes_quartiers[forme]:
                meilleur = par_ville.get(connu.ville)
                if meilleur is None or score > meilleur[0]:
                    par_ville[connu.ville] = (score, [connu])
                elif score == meilleur[0]:
                    meilleur[1].append(connu)
        return {ville: _centre(connus) for ville, (_, connus) in par_ville.items()}

    def adresses_contenant(self, cle: str) -> dict[str, tuple[_Connu, int]]:
        """Quartier cite dans les adresses de l'annuaire : centre des officines
        dont l'adresse le contient, et leur nombre, par ville. Mot entier
        seulement, pour que "ANFA" ne trouve pas "ANFAL"."""
        if contient_arabe(cle) or len(cle.replace(" ", "")) < LONGUEUR_MIN_ADRESSE:
            return {}
        motif = re.compile(rf"\b{re.escape(cle)}\b")
        trouvees = self.adresses[self.adresses["adresse_cle"].str.contains(motif)]
        nom = cle.title()
        return {
            ville: (_Connu(nom, ville, float(g["latitude"].mean()), float(g["longitude"].mean())), len(g))
            for ville, g in trouvees.groupby("ville")
        }

    def lieu_ville(self, cite: str, ville: str) -> Lieu:
        c = self.villes.get(ville)
        return Lieu(cite, "ville", nom=ville, ville=ville,
                    latitude=c.latitude if c else None, longitude=c.longitude if c else None)

    def quartier(self, cherche: str, cite: str, ville: str | None,
                 ville_connue: str | None) -> Lieu | None:
        """Le quartier `cherche`, dans `ville` si elle est donnee ; None s'il
        n'existe nulle part (ou pas dans cette ville).

        OSM et l'annuaire sont reunis : OSM ne connait que le Oulfa d'El Jadida,
        l'annuaire cite celui de Casablanca dans ses adresses. Une ville que
        seules les adresses donnent n'est gardee, a cote d'OSM, que si au moins
        deux officines la citent : un mot peut figurer une fois par hasard.
        """
        candidats: dict[str, tuple[_Connu, str]] = {
            v: (q, "osm") for v, q in self.quartiers(cherche).items()}
        osm = bool(candidats)
        for v, (q, n) in self.adresses_contenant(cherche).items():
            if v not in candidats and (n >= 2 or not osm or v == ville):
                candidats[v] = (q, "adresses")
        if ville:
            choisie = ville if ville in candidats else None
            if choisie is None:
                return None
        elif ville_connue in candidats:
            # la ville d'un message precedent departage des homonymes
            choisie = ville_connue
        elif len(candidats) == 1:
            choisie = next(iter(candidats))
        elif candidats:
            nom = next(iter(candidats.values()))[0].nom
            return Lieu(cite, "ambigu", nom=nom, villes_possibles=sorted(candidats))
        else:
            return None
        q, source = candidats[choisie]
        return Lieu(cite, "quartier", nom=q.nom, ville=q.ville,
                    latitude=q.latitude, longitude=q.longitude, source=source)

    def resoudre(self, cle: str, cite: str, ville_connue: str | None) -> Lieu:
        if not cle:
            return Lieu(cite)
        # 1. Le texte entier est une ville ("casa", "الرباط").
        if (hit := process.extractOne(cle, self.cles_villes, scorer=fuzz.ratio, score_cutoff=SEUIL_NOM)):
            return self.lieu_ville(cite, self.formes_villes[hit[0]])
        # 2. Le texte entier est un quartier. Avant de chercher une ville dans
        #    ses mots : "yacoub el mansour" (Rabat) contient presque le nom de
        #    la commune El Mansouria.
        if (lieu := self.quartier(cle, cite, None, ville_connue)):
            return lieu
        # 3. "quartier + ville" : "maarif casa".
        ville, reste = self.separer_ville(cle)
        if not ville:
            return Lieu(cite)
        if reste and (lieu := self.quartier(reste, cite, ville, None)):
            return lieu
        lieu = self.lieu_ville(cite, ville)
        if reste:
            lieu.quartier_inconnu = reste if contient_arabe(reste) else reste.title()
        return lieu


@lru_cache(maxsize=1)
def _index() -> _Index:
    return _Index()


def resoudre_lieu(texte: str | None, ville_connue: str | None = None) -> Lieu:
    """Ville ou quartier cite par le patient.

    ville_connue : ville deja etablie plus tot dans la conversation, pour ne
    pas redemander "Agdal, a Rabat ou a Fes ?" a qui a deja dit Rabat.
    """
    if not texte or not texte.strip():
        return Lieu(texte or "")
    idx = _index()
    cles = [_cle(texte)]
    if contient_arabe(texte):
        # Arabe d'abord ; a defaut, la translitteration vers les noms latins.
        cles.append(_cle_latine(translitterer(texte)))

    repli = Lieu(texte)
    for cle in cles:
        lieu = idx.resoudre(cle, texte, ville_connue)
        if lieu.statut in ("quartier", "ambigu") or (lieu.statut == "ville" and not lieu.quartier_inconnu):
            return lieu
        if repli.statut == "introuvable":
            repli = lieu
    return repli
