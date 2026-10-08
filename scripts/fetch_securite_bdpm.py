"""Constitue une base d'informations de securite par molecule, depuis la BDPM.

Entrees :
  - data/clean/medicaments_reference.csv   (les DCI du marche marocain)
  - BDPM (ANSM, open data) : CIS_bdpm.txt, CIS_COMPO_bdpm.txt + notices en ligne

Sorties :
  - data/clean/securite_medicaments.csv    (5 rubriques par molecule)
  - data/clean/securite_report.txt         (couverture)
  - data/raw/bdpm_notices/<cis>.html       (cache des notices telechargees)

Pourquoi la BDPM plutot qu'une source americaine (openFDA, DailyMed) : les
specialites marocaines viennent de la meme filiere que les francaises --
Doliprane, Spasfon, Augmentin y figurent sous le meme nom -- et les notices sont
deja en francais. Aucune traduction n'est necessaire, donc aucun risque de
deformer une contre-indication.

Ce qui est stocke est le texte officiel, mot pour mot. Le resume en darija est
produit a l'affichage, avec le texte complet en dessous : la base, elle, ne
contient que du verbatim.

L'unite est la molecule (DCI), pas le produit : la contre-indication du
paracetamol vaut pour Doliprane comme pour Panadol. On choisit donc une
specialite francaise representative par molecule et on lit sa notice.

Usage :
    py scripts/fetch_securite_bdpm.py            # 300 molecules les plus repandues
    py scripts/fetch_securite_bdpm.py --top 20   # echantillon de mise au point
"""
import argparse
import re
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
REF_PATH = ROOT / "data" / "clean" / "medicaments_reference.csv"
RAW_DIR = ROOT / "data" / "raw"
NOTICES_DIR = RAW_DIR / "bdpm_notices"
OUT_PATH = ROOT / "data" / "clean" / "securite_medicaments.csv"
RAPPORT_PATH = ROOT / "data" / "clean" / "securite_report.txt"

BDPM = "https://base-donnees-publique.medicaments.gouv.fr"
FICHIERS = {"cis": "CIS_bdpm.txt", "compo": "CIS_COMPO_bdpm.txt"}
ENTETES = {"User-Agent": "DwaTalk/0.1 (projet etudiant, assistant pharmacie Maroc)"}
DELAI_S = 1.0  # une notice par seconde : le site est un service public, pas une API

SEPARATEUR_DCI = "//"
SEUIL_SUBSTANCE = 92

# Debut de chaque rubrique dans une notice francaise, dans l'ordre ou elles
# apparaissent. La rubrique court jusqu'au debut de la suivante.
RUBRIQUES = [
    # Le titre des contre-indications varie avec la forme du medicament : on
    # prend un comprime, on donne un sirop a un enfant, on utilise ou on
    # applique une solution. Le nom de la specialite, en capitales, doit
    # suivre : sans cette exigence, la phrase "Ne donnez jamais votre
    # antibiotique a une autre personne", dans la notice du Flagyl, etait prise
    # pour le titre de la rubrique.
    ("contre_indications",
     r"(?:Ne prenez|Ne donnez|N['’]utilisez|N['’]appliquez|Ne pas prendre|Ne pas utiliser|"
     r"Ne pas donner)\s+jamais\s+[A-ZÉÈÀÎÔÛ0-9]"),
    ("precautions", r"Avertissements et pr[ée]cautions"),
    ("interactions", r"Autres m[ée]dicaments et |Interactions avec d['’]autres m[ée]dicaments"),
    ("grossesse_allaitement", r"Grossesse(?: et|,) allaitement"),
    ("effets_indesirables", r"4\.\s*QUELS SONT LES EFFETS IND[ÉE]SIRABLES"),
]

# Ecart minimal entre le titre des contre-indications et celui des precautions
# pour qu'il s'agisse du corps de la notice et non de son sommaire, ou les
# memes titres se suivent a quelques mots d'intervalle.
ECART_SOMMAIRE = 250

