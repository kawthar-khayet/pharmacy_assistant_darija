"""Evaluate the RapidFuzz entity-linking matcher against a small hand-labeled
set of (noisy query -> expected canonical nom) pairs, drawn from the
MEDICAMENT values used in seed_dataset.jsonl (misspellings, Arabic script,
partial names).

No API calls / no cost -- pure local evaluation, safe to run anytime.
"""
import json
import sys
from pathlib import Path

from entity_linking import MedicamentMatcher

HERE = Path(__file__).resolve().parent

# (query as it appears in seed_dataset.jsonl, expected match, match_mode)
# match_mode "exact": candidate must equal expected exactly (real commercial name).
# match_mode "contains": expected has no standalone brand in the reference (it's a
# DCI, e.g. amoxicilline is only sold under brand names like AMOXICILLINE SP,
# AMOXIL...) -- success means the expected substring appears in the candidate.
# match_mode "aucun": la requete ne designe aucun medicament ; reussir, c'est
# n'en donner aucun pour sur (garde-fou anti-bruit). Un `a_confirmer` reste
# acceptable : "Bidon" est a deux lettres de BRIDION, un vrai produit -- le
# proposer sous reserve est honnete, l'affirmer ne le serait pas.
CAS_LATIN = [
    ("doliprane", "DOLIPRANE", "exact"),
    ("dolipran", "DOLIPRANE", "exact"),
    ("dolipran", "DOLIPRANE", "exact"),  # duplicate on purpose: appears twice in seed set
    ("efferalgan", "EFFERALGAN", "exact"),
    ("efferalgant", "EFFERALGAN", "exact"),
    ("amoxicilline", "AMOXICILLINE", "contains"),
    ("amoxiciline", "AMOXICILLINE", "contains"),
    ("ventolin", "VENTOLINE", "exact"),
    ("augmentine", "AUGMENTIN", "contains"),
    ("voltarene", "VOLTARENE", "exact"),
    ("smecta", "SMECTA", "exact"),
    ("aspegik", "ASPEGIC", "exact"),
    ("immodium", "IMODIUM", "exact"),
    ("clamoxyl", "CLAMOXYL", "exact"),
    ("spasfon lyoc", "SPASFON LYOC", "exact"),
    ("spasfon", "SPASFON", "exact"),
    ("flagyl", "FLAGYL", "exact"),
    ("bidon inexistante xyz123", None, "aucun"),
]

# Graphie arabe. C'est la forme que prend une question posee a la voix en
# darija : Whisper n'ayant pas de modele de darija, il la transcrit en arabe.
# Les cinq premieres figuraient dans la table de correspondances ecrite a la
# main ; les suivantes n'y sont pas et ne renvoyaient donc rien avant la
# translitteration lettre a lettre + cle phonetique (translitteration.py).
CAS_ARABE = [
    ("دوليبران", "DOLIPRANE", "exact"),
    ("فلاجيل", "FLAGYL", "exact"),
    ("سميكتا", "SMECTA", "exact"),
    ("سبازفون", "SPASFON", "exact"),
    ("الأموكسيسيلين", "AMOXICILLINE", "contains"),
    ("فولتارين", "VOLTARENE", "exact"),
    ("فنتولين", "VENTOLINE", "exact"),
    ("أوغمنتين", "AUGMENTIN", "contains"),
    ("بانادول", "PANADOL", "exact"),
    ("كلاموكسيل", "CLAMOXYL", "exact"),
    ("إيموديوم", "IMODIUM", "exact"),
    ("أسبيجيك", "ASPEGIC", "exact"),
    ("أوميبرازول", "OMEPRAZOLE", "contains"),
    ("ميتفورمين", "METFORMINE", "contains"),
    ("إيبوبروفين", "IBUPROFENE", "contains"),
    ("الدوليبران", "DOLIPRANE", "exact"),        # avec l'article defini
    ("بغيت دوليبران", "DOLIPRANE", "exact"),      # nom noye dans une phrase
    ("باراسيتامول", "PARACETAMOL", "contains"),   # homophone de PARACETAL
    ("بيدون إينكسيستانت", None, "aucun"),         # bruit dicte en arabe
]

TEST_CASES = CAS_LATIN + CAS_ARABE
GROUPES = {"latin": CAS_LATIN, "arabe": CAS_ARABE}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    matcher = MedicamentMatcher()

    rows = []
    scores = {nom: {"top1": 0, "top3": 0, "n": len(cas)} for nom, cas in GROUPES.items()}

    for groupe, cas in GROUPES.items():
        print(f"\n=== Graphie {groupe} ===")
        for query, expected, mode in cas:
            results = matcher.match(query, top_k=3)
            candidates = [r["nom_candidat"] for r in results]

            if mode == "aucun":
                top1 = top3 = all(r["confidence"] != "auto" for r in results)
                attendu = "rien de sur"
            else:
                def is_match(c: str) -> bool:
                    return c == expected if mode == "exact" else expected in c

                top1 = is_match(candidates[0]) if candidates else False
                top3 = any(is_match(c) for c in candidates)
                attendu = repr(expected)

            scores[groupe]["top1"] += int(top1)
            scores[groupe]["top3"] += int(top3)

            rows.append({
                "groupe": groupe,
                "query": query,
                "expected": expected,
                "mode": mode,
                "candidates": candidates,
                "confidences": [r["confidence"] for r in results],
                "top1_correct": top1,
                "top3_correct": top3,
            })
            status = "OK " if top1 else ("~3 " if top3 else "MISS")
            print(f"[{status}] {query!r:25s} -> attendu={attendu:20s} candidats={candidates}")

    n = len(TEST_CASES)
    top1_hits = sum(s["top1"] for s in scores.values())
    top3_hits = sum(s["top3"] for s in scores.values())
    print("\n=== Resultats Entity Linking (RapidFuzz) ===")
    for nom, s in scores.items():
        print(f"{nom:6s} : top-1 {s['top1']}/{s['n']} = {s['top1'] / s['n']:.1%}"
              f"   top-3 {s['top3']}/{s['n']} = {s['top3'] / s['n']:.1%}")
    print(f"Top-1 accuracy : {top1_hits}/{n} = {top1_hits / n:.1%}")
    print(f"Top-3 accuracy : {top3_hits}/{n} = {top3_hits / n:.1%}")

    out_path = HERE / "entity_linking_eval_results.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nDetail sauvegarde dans : {out_path}")


if __name__ == "__main__":
    main()
