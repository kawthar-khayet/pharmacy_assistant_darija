"""Clean CNOPS and AMMPS medication data and merge into one reference table
for the pharmacy-assistant chatbot (Challenge #1).

Inputs:
  - ref-des-medicaments-cnops-2014.xlsx   (CNOPS, 2014, reimbursement focus)
  - data/raw/ammps_medicaments.csv         (AMMPS, current, national registry)

Output:
  - data/clean/medicaments_ammps.csv       (cleaned AMMPS, one row per product/presentation)
  - data/clean/medicaments_cnops.csv       (cleaned CNOPS)
  - data/clean/medicaments_reference.csv   (merged reference table)
  - data/clean/merge_report.txt            (data-quality / match summary)
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CNOPS_PATH = ROOT / "ref-des-medicaments-cnops-2014.xlsx"
AMMPS_PATH = ROOT / "data" / "raw" / "ammps_medicaments.csv"
CLEAN_DIR = ROOT / "data" / "clean"


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_text(s) -> str:
    if pd.isna(s):
        return ""
    s = str(s).strip().upper()
    s = strip_accents(s)
    s = re.sub(r"\s+", " ", s)
    return s


def norm_key_token(s) -> str:
    """Aggressive normalization for join keys: no spaces/punctuation."""
    s = norm_text(s)
    s = s.replace(",", ".")
    s = re.sub(r"[^A-Z0-9.]", "", s)
    return s


def parse_ammps_price(val):
    if pd.isna(val):
        return None
    s = str(val).replace("DH", "").strip()
    if not s or s.upper().startswith("SANS") or s == "-":
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif s.count(".") > 1:
        parts = s.split(".")
        s = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(s)
    except ValueError:
        return None


STATUT_MAP = {
    "suspendu du marché": "Suspendu du Marché",
    "suspendu du Marché": "Suspendu du Marché",
    "commercialisé ao": "Commercialisé AO",
}


def clean_statut(s):
    s = str(s).strip()
    low = s.lower()
    return STATUT_MAP.get(low, s)


PPGN_MAP = {
    "VACCIN": "VACCIN",
    "GN-HYBRIDE": "GN-HYBRIDE",
    "GN-Hybride".upper(): "GN-HYBRIDE",
}


def clean_ammps(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    text_cols = ["nom", "dosage", "forme", "substance_active", "classe_therapeutique",
                 "epi_laboratoire", "presentation"]
    for c in text_cols:
        df[c] = df[c].apply(lambda x: norm_text(x) if pd.notna(x) else pd.NA)

    df["statut_commercialisation"] = df["statut_commercialisation"].apply(clean_statut)
    df["statut_amm"] = df["statut_amm"].str.strip()
    df["pp_gn"] = df["pp_gn"].apply(lambda x: norm_text(x) if pd.notna(x) and str(x).strip() not in ("-", "") else pd.NA)

    for c in ["ppv", "ph", "pfht"]:
        df[c] = df[c].apply(parse_ammps_price)

    df["tva"] = df["tva"].astype(str).str.replace("%", "", regex=False).str.strip()
    df["tva"] = pd.to_numeric(df["tva"], errors="coerce")

    df["lien_rcp_naf"] = df["lien_rcp_naf"].replace({"-": pd.NA})

    df = df.drop(columns=["source_page"])
    df = df.drop_duplicates()

    df["join_key"] = (
        df["nom"].apply(norm_key_token) + "|" +
        df["dosage"].apply(norm_key_token) + "|" +
        df["forme"].apply(norm_key_token)
    )

    return df


def clean_cnops(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["CODE"] = df["CODE"].astype(str)
    for c in ["NOM", "DCI1", "FORME", "PRESENTATION"]:
        df[c] = df[c].apply(norm_text)
    df["DOSAGE1"] = df["DOSAGE1"].astype(str).where(df["DOSAGE1"].notna(), "")
    df["UNITE_DOSAGE1"] = df["UNITE_DOSAGE1"].apply(lambda x: norm_text(x) if pd.notna(x) else "")
    df["dosage_text"] = (df["DOSAGE1"].str.strip() + " " + df["UNITE_DOSAGE1"].str.strip()).str.strip()

    df["TAUX_REMBOURSEMENT"] = (
        df["TAUX_REMBOURSEMENT"].astype(str).str.replace("%", "", regex=False).str.strip()
    )
    df["TAUX_REMBOURSEMENT"] = pd.to_numeric(df["TAUX_REMBOURSEMENT"], errors="coerce")

    df["PRINCEPS_GENERIQUE"] = df["PRINCEPS_GENERIQUE"].map({"P": "PRINCEPS", "G": "GENERIQUE"})

    df = df.drop_duplicates()

    df["join_key"] = (
        df["NOM"].apply(norm_key_token) + "|" +
        df["dosage_text"].apply(norm_key_token) + "|" +
        df["FORME"].apply(norm_key_token)
    )

    return df


def build_reference(ammps: pd.DataFrame, cnops: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    merged = ammps.merge(
        cnops[["join_key", "CODE", "PRIX_BR", "TAUX_REMBOURSEMENT", "PRINCEPS_GENERIQUE", "DCI1"]],
        on="join_key", how="outer", suffixes=("", "_cnops"), indicator=True,
    )

    # rows that came only from cnops won't have ammps text fields; backfill from cnops columns
    only_cnops = merged["_merge"] == "right_only"
    cnops_only_rows = cnops[cnops["join_key"].isin(merged.loc[only_cnops, "join_key"])]

    result = pd.DataFrame()
    result["nom"] = merged["nom"]
    result["dci"] = merged["substance_active"]
    result["dosage"] = merged["dosage"]
    result["forme"] = merged["forme"]
    result["presentation"] = merged["presentation"]
    result["laboratoire"] = merged["epi_laboratoire"]
    result["classe_therapeutique"] = merged["classe_therapeutique"]
    result["type_produit"] = merged["pp_gn"]
    result["statut_commercialisation"] = merged["statut_commercialisation"]
    result["statut_amm"] = merged["statut_amm"]
    result["ppv"] = merged["ppv"]
    result["ph"] = merged["ph"]
    result["pfht"] = merged["pfht"]
    result["tva"] = merged["tva"]
    result["code_cnops"] = merged["CODE"]
    result["prix_base_remboursement_cnops"] = merged["PRIX_BR"]
    result["taux_remboursement_cnops"] = merged["TAUX_REMBOURSEMENT"]

    # Backfill AMMPS-missing text fields from CNOPS for rows only present in CNOPS
    cnops_indexed = cnops.set_index("join_key")
    right_only_keys = merged.loc[only_cnops, "join_key"]
    for key, ridx in zip(right_only_keys, merged.loc[only_cnops].index):
        row = cnops_indexed.loc[key]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        result.at[ridx, "nom"] = row["NOM"]
        result.at[ridx, "dci"] = row["DCI1"]
        result.at[ridx, "dosage"] = row["dosage_text"]
        result.at[ridx, "forme"] = row["FORME"]
        result.at[ridx, "presentation"] = row["PRESENTATION"]
        result.at[ridx, "type_produit"] = row["PRINCEPS_GENERIQUE"]

    result["source"] = merged["_merge"].map({
        "left_only": "ammps",
        "right_only": "cnops",
        "both": "ammps+cnops",
    })

    result = result.sort_values(["nom", "dosage"]).reset_index(drop=True)

    stats = {
        "ammps_rows": len(ammps),
        "cnops_rows": len(cnops),
        "matched_both": int((merged["_merge"] == "both").sum()),
        "ammps_only": int((merged["_merge"] == "left_only").sum()),
        "cnops_only": int((merged["_merge"] == "right_only").sum()),
        "reference_rows": len(result),
    }
    return result, stats


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    ammps_raw = pd.read_csv(AMMPS_PATH)
    cnops_raw = pd.read_excel(CNOPS_PATH)

    ammps = clean_ammps(ammps_raw)
    cnops = clean_cnops(cnops_raw)

    ammps.to_csv(CLEAN_DIR / "medicaments_ammps.csv", index=False, encoding="utf-8-sig")
    cnops.to_csv(CLEAN_DIR / "medicaments_cnops.csv", index=False, encoding="utf-8-sig")

    reference, stats = build_reference(ammps, cnops)
    reference.to_csv(CLEAN_DIR / "medicaments_reference.csv", index=False, encoding="utf-8-sig")

    report_lines = [
        "=== Rapport de fusion CNOPS + AMMPS ===",
        f"AMMPS (source) lignes nettoyees : {stats['ammps_rows']}",
        f"CNOPS (source) lignes nettoyees : {stats['cnops_rows']}",
        f"Correspondances exactes (nom+dosage+forme) : {stats['matched_both']}",
        f"AMMPS uniquement (pas de correspondance CNOPS) : {stats['ammps_only']}",
        f"CNOPS uniquement (pas de correspondance AMMPS) : {stats['cnops_only']}",
        f"Total table de reference : {stats['reference_rows']}",
        "",
        f"Taux de correspondance CNOPS->AMMPS : {stats['matched_both'] / stats['cnops_rows']:.1%}",
    ]
    report = "\n".join(report_lines)
    (CLEAN_DIR / "merge_report.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
