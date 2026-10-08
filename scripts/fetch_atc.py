"""Associe un code ATC (classification therapeutique de l'OMS) a chaque DCI.

Entree : data/clean/medicaments_reference.csv (colonne `dci`)
Sorties :
  - data/clean/dci_atc.csv          (dci, principe_actif, rxcui, code_atc, libelle_atc)
  - data/clean/dci_atc_report.txt   (couverture)

Pourquoi l'ATC : la colonne `classe_therapeutique` de l'annuaire AMMPS n'est
remplie que pour 73 % des lignes et compte 273 libelles maison, du tres large
("INFECTIOLOGIE-PARASITOLOGIE") au tres precis ("ANTIPSYCHOTIQUE"). L'ATC est
un standard hierarchique : meme code chez tout le monde, et un niveau de detail
choisi (J01CA = penicillines a spectre large).

Pourquoi RxNav plutot que l'index ATC de l'OMS : l'index officiel n'est pas
librement redistribuable. RxNav (NIH, API publique sans cle) expose la meme
classification, interrogeable par nom de molecule.

Deux appels par principe actif :
  1. approximateTerm : trouve l'identifiant RxNorm meme quand le nom est en
     francais ("AMOXICILLINE" -> Amoxicillin, "ACIDE CLAVULANIQUE" -> 21216).
  2. rxclass/byRxcui : les classes ATC rattachees a cet identifiant.

Une DCI composee ("AMOXICILLINE // ACIDE CLAVULANIQUE") est decoupee : chaque
principe actif a sa propre ligne, et donc son propre code.

Plusieurs codes ATC par molecule est la regle, pas l'exception : l'ibuprofene
est M01AE par voie orale et M02AA en gel. Toutes les lignes sont conservees --
en garder une seule au hasard afficherait "anti-inflammatoire topique" pour un
comprime.

Usage : py scripts/fetch_atc.py   (~10 min la premiere fois, puis cache)
"""
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
REF_PATH = ROOT / "data" / "clean" / "medicaments_reference.csv"
OUT_PATH = ROOT / "data" / "clean" / "dci_atc.csv"
RAPPORT_PATH = ROOT / "data" / "clean" / "dci_atc_report.txt"
CACHE_PATH = ROOT / "data" / "raw" / "rxnav_cache.json"

BASE = "https://rxnav.nlm.nih.gov/REST"
ENTETES = {"User-Agent": "DwaTalk/0.1 (projet etudiant, assistant pharmacie Maroc)"}
# RxNav demande de rester sous 20 requetes par seconde : on en fait 5.
DELAI_S = 0.2

# Separateurs des DCI composees. La table de reference en utilise deux, selon
# la source d'origine : "AMOXICILLINE // ACIDE CLAVULANIQUE" (AMMPS) et
# "PERINDOPRIL / INDAPAMIDE" (CNSS), 299 DCI dans le second cas.
SEPARATEURS = re.compile(r"\s*//\s*|\s*/\s*")
# Une DCI qui contient des chiffres ou des parentheses n'est pas une simple
# association : ce sont des libelles de solutes ou de vaccins ou le "/" fait
# partie d'une unite ("103 MMOL / L DE SODIUM"). Les decouper produirait des
# fragments qui ne designent aucune molecule.
NE_PAS_DECOUPER = re.compile(r"[\d()]")
# Score minimal d'appariement approximatif. En dessous, RxNav propose un nom
# qui ne ressemble plus a la molecule demandee.
SCORE_MIN = 8.0


def appel(chemin: str, params: dict) -> dict:
    try:
        r = requests.get(f"{BASE}/{chemin}", params=params, headers=ENTETES, timeout=30)
        return r.json() if r.ok else {}
    except (requests.RequestException, ValueError):
        return {}


def rxcui_de(nom: str) -> str | None:
    # Recherche exacte d'abord (le nom normalise suffit pour la plupart des
    # molecules) : l'appariement approximatif notait "PARACETAMOL" 7,3, sous le
    # seuil, et le laissait donc sans classe alors que RxNorm le connait.
    exact = appel("rxcui.json", {"name": nom, "search": 2})
    identifiants = exact.get("idGroup", {}).get("rxnormId")
    if identifiants:
        return identifiants[0]

    donnees = appel("approximateTerm.json", {"term": nom, "maxEntries": 1, "option": 1})
    candidats = donnees.get("approximateGroup", {}).get("candidate", [])
    if not candidats:
        return None
    meilleur = candidats[0]
    if float(meilleur.get("score", 0)) < SCORE_MIN:
        return None
    return meilleur.get("rxcui")


