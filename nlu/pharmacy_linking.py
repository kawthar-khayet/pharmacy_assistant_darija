"""Entity Linking for pharmacies: resolve PHARMACIE / LOCALISATION entities
extracted by the NLU against the pharmacies directory
(data/clean/pharmacies_reference.csv, scraped from saydalia.ma).

Same "normalisation + RapidFuzz" approach as entity_linking.py for
medicaments, adapted to two search axes:
  - by name (PHARMACIE entity, e.g. "Ibn Sina", "Al Amal")
  - by location (LOCALISATION entity, e.g. "Maarif", "Agadir") -- matched
    against both the city field (`ville`) and, since most Moroccan
    neighborhoods aren't captured at city granularity, a substring search
    inside the free-text `adresse` field.
The two can be combined: a location filters the candidate pool first
(more accurate, avoids cross-city name collisions like multiple
"Pharmacie Centrale"), then the name is fuzzy-matched within it.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_PATH = ROOT / "data" / "clean" / "pharmacies_reference.csv"

CONFIDENCE_THRESHOLDS = {"auto": 90, "a_confirmer": 70}

# Common leading words that don't help discriminate between pharmacy names
# (almost all entries start with one of these) -- stripped before matching.
NAME_PREFIXES = re.compile(
    r"^(LA |GRANDE |NOUVELLE )*PHARMACIE\s+(DE\s+|DU\s+|DES\s+|D')?",
    re.IGNORECASE,
)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalize(s) -> str:
    if pd.isna(s):
        return ""
    s = str(s).strip().upper()
    s = strip_accents(s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_pharmacie_prefix(name_norm: str) -> str:
    return NAME_PREFIXES.sub("", name_norm).strip()


class PharmacyMatcher:
    def __init__(self, reference_path: Path = REFERENCE_PATH):
        self.df = pd.read_csv(reference_path, dtype={"id": str, "telephone": str})
        self.df["nom_norm"] = self.df["nom"].apply(normalize)
        self.df["nom_court"] = self.df["nom_norm"].apply(strip_pharmacie_prefix)
        self.df["ville_norm"] = self.df["ville"].apply(normalize)
        self.df["adresse_norm"] = self.df["adresse"].apply(normalize)

        self.unique_villes = sorted(v for v in self.df["ville_norm"].dropna().unique() if v)
        self.last_location_note: str | None = None

    def _filter_by_location(self, location: str) -> tuple[pd.DataFrame | None, str | None]:
        """Returns (matching rows or None, ambiguity_note or None).

        None for the rows means the location can't be confidently resolved
        -- callers must NOT silently fall back to the unfiltered national
        list in that case (a user who names a place we don't recognise
        should be told so, not handed pharmacies from random other cities).

        The note is set whenever we DID resolve to a dominant city but the
        same name also matched other, less frequent cities -- so a caller
        who actually meant one of those doesn't get silently overridden
        without any indication that a choice was made on their behalf."""
        loc_norm = normalize(location)
        if not loc_norm:
            return None, None

        # exact/near city match first
        city_hits = process.extract(loc_norm, self.unique_villes, scorer=fuzz.WRatio, limit=1)
        if city_hits and city_hits[0][1] >= 90:
            return self.df[self.df["ville_norm"] == city_hits[0][0]], None

        # fall back to substring search in the free-text address (districts,
        # neighborhoods -- not captured at city granularity). Only trust it
        # if one city clearly dominates the hits. A flat percentage isn't a
        # good test here: some neighborhood names are real districts that
        # legitimately exist in several cities (e.g. "Agdal" is a real
        # district in Rabat, Marrakech, Meknes AND Oujda -- Rabat is only
        # ~53% of those hits but is still clearly the right answer, being
        # 4-5x more frequent than any other single city), while others are
        # a coincidental substring with no real dominant city at all (e.g.
        # "Al Irfane" hits three unrelated cities once each). So we compare
        # the top city's count against the runner-up's instead of an
        # absolute share: a clear leader (>=2x the second place) is trusted,
        # a close spread is treated as unresolved rather than guessed at.
        in_address = self.df["adresse_norm"].str.contains(re.escape(loc_norm), na=False)
        matches = self.df[in_address]
        if not matches.empty:
            city_counts = matches["ville_norm"].value_counts()
            top_count = city_counts.iloc[0]
            second_count = city_counts.iloc[1] if len(city_counts) > 1 else 0
            if len(city_counts) == 1 or top_count >= 2 * max(second_count, 1):
                dominant_city = city_counts.index[0]
                dominant_rows = matches[matches["ville_norm"] == dominant_city]

                note = None
                other_cities = city_counts.index[1:]
                if len(other_cities) > 0:
                    dominant_display = dominant_rows["ville"].iloc[0]
                    others_display = sorted({
                        self.df.loc[self.df["ville_norm"] == c, "ville"].iloc[0] for c in other_cities
                    })
                    note = (
                        f"'{location}' existe aussi a : {', '.join(others_display)}. "
                        f"Resultats ci-dessous pour {dominant_display} (le plus frequent) -- "
                        f"precise la ville si ce n'est pas la bonne."
                    )
                return dominant_rows, note

        return None, None

    def match(self, nom: str | None = None, location: str | None = None, top_k: int = 5) -> list[dict]:
        self.last_location_note = None
        if location:
            pool, note = self._filter_by_location(location)
            self.last_location_note = note
            if pool is None or pool.empty:
                if nom:
                    pool = self.df  # degrade gracefully: search the name nationally
                else:
                    return []  # honest: we don't recognise this place, nothing to list
        else:
            pool = self.df

        if not nom:
            # location-only query: just return entries in that pool (e.g. sorted
            # to prioritise on-duty "garde" pharmacies first)
            pool = pool.copy()
            pool["_garde_first"] = pool["garde"].notna()
            pool = pool.sort_values("_garde_first", ascending=False)
            return [
                {
                    "nom": r["nom"], "telephone": r["telephone"], "adresse": r["adresse"],
                    "ville": r["ville"], "garde": r["garde"] if pd.notna(r["garde"]) else None,
                    "score": None, "confidence": "liste_localisation",
                }
                for r in pool.head(top_k).to_dict(orient="records")
            ]

        query_norm = normalize(nom)
        query_court = strip_pharmacie_prefix(query_norm)

        choices = pool["nom_court"].tolist()
        if not choices:
            return []
        hits = process.extract(query_court, choices, scorer=fuzz.WRatio, limit=top_k)

        results = []
        seen = set()
        for matched_text, score, idx in hits:
            row = pool.iloc[idx]
            key = (row["nom"], row["adresse"])
            if key in seen:
                continue
            seen.add(key)

            confidence = (
                "auto" if score >= CONFIDENCE_THRESHOLDS["auto"]
                else "a_confirmer" if score >= CONFIDENCE_THRESHOLDS["a_confirmer"]
                else "non_fiable"
            )
            results.append({
                "nom": row["nom"],
                "telephone": row["telephone"],
                "adresse": row["adresse"],
                "ville": row["ville"],
                "garde": row["garde"] if pd.notna(row["garde"]) else None,
                "score": round(float(score), 1),
                "confidence": confidence,
            })
        return results


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print('Usage: python nlu/pharmacy_linking.py "<nom pharmacie>" ["<localisation>"]')
        print('       python nlu/pharmacy_linking.py "" "<localisation>"   # liste par lieu')
        sys.exit(1)
    nom = sys.argv[1] or None
    location = sys.argv[2] if len(sys.argv) > 2 else None

    matcher = PharmacyMatcher()
    results = matcher.match(nom=nom, location=location)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