# Rubrique 1 de la notice : a quoi sert le medicament. Elle est decoupee a part
# des autres, car elle se lit entre les titres 1 et 2 et non dans la suite du
# corps. C'est la reponse a "chno kaydir had dwa ?", la question la plus
# naturelle d'un patient -- et la seule des grandes rubriques qui manquait.
DEBUT_INDICATIONS = re.compile(
    r"1\.\s*QU[’']?EST-CE QUE [^\n]{0,160}\?|1\.\s*QU[’']?EST CE QUE [^\n]{0,160}\?", re.I
)
FIN_INDICATIONS = re.compile(r"2\.\s*QUELLES SONT LES INFORMATIONS", re.I)
# La premiere ligne rappelle la classe et le code ATC : utile ailleurs, mais
# ce n'est pas une indication, et elle ouvrirait le texte sur du jargon.
LIGNE_CLASSE = re.compile(r"^\s*Classe pharmacoth[ée]rapeutique[^\n]*\n?", re.I)
# Ce qui ferme la derniere rubrique.
FIN_NOTICE = r"5\.\s*COMMENT CONSERVER"

# Code ATC officiel de la specialite, annonce en tete de la rubrique 1 de la
# notice ("Classe pharmacotherapeutique - code ATC : N02BE01"). C'est la source
# qui fait foi pour une molecule, la ou RxNav liste toutes les classes qui la
# contiennent sans dire laquelle est la sienne.
CODE_ATC = re.compile(r"code ATC\s*:?\s*([A-Z]\d{2}[A-Z]{2}\d{0,2})")

# Bruit de navigation present dans chaque page.
BRUIT = re.compile(r"(?im)^\s*(redirection vers le haut de page|aller au glossaire|imprimer)\s*$")


def sans_accents(s) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")


def cle(s) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", sans_accents(s).lower())).strip()


# La BDPM nomme le sel effectivement present dans le comprime ("AMOXICILLINE
# TRIHYDRATEE", "BESILATE D'AMLODIPINE", "LOSARTAN POTASSIQUE"), la liste
# marocaine nomme la molecule seule ("AMOXICILLINE"). Retirer ces mots ramene
# les deux ecritures a la meme cle : c'est bien la meme substance active, et
# c'est la meme notice.
MOTS_SELS = {
    "sodique", "potassique", "calcique", "magnesique", "sodium", "potassium",
    "chlorhydrate", "bromhydrate", "sulfate", "besilate", "besylate", "maleate",
    "tartrate", "mesilate", "mesylate", "citrate", "acetate", "fumarate",
    "succinate", "phosphate", "nitrate", "gluconate", "lactate", "oxalate",
    "trihydratee", "trihydrate", "dihydrate", "monohydrate", "hemihydrate",
    "anhydre", "hydrate", "micronise", "micronisee", "base", "de", "d", "du", "l",
}


def cle_base(nom) -> str:
    """Nom de molecule debarrasse de la forme saline et de l'hydratation."""
    mots = [m for m in cle(nom).split() if m not in MOTS_SELS]
    return " ".join(mots)


def variantes(nom) -> list[str]:
    """Ecritures sous lesquelles la meme molecule peut apparaitre.

    Un acide et son sel portent des noms differents ("acide clavulanique" cote
    marocain, "clavulanate de potassium" cote BDPM) : la regle de formation est
    reguliere en francais, on genere donc la forme en -ate."""
    base = cle_base(nom)
    formes = [base]
    mots = base.split()
    if mots and mots[0] == "acide" and len(mots) > 1:
        radical = re.sub(r"(ique|iques)$", "", mots[1])
        formes.append(" ".join([radical + "ate"] + mots[2:]).strip())
    return [f for f in formes if f]


def telecharger_fichier(nom: str) -> Path:
    """Fichier plat BDPM, garde sur disque : il change une fois par mois."""
    chemin = RAW_DIR / nom
    if chemin.exists():
        return chemin
    print(f"Telechargement {nom}...", flush=True)
    reponse = requests.get(f"{BDPM}/download/file/{nom}", headers=ENTETES, timeout=180)
    reponse.raise_for_status()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(reponse.content)
    return chemin


