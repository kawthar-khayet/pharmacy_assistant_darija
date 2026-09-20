"""Evaluate the pharmacy matcher against real entries from
pharmacies_reference.csv, with typos/partial names injected, plus a few
location-based queries. No API calls -- pure local evaluation.
"""
import sys
from pathlib import Path

from pharmacy_linking import PharmacyMatcher

HERE = Path(__file__).resolve().parent

# (query_nom, query_location, expected_nom, expected_ville, mode)
# mode "exact": top-1 nom must equal expected_nom.
# mode "any": expected_nom must appear somewhere in the returned candidates.
# mode "ambigu": plusieurs officines portent ce nom dans des villes
#   differentes. Reussir, ce n'est pas deviner la bonne -- c'est demander la
#   ville au lieu de trancher en silence.
TEST_CASES = [
    ("Pharmacie Granada", None, None, None, "ambigu"),
    ("Granada", "Nador", "Pharmacie Granada", "Nador", "exact"),
    ("Grenada", "Nador", "Pharmacie Granada", "Nador", "exact"),  # typo
    ("Al Hikma", "Rabat", "Pharmacie Al Hikma", "Rabat", "exact"),
    ("Al Hikmaa", "Rabat", "Pharmacie Al Hikma", "Rabat", "exact"),  # typo
    ("Ibn Nafiss", "Chefchaouen", "Pharmacie Ibn Nafiss", "Chefchaouen", "exact"),
    ("Ibn Nafis", "Chefchaouen", "Pharmacie Ibn Nafiss", "Chefchaouen", "exact"),  # typo
    ("Oumaima", "Guelmim", "Pharmacie Oumaima", "Guelmim", "exact"),
    ("Populaire", "Ksar El Kebir", "Pharmacie Populaire", "Ksar El Kebir", "exact"),
    ("Branes", "Tanger", "Pharmacie Branes", "Tanger", "exact"),
    ("Bidon Inexistante Xyz123", None, None, None, "no_confident_match"),
    # Graphie arabe : ce que donne une demande dictee a la voix, Whisper
    # n'ayant pas de modele de darija. Le nom passe par la translitteration
    # et la cle sonore, la ville par la table d'alias (un toponyme se
    # traduit, il ne se translittere pas).
    ("صيدلية ابن سينا", "الرباط", "Pharmacie Ibn Sina", "Rabat", "exact"),
    ("ابن سينا", "Rabat", "Pharmacie Ibn Sina", "Rabat", "exact"),
    ("الحكمة", "Rabat", "Pharmacie Al Hikma", "Rabat", "exact"),
    ("صيدلية بيدون إينكسيستانت", None, None, None, "no_confident_match"),
]

# (location query, expected city or None if district-level substring match)
LOCATION_ONLY_CASES = [
    "Maarif",
    "Casablanca",
    "Agadir",
    "الدار البيضاء",   # Casablanca, dicte en arabe
    "كازا",            # diminutif courant
    "مراكش",           # Marrakech
]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    matcher = PharmacyMatcher()

    print("=== Cas nom (+ localisation) ===")
    top1_hits = 0
    n_scored = 0
    for nom, loc, expected_nom, expected_ville, mode in TEST_CASES:
        results = matcher.match(nom=nom, location=loc, top_k=3)
        candidates = [(r["nom"], r["ville"]) for r in results]

        if mode == "ambigu":
            note = matcher.last_name_note
            status = "OK " if note else "FAIL"
            print(f"[{status}] {nom!r:30s} loc={loc!r:12s} -> attendu: demander la ville, obtenu={note!r}")
            continue

        if mode == "no_confident_match":
            top_conf = results[0]["confidence"] if results else "aucun"
            ok = not results or top_conf == "non_fiable"
            status = "OK " if ok else "FAIL"
            print(f"[{status}] {nom!r:30s} loc={loc!r:12s} -> attendu: pas de match fiable, obtenu confidence={top_conf!r}")
            continue

        n_scored += 1
        top1 = bool(candidates) and candidates[0] == (expected_nom, expected_ville)
        top1_hits += int(top1)
        status = "OK " if top1 else "FAIL"
        print(f"[{status}] {nom!r:30s} loc={loc!r:12s} -> attendu=({expected_nom!r}, {expected_ville!r}) obtenu={candidates[:1]}")

    print(f"\nTop-1 accuracy (cas nominatifs) : {top1_hits}/{n_scored} = {top1_hits / n_scored:.1%}")

    print("\n=== Cas localisation seule ===")
    for loc in LOCATION_ONLY_CASES:
        results = matcher.match(nom=None, location=loc, top_k=3)
        villes = {r["ville"] for r in results}
        print(f"{loc!r:15s} -> {len(results)} resultats, villes={villes}")


if __name__ == "__main__":
    main()