def classes_atc(rxcui: str) -> list[dict]:
    donnees = appel(
        "rxclass/class/byRxcui.json", {"rxcui": rxcui, "relaSource": "ATC"}
    )
    items = donnees.get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
    vues, classes = set(), []
    for item in items:
        concept = item.get("rxclassMinConceptItem", {})
        code, libelle = concept.get("classId"), concept.get("className")
        if code and code not in vues:
            vues.add(code)
            classes.append({"code_atc": code, "libelle_atc": libelle})
    return classes


def principes_actifs(dci: str) -> list[str]:
    texte = str(dci).strip()
    if NE_PAS_DECOUPER.search(texte):
        return [texte] if texte else []
    return [p.strip() for p in SEPARATEURS.split(texte) if p.strip()]


def main() -> None:
    reference = pd.read_csv(REF_PATH)
    dcis = sorted(reference["dci"].dropna().unique())
    actifs = sorted({p for d in dcis for p in principes_actifs(d)})
    print(f"{len(dcis)} DCI, {len(actifs)} principes actifs distincts", flush=True)

    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    for i, actif in enumerate(actifs, start=1):
        # Une molecule sans identifiant en cache est reessayee : une coupure
        # reseau passagere avait fait enregistrer le paracetamol comme
        # introuvable, alors que RxNav le connait parfaitement. Seuls les
        # succes sont donc definitifs.
        if actif in cache and cache[actif].get("rxcui"):
            continue
        rxcui = rxcui_de(actif)
        time.sleep(DELAI_S)
        classes = classes_atc(rxcui) if rxcui else []
        if rxcui:
            time.sleep(DELAI_S)
        cache[actif] = {"rxcui": rxcui, "classes": classes}
        if i % 100 == 0:
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"  {i}/{len(actifs)}", flush=True)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    lignes = []
    for dci in dcis:
        for actif in principes_actifs(dci):
            trouve = cache.get(actif, {})
            classes = trouve.get("classes") or [{"code_atc": None, "libelle_atc": None}]
            for classe in classes:
                lignes.append({
                    "dci": dci,
                    "principe_actif": actif,
                    "rxcui": trouve.get("rxcui"),
                    # RxNav rattache une molecule a sa propre classe ET aux
                    # classes d'associations qui la contiennent, sans dire
                    # laquelle est la sienne. Toutes sont donc conservees, sans
                    # en elire une : le code officiel d'une molecule se lit
                    # dans sa notice (colonne `code_atc_notice` de
                    # securite_medicaments.csv), pas par deduction.
                    "code_atc": classe["code_atc"],
                    # Le premier caractere du code ATC est le groupe anatomique
                    # (J = anti-infectieux, N = systeme nerveux...) : utile pour
                    # regrouper sans descendre dans le detail.
                    "groupe_atc": classe["code_atc"][0] if classe["code_atc"] else None,
                    "libelle_atc": classe["libelle_atc"],
                })
    table = pd.DataFrame(lignes)
    table.to_csv(OUT_PATH, index=False, encoding="utf-8")

    avec_code = table[table["code_atc"].notna()]
    dci_couvertes = avec_code["dci"].nunique()
    actifs_couverts = avec_code["principe_actif"].nunique()
    rapport = [
        "Couverture ATC",
        f"DCI : {dci_couvertes}/{len(dcis)} ({dci_couvertes / len(dcis) * 100:.1f} %)",
        f"principes actifs : {actifs_couverts}/{len(actifs)} "
        f"({actifs_couverts / len(actifs) * 100:.1f} %)",
        f"lignes ecrites : {len(table)}",
        f"codes ATC distincts : {avec_code['code_atc'].nunique()}",
        "",
        "Les libelles ATC sont en anglais (source RxNav / OMS) : les traduire "
        "demande une passe a part, revue a la main.",
        "",
        "Source : RxNav / RxClass (National Library of Medicine), classification ATC de l'OMS.",
    ]
    RAPPORT_PATH.write_text("\n".join(rapport), encoding="utf-8")
    print("\n".join(rapport[:5]))
    print(f"\n-> {OUT_PATH}\n-> {RAPPORT_PATH}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