def charger_bdpm() -> tuple[pd.DataFrame, pd.DataFrame]:
    # Fichiers tabules, sans en-tete, encodes en latin-1 (documentation BDPM).
    cis = pd.read_csv(
        telecharger_fichier(FICHIERS["cis"]), sep="\t", header=None, encoding="latin-1",
        names=["cis", "denomination", "forme", "voies", "statut_amm", "type_procedure",
               "etat_commercialisation", "date_amm", "statut_bdm", "numero_europe",
               "titulaire", "surveillance"],
        dtype={"cis": str}, on_bad_lines="skip",
    )
    compo = pd.read_csv(
        telecharger_fichier(FICHIERS["compo"]), sep="\t", header=None, encoding="latin-1",
        names=["cis", "designation", "code_substance", "substance", "dosage",
               "reference_dosage", "nature_composant", "numero_liaison"],
        dtype={"cis": str}, on_bad_lines="skip",
    )
    # SA = substance active ; ST = fraction therapeutique, qui doublonne la SA.
    compo = compo[compo["nature_composant"] == "SA"]
    return cis, compo


def dci_les_plus_repandues(reference: pd.DataFrame, combien: int) -> list[str]:
    """Les molecules qui portent le plus de produits distincts au Maroc : ce
    sont celles qu'un patient a le plus de chances de nommer."""
    compte = reference.groupby("dci")["nom"].nunique().sort_values(ascending=False)
    return compte.head(combien).index.tolist()


def composition_de(actif: str, index_substances: dict) -> str | None:
    """La cle BDPM correspondant a un principe actif marocain, ou None."""
    for forme in variantes(actif):
        if forme in index_substances:
            return forme
    meilleur = process.extractOne(
        cle_base(actif), list(index_substances), scorer=fuzz.WRatio,
        score_cutoff=SEUIL_SUBSTANCE,
    )
    return meilleur[0] if meilleur else None


def choisir_specialites(actifs: list[str], cis: pd.DataFrame, compositions: dict,
                        index_substances: dict, combien: int = 4) -> list[tuple[str, str]]:
    """Une specialite francaise dont la composition est EXACTEMENT celle de la
    DCI marocaine, ni plus ni moins.

    L'egalite stricte est le point important. Se contenter d'exiger que nos
    substances soient presentes faisait choisir ACTRON (paracetamol + aspirine
    + cafeine) pour le paracetamol seul, et AUGMENTIN pour l'amoxicilline
    seule : on aurait affiche au patient les contre-indications de l'aspirine
    sous une boite de Doliprane.
    Plusieurs specialites sont renvoyees, par ordre de pertinence : toutes
    n'ont pas de notice en ligne, et l'appelant essaie la suivante.
    """
    cherchees = set()
    for actif in actifs:
        trouve = composition_de(actif, index_substances)
        if not trouve:
            return []
        cherchees.add(trouve)

    candidats = [c for c, substances in compositions.items() if substances == cherchees]
    lignes = cis[cis["cis"].isin(candidats)].copy()
    if lignes.empty:
        return []
    # Une specialite commercialisee et sous forme orale simple a la notice la
    # plus complete et la plus proche de l'usage courant.
    lignes["_score"] = (
        lignes["etat_commercialisation"].str.contains("Commercialis", na=False).astype(int) * 2
        + lignes["forme"].str.contains("comprim|g[ée]lule|poudre|suspension", case=False, na=False).astype(int)
    )
    lignes = lignes.sort_values("_score", ascending=False).head(combien)
    return list(zip(lignes["cis"], lignes["denomination"]))


def texte_notice(cis_code: str) -> str | None:
    """Notice en texte brut, depuis le cache si elle y est deja."""
    NOTICES_DIR.mkdir(parents=True, exist_ok=True)
    cache = NOTICES_DIR / f"{cis_code}.html"
    if cache.exists():
        html = cache.read_text(encoding="utf-8")
    else:
        try:
            reponse = requests.get(
                f"{BDPM}/affichageDoc.php", params={"specid": cis_code, "typedoc": "N"},
                headers=ENTETES, timeout=60,
            )
        except requests.RequestException:
            return None
        if not reponse.ok:
            return None
        reponse.encoding = "utf-8"
        html = reponse.text
        cache.write_text(html, encoding="utf-8")
        time.sleep(DELAI_S)
    texte = BeautifulSoup(html, "html.parser").get_text("\n")
    texte = BRUIT.sub("", texte)
    return re.sub(r"\n{2,}", "\n", texte)


