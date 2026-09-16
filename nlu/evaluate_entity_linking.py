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
TEST_CASES = [
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
    ("دوليبران", "DOLIPRANE", "exact"),
    ("فلاجيل", "FLAGYL", "exact"),
    ("سميكتا", "SMECTA", "exact"),
    ("سبازفون", "SPASFON", "exact"),
    ("الأموكسيسيلين", "AMOXICILLINE", "contains"),
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    matcher = MedicamentMatcher()

    top1_hits = 0
    top3_hits = 0
    rows = []

    for query, expected, mode in TEST_CASES:
        results = matcher.match(query, top_k=3)
        candidates = [r["nom_candidat"] for r in results]

        def is_match(c: str) -> bool:
            return c == expected if mode == "exact" else expected in c

        top1 = is_match(candidates[0]) if candidates else False
        top3 = any(is_match(c) for c in candidates)
        top1_hits += int(top1)
        top3_hits += int(top3)

        rows.append({
            "query": query,
            "expected": expected,
            "candidates": candidates,
            "top1_correct": top1,
            "top3_correct": top3,
        })
        status = "OK " if top1 else ("~3 " if top3 else "MISS")
        print(f"[{status}] {query!r:25s} -> attendu={expected!r:15s} candidats={candidates}")

    n = len(TEST_CASES)
    print("\n=== Resultats Entity Linking (RapidFuzz) ===")
    print(f"Top-1 accuracy : {top1_hits}/{n} = {top1_hits / n:.1%}")
    print(f"Top-3 accuracy : {top3_hits}/{n} = {top3_hits / n:.1%}")

    out_path = HERE / "entity_linking_eval_results.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nDetail sauvegarde dans : {out_path}")


if __name__ == "__main__":
    main()
