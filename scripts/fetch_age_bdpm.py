"""A qui s'adresse chaque presentation (adulte, enfant, a partir de quel age ou
de quel poids), d'apres les notices officielles de la BDPM.

La base marocaine ne dit presque jamais si une presentation est pour l'enfant :
"DOLIPRANE 100 MG, SACHET" ne porte aucune mention. La notice francaise de la
meme presentation, elle, le dit ("reservee a l'enfant de 6 a 8 kg"). Pour
chaque presentation marocaine (molecule, dosage, forme), on cherche donc une
specialite francaise de MEME composition, MEME dosage et MEME voie, et on lit
dans sa notice les phrases qui parlent d'age ou de poids.

Entrees :
  - un CSV avec une colonne de molecules (par defaut la proposition de conseil)
  - data/clean/medicaments_reference.csv
  - BDPM : CIS_bdpm.txt, CIS_COMPO_bdpm.txt + notices en ligne (cache local)

Sortie :
  - data/clean/age_presentations.csv : une ligne par presentation marocaine,
    avec le public, la phrase de la notice mot pour mot et sa source.

Ce qui est ecrit dans `phrase_notice` est le texte officiel. `public` et
`age_min` en sont une lecture automatique : a relire avant usage.

Usage :
    py scripts/fetch_age_bdpm.py
    py scripts/fetch_age_bdpm.py --source data/clean/conseil_symptomes.csv --colonne dci
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from fetch_securite_bdpm import (  # noqa: E402
    BDPM, FIN_NOTICE, charger_bdpm, cle, cle_base, composition_de, sans_accents, texte_notice,
)
from nlp.linking.medicaments import STATUTS_EN_OFFICINE, famille_forme  # noqa: E402

REF_PATH = ROOT / "data" / "clean" / "medicaments_reference.csv"
OUT_PATH = ROOT / "data" / "clean" / "age_presentations.csv"
SOURCE_DEFAUT = ROOT / "docs" / "proposition_conseil_ansm.csv"

SEPARATEURS_DCI = re.compile(r"\s*//\s*|\s*/\s*")

# --- dosage : "500 MG", "1 G", "2 %", "20 MG / ML" -> (valeur en unite de base, unite)
_UNITES = {"mg": ("mg", 1), "g": ("mg", 1000), "microgrammes": ("mg", 0.001), "mcg": ("mg", 0.001),
           "µg": ("mg", 0.001), "ug": ("mg", 0.001), "%": ("%", 1), "pour cent": ("%", 1), "ml": ("ml", 1),
           "ui": ("ui", 1)}
# "%" n'est pas un caractere de mot : pas de \b apres lui
_DOSE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(%|pour cent|(?:mg|g|microgrammes|mcg|µg|ug|ml|ui)\b)", re.I)


def dose(texte) -> tuple[float, str] | None:
    """Premiere quantite d'un dosage, ramenee a une unite commune."""
    if not isinstance(texte, str):
        return None
    m = _DOSE.search(texte.replace(" ", " ").replace("POUR CENT", "%").replace("pour cent", "%"))
    if not m:
        return None
    unite, facteur = _UNITES[m.group(2).lower()]
    return round(float(m.group(1).replace(",", ".")) * facteur, 6), unite


def voie(texte) -> str:
    """Voie d'administration d'une forme (marocaine ou francaise) ; "" si inconnue."""
    f = famille_forme(sans_accents(texte).upper()) if isinstance(texte, str) else ""
    return "" if f.startswith("autre") else f


# --- phrases de la notice qui disent a qui s'adresse le medicament
PHRASE_AGE = re.compile(
    r"r[ée]serv[ée]e?s? (?:[àa]|au|aux) |"
    r"(?:chez|de|pour) l[’']adulte|adultes? et (?:l[’'])?enfants?|adultes? et (?:l[’'])?adolescents?|"
    r"enfants? (?:de|[àa] partir|[âa]g[ée]s?|pesant|de plus|de moins)|"
    r"nourrissons? (?:de|[àa] partir|[âa]g[ée]s?|pesant|et)|"
    r"[àa] partir de \d+ ?(?:ans|mois|kg)|de plus de \d+ ?(?:ans|mois|kg)|de moins de \d+ ?(?:ans|mois|kg)|"
    r"contre-indiqu[ée]e? chez (?:l[’'])?enfant", re.I)
