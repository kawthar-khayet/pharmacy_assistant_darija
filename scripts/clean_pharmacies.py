"""Clean the scraped Saydalia pharmacies directory for the chatbot's
info_pharmacie intent.

Input:  data/raw/saydalia_pharmacies.csv  (2661 raw records, deduped by id)
Output: data/clean/pharmacies_reference.csv
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "data" / "raw" / "saydalia_pharmacies.csv"
CLEAN_DIR = ROOT / "data" / "clean"


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_text(s) -> str:
    if pd.isna(s):
        return ""
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    return s.strip(" ,-")


def classify_type(title: str) -> str:
    t = strip_accents(title).strip().lower()
    if t.startswith("pharmacie") or t.startswith("la pharmacie") or t.startswith("grande pharmacie"):
        return "pharmacie"
    if "parapharm" in t or "para pharm" in t:
        return "parapharmacie"
    if "laborato" in t:
        return "laboratoire"
    return "autre_point_de_vente"


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RAW_PATH, dtype={"phone": str, "id": str})

    df["nom"] = df["title"].apply(norm_text)
    df["telephone"] = df["phone"].str.strip()
    df["adresse"] = df["address"].apply(norm_text)
    df["ville"] = df["ville"].apply(norm_text).str.title()
    df["garde"] = df["garde"].apply(lambda x: norm_text(x) if pd.notna(x) else pd.NA)
    df["type_etablissement"] = df["title"].apply(classify_type)

    result = df[["id", "nom", "type_etablissement", "telephone", "adresse", "ville", "garde"]].copy()

    before = len(result)
    result = result.drop_duplicates(subset=["nom", "adresse"])
    result = result.drop_duplicates(subset=["telephone"], keep="first")
    after = len(result)

    result = result.sort_values(["ville", "nom"]).reset_index(drop=True)
    result.to_csv(CLEAN_DIR / "pharmacies_reference.csv", index=False, encoding="utf-8-sig")

    report = [
        "=== Rapport de nettoyage pharmacies (source: saydalia.ma) ===",
        f"Lignes brutes                : {before}",
        f"Doublons supprimes (nom+adresse ou telephone) : {before - after}",
        f"Total table de reference     : {after}",
        "",
        "Repartition par type :",
        result["type_etablissement"].value_counts().to_string(),
        "",
        "Top 10 villes :",
        result["ville"].value_counts().head(10).to_string(),
    ]
    report_text = "\n".join(report)
    (CLEAN_DIR / "pharmacies_report.txt").write_text(report_text, encoding="utf-8")
    print(report_text)


if __name__ == "__main__":
    main()
