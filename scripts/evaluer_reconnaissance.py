"""Evaluation experimentale du pipeline de reconnaissance (Challenge #2) :
photo -> nlp/vision (pretraitement + OCR) -> nlp.linking.medicaments (matcher).

Fait tourner le pipeline reel (charge EasyOCR, donc lent au premier appel) sur
un dataset avec verite terrain -- celui genere par
scripts/generer_boites_synthetiques.py, ou un dossier de vraies photos
organise de la meme facon (images/ + manifest.csv avec au moins les colonnes
`fichier` et `nom`).

Sortie : un resume (accuracy top-1 / top-5, repartition par niveau de
confiance) imprime dans le terminal, et le detail par image dans
<dataset>/evaluation.csv, pour relire les cas rates.

Usage :
    py scripts/evaluer_reconnaissance.py
    py scripts/evaluer_reconnaissance.py --dataset data/vision/photos_reelles
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nlp.linking.medicaments import normalize  # noqa: E402
from nlp.outils.resolution import reconnaitre_depuis_lignes  # noqa: E402
from nlp.vision.ocr import extraire_texte  # noqa: E402
from nlp.vision.pretraitement import ErreurImage, pretraiter  # noqa: E402

DATASET_DEFAUT = ROOT / "data" / "vision" / "synthetique"


def evaluer_une_image(chemin: Path, top_k: int) -> dict:
    debut = time.time()
    try:
        image = pretraiter(chemin.read_bytes())
    except ErreurImage as e:
        return {"texte_detecte": "", "resultats": [], "erreur": str(e), "duree_s": time.time() - debut}

    ocr = extraire_texte(image)
    if not ocr["textes"]:
        return {"texte_detecte": "", "resultats": [], "erreur": "aucun texte detecte",
                "duree_s": time.time() - debut}

    # meme logique que POST /reconnaissance : une ligne a la fois (voir
    # nlp/outils/resolution.py)
    resultats = reconnaitre_depuis_lignes(ocr["textes"], top_k=top_k)
    return {"texte_detecte": " ".join(ocr["textes"]), "resultats": resultats,
            "erreur": None, "duree_s": time.time() - debut}


def main(dataset: Path, top_k: int) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    manifest = pd.read_csv(dataset / "manifest.csv", dtype=str)

    lignes = []
    for _, reference in manifest.iterrows():
        chemin = dataset / "images" / reference["fichier"]
        sortie = evaluer_une_image(chemin, top_k)

        candidats = [normalize(r["nom_candidat"]) for r in sortie["resultats"]]
        verite = normalize(reference["nom"])
        top1 = bool(candidats) and candidats[0] == verite
        topk = verite in candidats
        confiance = sortie["resultats"][0]["confidence"] if sortie["resultats"] else None

        lignes.append({
            "fichier": reference["fichier"], "attendu": reference["nom"],
            "predit": sortie["resultats"][0]["nom_candidat"] if sortie["resultats"] else None,
            "top1_correct": top1, "top5_correct": topk, "confidence": confiance,
            "texte_ocr": sortie["texte_detecte"], "erreur": sortie["erreur"],
            "duree_s": round(sortie["duree_s"], 2),
        })

    resultats = pd.DataFrame(lignes)
    resultats.to_csv(dataset / "evaluation.csv", index=False)

    total = len(resultats)
    top1 = resultats["top1_correct"].sum()
    top5 = resultats["top5_correct"].sum()
    sans_texte = (resultats["erreur"] == "aucun texte detecte").sum()

    print(f"{total} images evaluees ({dataset})")
    print(f"accuracy top-1 : {top1}/{total} ({100 * top1 / total:.1f}%)")
    print(f"accuracy top-{top_k} : {top5}/{total} ({100 * top5 / total:.1f}%)")
    print(f"aucun texte detecte : {sans_texte}/{total}")
    print(resultats["confidence"].value_counts(dropna=False).to_string())
    print(f"duree moyenne par image : {resultats['duree_s'].mean():.2f} s")
    print(f"detail -> {dataset / 'evaluation.csv'}")


if __name__ == "__main__":
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--dataset", type=Path, default=DATASET_DEFAUT)
    analyseur.add_argument("--top-k", type=int, default=5)
    arguments = analyseur.parse_args()
    main(arguments.dataset, arguments.top_k)