ADULTE_SEUL = re.compile(r"r[ée]serv[ée]e?s? [àa] l[’']adulte(?! et)|(?:de|chez|pour) l[’']adulte(?! et| ou)(?!s)", re.I)
ENFANT_SEUL = re.compile(r"r[ée]serv[ée]e?s? (?:[àa] l[’']enfant|au nourrisson|aux enfants|aux nourrissons)", re.I)
A_PARTIR = re.compile(
    r"(?:[àa] partir de|de plus de|[âa]g[ée]s? de plus de|pesant plus de|d[’']au moins)\s*(\d+ ?(?:ans|mois|kg))"
    r"(\s*\((?:environ|soit)[^)]{0,40}\))?", re.I)
INTERVALLE = re.compile(r"(?:enfants?|nourrissons?)[^.]{0,40}?de\s*(\d+ ?(?:ans|mois|kg)? ?(?:[àa]|-) ?\d+ ?(?:ans|mois|kg))"
                        r"(\s*\((?:environ|soit)[^)]{0,60}\))?", re.I)


def corps(texte: str) -> str:
    """La notice sans son sommaire ni ses dernieres rubriques (conservation, emballage)."""
    debuts = [m.start() for m in re.finditer(r"1\.\s*QU[’']?EST[- ]CE QUE", texte, re.I)]
    fins = [m.start() for m in re.finditer(FIN_NOTICE, texte, re.I)]
    debut = debuts[-1] if debuts else 0
    fin = next((f for f in reversed(fins) if f > debut), len(texte))
    return texte[debut:fin]


def phrases_age(texte: str, combien: int = 3) -> list[str]:
    """Les phrases de la notice qui parlent d'age ou de poids, mot pour mot."""
    trouvees = []
    for phrase in re.split(r"(?<=[.!?])\s+|\n", corps(texte)):
        phrase = re.sub(r"\s+", " ", phrase).strip(" ·•-")
        if 25 < len(phrase) < 400 and PHRASE_AGE.search(phrase) and phrase not in trouvees:
            trouvees.append(phrase)
    # d'abord celles qui tranchent ("reserve a..."), puis l'indication
    trouvees.sort(key=lambda p: (not re.search(r"r[ée]serv", p, re.I), not re.search(r"indiqu", p, re.I)))
    return trouvees[:combien]


def lire_public(phrases: list[str]) -> tuple[str, str]:
    """(public, age ou poids minimum) lus dans les phrases ; ("non précisé", "") sinon."""
    # "reserve a l'enfant de plus de 2 ans [...] et chez l'adulte" (Smecta) n'est
    # pas un medicament pour enfant seulement : les autres phrases le disent.
    aussi_adulte = any(re.search(r"adulte", p, re.I) for p in phrases)
    for p in phrases:
        if ENFANT_SEUL.search(p):
            m = INTERVALLE.search(p) or A_PARTIR.search(p)
            age = (m.group(1) + (m.group(2) or "")).strip() if m else ""
            if aussi_adulte:
                return "adulte et enfant", f"à partir de {age}" if age else ""
            return "enfant", age
    # "chez l'adulte et l'enfant de plus de 8 ans" passe avant "chez l'adulte" :
    # une autre phrase de la meme notice peut ne citer que l'adulte (Forlax).
    for p in phrases:
        if re.search(r"adultes?,? (?:et|ou) (?:[àa] )?(?:l[’']|aux |les )?(?:enfants?|adolescents?)", p, re.I) \
                or re.search(r"enfant", p, re.I):
            m = A_PARTIR.search(p)
            if m:
                return "adulte et enfant", ("à partir de " + m.group(1) + (m.group(2) or "")).strip()
    for p in phrases:
        if ADULTE_SEUL.search(p) and not re.search(r"enfant|adolescent", p, re.I):
            return "adulte", ""
    return "non précisé", ""


