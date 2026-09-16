"""Entity Linking: resolve a MEDICAMENT entity extracted by the NLU
(often misspelled, incomplete, or in Arabic script) against the
official reference table (data/clean/medicaments_reference.csv).

Pipeline: normalisation -> (transliteration darija/arabe -> latin, via
a small seed lookup table) -> fuzzy matching (RapidFuzz) on `nom` and
`dci` -> ranked candidates with a confidence tier.

This is intentionally the "simple first" approach recommended before
trying embeddings/semantic search: normalisation + RapidFuzz.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_PATH = ROOT / "data" / "clean" / "medicaments_reference.csv"

# Seed lookup for common medicaments written in Arabic script by patients.
# Extend this table as new cases are observed in real usage/logs.
ARABIC_TO_LATIN = {
    "دوليبران": "DOLIPRANE",
    "فلاجيل": "FLAGYL",
    "سميكتا": "SMECTA",
    "سبازفون": "SPASFON",
    "الأموكسيسيلين": "AMOXICILLINE",
    "أموكسيسيلين": "AMOXICILLINE",
    "افرالغان": "EFFERALGAN",
    "إفرالغان": "EFFERALGAN",
}

CONFIDENCE_THRESHOLDS = {"auto": 90, "a_confirmer": 70}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def has_arabic(s: str) -> bool:
    return bool(re.search(r"[؀-ۿ]", s))


def normalize(s: str) -> str:
    s = str(s).strip().upper()
    s = strip_accents(s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def transliterate(query: str) -> str:
    """If the query is (partly) in Arabic script, map known words to their
    Latin canonical form via the seed lookup table; unknown Arabic tokens
    are left as-is (they simply won't fuzzy-match anything, which is a
    known limitation -- see nlu/README.md)."""
    if not has_arabic(query):
        return query
    tokens = query.split()
    mapped = [ARABIC_TO_LATIN.get(tok, tok) for tok in tokens]
    return " ".join(mapped)


class MedicamentMatcher:
    def __init__(self, reference_path: Path = REFERENCE_PATH):
        self.df = pd.read_csv(reference_path, dtype={"code_cnops": str})
        self.df["nom_norm"] = self.df["nom"].apply(normalize)
        self.df["dci_norm"] = self.df["dci"].fillna("").apply(normalize)

        self.unique_noms = sorted(self.df["nom_norm"].dropna().unique())
        self.unique_dcis = sorted(d for d in self.df["dci_norm"].dropna().unique() if d)

    def match(self, query: str, dosage: str | None = None, top_k: int = 5) -> list[dict]:
        query_translit = transliterate(query)
        query_norm = normalize(query_translit)
        if not query_norm:
            return []

        nom_hits = process.extract(query_norm, self.unique_noms, scorer=fuzz.WRatio, limit=top_k * 3)
        dci_hits = process.extract(query_norm, self.unique_dcis, scorer=fuzz.WRatio, limit=top_k * 2)

        candidates = {}  # nom_norm -> best score, and whether matched via dci
        for name, score, _ in nom_hits:
            candidates[name] = max(candidates.get(name, 0), score)
        for dci_name, score, _ in dci_hits:
            rows = self.df.loc[self.df["dci_norm"] == dci_name, "nom_norm"].unique()
            for name in rows:
                candidates[name] = max(candidates.get(name, 0), score * 0.95)  # slight discount: indirect match

        ranked = sorted(candidates.items(), key=lambda kv: kv[1], reverse=True)[: top_k * 2]

        results = []
        seen_noms = set()
        for name_norm, score in ranked:
            if name_norm in seen_noms:
                continue
            seen_noms.add(name_norm)
            rows = self.df[self.df["nom_norm"] == name_norm]

            if dosage:
                dosage_norm = normalize(dosage)
                dosage_matches = rows[rows["dosage"].fillna("").apply(normalize).str.contains(re.escape(dosage_norm), na=False)]
                display_rows = dosage_matches if len(dosage_matches) else rows
            else:
                display_rows = rows

            confidence = (
                "auto" if score >= CONFIDENCE_THRESHOLDS["auto"]
                else "a_confirmer" if score >= CONFIDENCE_THRESHOLDS["a_confirmer"]
                else "non_fiable"
            )

            variants = display_rows[
                ["nom", "dci", "dosage", "forme", "presentation", "ppv", "taux_remboursement_cnops", "source"]
            ].drop_duplicates().head(5)
            results.append({
                "nom_candidat": rows["nom"].iloc[0],
                "score": round(float(score), 1),
                "confidence": confidence,
                "nb_variantes": len(rows),
                "variantes": variants.to_dict(orient="records"),
            })

            if len(results) >= top_k:
                break

        return results


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print('Usage: python nlu/entity_linking.py "dolipran" [dosage]')
        sys.exit(1)
    query = sys.argv[1]
    dosage = sys.argv[2] if len(sys.argv) > 2 else None

    matcher = MedicamentMatcher()
    results = matcher.match(query, dosage=dosage)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