def extraire_indications(texte: str) -> str | None:
    """Ce a quoi sert le medicament, entre les titres 1 et 2 de la notice.

    Comme pour les autres rubriques, ce sont les DERNIERES occurrences des
    titres qui delimitent le corps : les premieres appartiennent au sommaire,
    ou les deux titres se suivent sans rien entre eux."""
    debuts = [m.end() for m in DEBUT_INDICATIONS.finditer(texte)]
    fins = [m.start() for m in FIN_INDICATIONS.finditer(texte)]
    if not debuts or not fins:
        return None
    # On retient le plus grand debut suivi d'une fin : une notice qui repete
    # ses rubriques par presentation en compte plusieurs paires.
    paires = [(d, f) for d in debuts for f in fins if f > d]
    if not paires:
        return None
    debut, fin = max(paires, key=lambda p: p[0])
    extrait = LIGNE_CLASSE.sub("", texte[debut:fin].strip())
    lignes = [l.strip(" \t·•") for l in extrait.splitlines()]
    extrait = "\n".join(l for l in lignes if l)
    # Un titre seul ne dit rien ; au-dela de 6000 caracteres, le decoupage a
    # rate et a emporte la suite de la notice.
    return extrait if 40 < len(extrait) < 6000 else None


def debut_du_corps(texte: str) -> int | None:
    """Position ou s'ouvrent les contre-indications dans le corps de la notice.

    Le sommaire reprend les memes titres quelques lignes plus haut, et certaines
    notices repetent le tout pour chaque presentation : on retient la premiere
    occurrence suivie d'un vrai contenu."""
    motif_ci, motif_precautions, motif_interactions = (RUBRIQUES[i][1] for i in (0, 1, 2))
    for trouve in re.finditer(motif_ci, texte):
        suite = re.search(motif_precautions, texte[trouve.start():])
        if suite and suite.start() >= ECART_SOMMAIRE:
            return trouve.start()
    # Notice dont le titre de contre-indications n'est pas reconnu : on ouvre
    # sur les precautions, avec la meme garde contre le sommaire.
    for trouve in re.finditer(motif_precautions, texte):
        suite = re.search(motif_interactions, texte[trouve.start():])
        if suite and suite.start() >= ECART_SOMMAIRE:
            return trouve.start()
    return None


def decouper_rubriques(texte: str) -> dict:
    """Le texte de chaque rubrique, de son titre jusqu'au titre suivant.

    On avance dans l'ordre du document a partir du corps de la notice : chaque
    rubrique est la premiere occurrence de son titre apres la precedente."""
    debut = debut_du_corps(texte)
    if debut is None:
        return {nom: None for nom, _ in RUBRIQUES}

    positions, curseur = [], debut
    for nom, motif in RUBRIQUES:
        trouve = re.search(motif, texte[curseur:])
        if not trouve:
            # Rubrique absente ou placee autrement (les notices ne suivent pas
            # toutes le meme ordre) : on la cherche depuis le debut du corps
            # plutot que de l'abandonner. Le tri qui suit remet tout en ordre.
            trouve = re.search(motif, texte[debut:])
            if not trouve:
                continue
            positions.append((debut + trouve.start(), nom))
            continue
        depart = curseur + trouve.start()
        positions.append((depart, nom))
        curseur = depart + 1
    positions.sort()

    fin = re.search(FIN_NOTICE, texte[curseur:])
    borne_finale = curseur + fin.start() if fin else len(texte)

    resultat = {nom: None for nom, _ in RUBRIQUES}
    for i, (depart, nom) in enumerate(positions):
        arrivee = positions[i + 1][0] if i + 1 < len(positions) else borne_finale
        extrait = texte[depart:arrivee].strip()
        # Un titre seul n'apprend rien ; un pave de plus de 12000 caracteres
        # signale un decoupage rate plutot qu'une rubrique.
        if 40 < len(extrait) < 12000:
            resultat[nom] = extrait
    return resultat