def molecules_de(chemin: Path, colonne: str) -> list[str]:
    valeurs = pd.read_csv(chemin, encoding="utf-8-sig")[colonne].dropna().astype(str)
    molecules = []
    for v in valeurs:
        for ecriture in v.split("|"):          # "CETIRIZINE (DICHLORHYDRATE)|CETIRIZINE"
            if ecriture.strip() and ecriture.strip() not in molecules:
                molecules.append(ecriture.strip())
    return molecules


def main(source: Path, colonne: str) -> None:
    molecules = molecules_de(source, colonne)
    reference = pd.read_csv(REF_PATH)
    vendus = reference[reference["statut_commercialisation"].isna()
                       | reference["statut_commercialisation"].isin(STATUTS_EN_OFFICINE)]
    cis, compo = charger_bdpm()
    compo = compo.assign(cle=compo["substance"].map(cle_base))
    compositions = compo.groupby("cis")["cle"].agg(set).to_dict()
    index_substances = {c: True for c in compo["cle"].unique()}
    cis = cis.assign(voie=cis["forme"].map(voie), dose=cis["denomination"].map(dose),
                     vendue=cis["etat_commercialisation"].str.contains("Commercialis", na=False))

    lignes, sans_notice = [], 0
    for molecule in molecules:
        presentations = (vendus[vendus["dci"].fillna("").str.upper() == molecule.upper()]
                         [["dosage", "forme"]].drop_duplicates())
        if presentations.empty:
            continue
        cherchees = {composition_de(a, index_substances) for a in SEPARATEURS_DCI.split(molecule)}
        if None in cherchees:
            continue                                  # molecule absente de la BDPM
        candidats = cis[cis["cis"].isin([c for c, s in compositions.items() if s == cherchees])]
        for p in presentations.itertuples():
            v, d = voie(p.forme), dose(p.dosage)
            memes = candidats[(candidats["voie"] == v) & (candidats["dose"] == d)] if v and d else candidats.iloc[0:0]
            ligne = {"molecule": molecule, "dosage": p.dosage, "forme": p.forme, "public": "non précisé",
                     "age_min": "", "phrase_notice": "", "specialite_bdpm": "", "cis": "", "source_url": ""}
            # la notice d'une specialite commercialisee d'abord ; toutes n'en ont pas en ligne
            for spec in memes.sort_values("vendue", ascending=False).head(3).itertuples():
                texte = texte_notice(spec.cis)
                phrases = phrases_age(texte) if texte else []
                if not phrases:
                    continue
                public, age = lire_public(phrases)
                ligne |= {"public": public, "age_min": age, "phrase_notice": " // ".join(phrases),
                          "specialite_bdpm": spec.denomination, "cis": spec.cis,
                          "source_url": f"{BDPM}/affichageDoc.php?specid={spec.cis}&typedoc=N"}
                break
            else:
                sans_notice += 1
            lignes.append(ligne)
        print(f"  {molecule} : {len(presentations)} presentations", flush=True)

    resultat = pd.DataFrame(lignes)
    resultat.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n{len(resultat)} presentations -> {OUT_PATH}")
    print(resultat["public"].value_counts().to_string())
    print(f"sans specialite francaise de meme dosage et de meme voie, ou sans notice : {sans_notice}")


if __name__ == "__main__":
    analyseur = argparse.ArgumentParser()
    analyseur.add_argument("--source", type=Path, default=SOURCE_DEFAUT)
    analyseur.add_argument("--colonne", default="molecule")
    arguments = analyseur.parse_args()
    main(arguments.source, arguments.colonne)
