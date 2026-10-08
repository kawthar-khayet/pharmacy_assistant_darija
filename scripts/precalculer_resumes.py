"""Pre-calcule les resumes de securite, langue par langue.

Entree : data/clean/securite_medicaments.csv
Sortie : data/clean/securite_resumes.json (le cache que lit api/resume.py)
         data/clean/securite_explications.json avec --explications (reponses du chat)

Pourquoi un script separe : le palier gratuit de Gemini limite le nombre
d'appels par minute. Genere a la volee pendant une conversation, un resume
manquant tombe sur ce quota et n'arrive jamais. Genere ici, a froid et avec une
pause entre chaque molecule, il est deja en cache quand un patient pose sa
question -- et il n'est paye qu'une fois.

Le script est reprenable : ce qui est en cache n'est pas redemande.

Usage :
    py scripts/precalculer_resumes.py                    # darija latine
    py scripts/precalculer_resumes.py --langues ary_lat,ary_ar,fr
    py scripts/precalculer_resumes.py --pause 6          # quota plus serre
    py scripts/precalculer_resumes.py --explications --langues ary_lat,ary_ar,ar,fr
"""
import argparse
import sys
import time
from pathlib import Path

import pandas as pd

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from api import donnees, resume  # noqa: E402

SECURITE_PATH = RACINE / "data" / "clean" / "securite_medicaments.csv"
# 4 secondes entre deux appels : sous la limite par minute du palier gratuit,
# avec de la marge.
PAUSE_S = 4.0


def main(langues: list[str], pause: float, explications: bool = False) -> None:
    table = pd.read_csv(SECURITE_PATH)
    dcis = table["dci"].dropna().tolist()
    print(f"{len(dcis)} molecules x {len(langues)} langue(s)", flush=True)

    faits = ignores = echecs = 0
    for langue in langues:
        for i, dci in enumerate(dcis, start=1):
            chemin = resume.EXPLICATIONS_PATH if explications else resume.CACHE_PATH
            if f"{dci}|{langue}" in resume._charger_cache(chemin):
                ignores += 1
                continue
            fiche = donnees.securite(dci)
            if not fiche:
                continue
            produit = resume.expliquer(fiche, langue) if explications else resume.resumer(fiche, langue)
            if produit:
                faits += 1
            else:
                echecs += 1
            time.sleep(pause)
            if i % 20 == 0:
                print(f"  {langue} {i}/{len(dcis)} — {faits} ecrits, {echecs} sans resume",
                      flush=True)

    print(f"\n{faits} resumes ecrits, {ignores} deja en cache, {echecs} sans resume")
    print(f"-> {resume.EXPLICATIONS_PATH if explications else resume.CACHE_PATH}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--langues", default="ary_lat")
    parser.add_argument("--pause", type=float, default=PAUSE_S)
    parser.add_argument("--explications", action="store_true",
                        help="explications simples par rubrique (reponses du chat)")
    arguments = parser.parse_args()
    main([l.strip() for l in arguments.langues.split(",") if l.strip()], arguments.pause,
         arguments.explications)