def main(combien: int) -> None:
    reference = pd.read_csv(REF_PATH)
    cis, compo = charger_bdpm()
    # Cle normalisee par substance, et composition complete de chaque specialite :
    # c'est cette composition entiere qui doit egaler la DCI cherchee.
    index_substances = {cle_base(s): cle_base(s) for s in compo["substance"]}
    compositions = (
        compo.assign(cle=compo["substance"].map(cle_base))
        .groupby("cis")["cle"].apply(frozenset)
        .apply(set)
        .to_dict()
    )

    dcis = dci_les_plus_repandues(reference, combien)
    print(f"{len(dcis)} molecules a traiter", flush=True)

    lignes, sans_specialite, sans_rubrique = [], [], []
    for i, dci in enumerate(dcis, start=1):
        actifs = [p.strip() for p in str(dci).split(SEPARATEUR_DCI) if p.strip()]
        candidates = choisir_specialites(actifs, cis, compositions, index_substances)
        if not candidates:
            sans_specialite.append(dci)
            continue
        # La premiere specialite n'a pas toujours de notice en ligne : on
        # descend la liste jusqu'a en trouver une exploitable.
        cis_code = denomination = rubriques = code_atc = None
        for code, nom_specialite in candidates:
            texte = texte_notice(code)
            if not texte:
                continue
            atc_trouve = CODE_ATC.search(texte)
            code_atc = atc_trouve.group(1) if atc_trouve else code_atc
            trouvees = decouper_rubriques(texte)
            trouvees["indications"] = extraire_indications(texte)
            if any(trouvees.values()):
                cis_code, denomination, rubriques = code, nom_specialite, trouvees
                break
        if not rubriques:
            sans_rubrique.append(dci)
            continue
        lignes.append({
            "dci": dci,
            "principes_actifs": " // ".join(actifs),
            "nb_produits_maroc": int(reference[reference["dci"] == dci]["nom"].nunique()),
            "cis_bdpm": cis_code,
            "specialite_bdpm": denomination,
            "code_atc_notice": code_atc,
            **rubriques,
            "source_url": f"{BDPM}/affichageDoc.php?specid={cis_code}&typedoc=N",
            "date_recuperation": date.today().isoformat(),
        })
        if i % 25 == 0:
            print(f"  {i}/{len(dcis)}", flush=True)

    table = pd.DataFrame(lignes)
    table.to_csv(OUT_PATH, index=False, encoding="utf-8")

    colonnes = ["indications"] + [nom for nom, _ in RUBRIQUES]
    remplies = {nom: int(table[nom].notna().sum()) for nom in colonnes} if not table.empty else {}
    rapport = [
        "Informations de securite par molecule (source : BDPM / ANSM)",
        f"molecules demandees : {len(dcis)}",
        f"molecules avec au moins une rubrique : {len(table)}",
        f"sans specialite francaise correspondante : {len(sans_specialite)}",
        f"notice trouvee mais aucune rubrique reconnue : {len(sans_rubrique)}",
        "",
        "rubriques remplies :",
        *[f"  {nom} : {n}" for nom, n in remplies.items()],
        "",
        "Le texte est celui de la notice officielle francaise, conserve mot pour mot. "
        "Il decrit la molecule, pas la specialite marocaine : le conditionnement, le "
        "dosage et le titulaire peuvent differer.",
        "",
        "Source : Base de donnees publique des medicaments (ANSM, HAS, UNCAM), "
        "base-donnees-publique.medicaments.gouv.fr -- Licence Ouverte.",
    ]
    if sans_specialite[:10]:
        rapport += ["", "exemples sans correspondance : " + ", ".join(sans_specialite[:10])]
    RAPPORT_PATH.write_text("\n".join(rapport), encoding="utf-8")
    print("\n".join(rapport[:12]))
    print(f"\n-> {OUT_PATH}\n-> {RAPPORT_PATH}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=300, help="nombre de molecules")
    main(parser.parse_args().top)
