"""Clean CNOPS, AMMPS and CNSS medication data and merge into one reference
table for the pharmacy-assistant chatbot (Challenge #1).

Inputs:
  - ref-des-medicaments-cnops-2014.xlsx   (CNOPS, 2014, reimbursement focus)
  - data/raw/ammps_medicaments.csv         (AMMPS, current, national registry)
  - data/raw/cnss_medicaments.csv          (CNSS, current reimbursable list)

Output:
  - data/clean/medicaments_ammps.csv       (cleaned AMMPS, one row per product/presentation)
  - data/clean/medicaments_cnops.csv       (cleaned CNOPS)
  - data/clean/medicaments_cnss.csv        (cleaned CNSS)
  - data/clean/medicaments_reference.csv   (merged reference table)
  - data/clean/merge_report.txt            (data-quality / match summary)

CNSS is merged differently from CNOPS on purpose. CNOPS is joined with a plain
outer merge, which multiplies rows whenever the same nom+dosage+forme key is
duplicated on both sides (a real, pre-existing effect: 219 keys are duplicated
in both AMMPS and CNOPS, so the merge emits their cartesian product). Joining a
third source the same way would compound that explosion, so CNSS is attached in
two steps instead: its reimbursement metadata is folded onto existing rows via a
one-row-per-key lookup (which cannot multiply anything), and only its genuinely
new products are appended as fresh rows.
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CNOPS_PATH = ROOT / "ref-des-medicaments-cnops-2014.xlsx"
AMMPS_PATH = ROOT / "data" / "raw" / "ammps_medicaments.csv"
CNSS_PATH = ROOT / "data" / "raw" / "cnss_medicaments.csv"
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


def clean_cnss(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the CNSS reimbursable-medication list.

    Same shape as CNOPS (dosage and its unit in separate columns, one row per
    presentation), so it is normalised the same way and gets the same join key.

    One caveat is carried through deliberately: the source column labelled
    "Princeps / Générique" holds the codes A/N/C/B, not P/G, and those codes do
    NOT encode princeps-vs-generique. Cross-tabulating them against the products
    CNSS shares with the other two sources shows no relationship at all -- code
    "A" covers 1010 products CNOPS calls GENERIQUE and 969 it calls PRINCEPS,
    and AMMPS agrees no better. The CNSS site itself displays the bare letter
    with no legend. So the value is kept verbatim under a name that does not
    claim a meaning (`princeps_generique_code`) and is never fed into the
    reference table's `type_produit`, which stays sourced from AMMPS/CNOPS.
    """
    df = df.copy()
    df["code"] = df["code"].astype(str)

    for c in ["nom", "dci", "forme", "presentation", "laboratoire", "classe_therapeutique"]:
        df[c] = df[c].apply(norm_text)

    df["unite_dosage"] = df["unite_dosage"].apply(lambda x: norm_text(x) if pd.notna(x) else "")
    df["dosage"] = df["dosage"].astype(str).where(df["dosage"].notna(), "")
    df["dosage_text"] = (df["dosage"].str.strip() + " " + df["unite_dosage"].str.strip()).str.strip()

    for c in ["ppv", "ph", "ppv_br"]:
        df[c] = df[c].apply(parse_ammps_price)

    df["taux_remboursement_cnss"] = (
        df["taux_remboursement_cnss"].astype(str).str.replace("%", "", regex=False).str.strip()
    )
    df["taux_remboursement_cnss"] = pd.to_numeric(df["taux_remboursement_cnss"], errors="coerce")

    df = df.rename(columns={"princeps_generique": "princeps_generique_code"})

    df = df.drop_duplicates()

    df["join_key"] = (
        df["nom"].apply(norm_key_token) + "|" +
        df["dosage_text"].apply(norm_key_token) + "|" +
        df["forme"].apply(norm_key_token)
    )

    return df


def cnss_metadata_by_key(cnss: pd.DataFrame) -> pd.DataFrame:
    """Collapse CNSS to exactly one row per join key, so it can be attached to
    the AMMPS/CNOPS table without ever multiplying rows.

    `taux` is safe to collapse: it is already single-valued for 99% of keys
    (6523/6591), and the 68 disagreeing keys take the max, i.e. the rate the
    patient is most likely to benefit from.

    `ppv_br` is not safe to collapse the same way -- it is a per-presentation
    amount and genuinely differs across presentations of the same product for
    1305 keys. Picking one arbitrarily would attach a reimbursement base to a
    box size it does not belong to, so it is only carried when the key has a
    single unambiguous value, and left empty otherwise. The full per-presentation
    detail always remains in medicaments_cnss.csv.
    """
    grouped = cnss.groupby("join_key")

    meta = pd.DataFrame({
        "code_cnss": grouped["code"].first(),
        "taux_remboursement_cnss": grouped["taux_remboursement_cnss"].max(),
    })

    br_nunique = grouped["ppv_br"].nunique()
    br_value = grouped["ppv_br"].max()
    meta["prix_base_remboursement_cnss"] = br_value.where(br_nunique == 1)

    return meta.reset_index()


def build_reference(ammps: pd.DataFrame, cnops: pd.DataFrame, cnss: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
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

    # .map over the categorical `_merge` indicator returns a Categorical, which
    # cannot be concatenated with "+cnss" below -- keep it as plain strings.
    result["source"] = merged["_merge"].map({
        "left_only": "ammps",
        "right_only": "cnops",
        "both": "ammps+cnops",
    }).astype(str)

    # --- CNSS, step 1: fold its reimbursement data onto the rows already built.
    # A one-row-per-key lookup, so this join can only add columns, never rows.
    result["join_key"] = merged["join_key"].values
    cnss_meta = cnss_metadata_by_key(cnss)
    before = len(result)
    result = result.merge(cnss_meta, on="join_key", how="left")
    assert len(result) == before, "l'attachement CNSS ne doit jamais creer de lignes"

    matched_cnss = result["code_cnss"].notna()
    result.loc[matched_cnss, "source"] = result.loc[matched_cnss, "source"] + "+cnss"

    # --- CNSS, step 2: append the products CNSS has and the others don't.
    # Every presentation is kept here (unlike the collapsed lookup above), since
    # for these rows CNSS is the only description of the product available.
    known_keys = set(result["join_key"])
    cnss_new = cnss[~cnss["join_key"].isin(known_keys)].copy()

    appended = pd.DataFrame({
        "nom": cnss_new["nom"],
        "dci": cnss_new["dci"],
        "dosage": cnss_new["dosage_text"],
        "forme": cnss_new["forme"],
        "presentation": cnss_new["presentation"],
        "laboratoire": cnss_new["laboratoire"],
        "classe_therapeutique": cnss_new["classe_therapeutique"],
        "ppv": cnss_new["ppv"],
        "ph": cnss_new["ph"],
        "code_cnss": cnss_new["code"],
        "prix_base_remboursement_cnss": cnss_new["ppv_br"],
        "taux_remboursement_cnss": cnss_new["taux_remboursement_cnss"],
        "source": "cnss",
        "join_key": cnss_new["join_key"],
    })

    result = pd.concat([result, appended], ignore_index=True)
    result = result.drop(columns=["join_key"])
    result = result.sort_values(["nom", "dosage"]).reset_index(drop=True)

    stats = {
        "ammps_rows": len(ammps),
        "cnops_rows": len(cnops),
        "cnss_rows": len(cnss),
        "matched_both": int((merged["_merge"] == "both").sum()),
        "ammps_only": int((merged["_merge"] == "left_only").sum()),
        "cnops_only": int((merged["_merge"] == "right_only").sum()),
        "cnss_keys": int(cnss["join_key"].nunique()),
        "cnss_keys_matched": int(cnss_meta["join_key"].isin(known_keys).sum()),
        "cnss_rows_appended": len(appended),
        "reference_rows": len(result),
    }
    return result, stats


def main():
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    ammps_raw = pd.read_csv(AMMPS_PATH)
    cnops_raw = pd.read_excel(CNOPS_PATH)
    cnss_raw = pd.read_csv(CNSS_PATH, dtype=str, encoding="utf-8-sig")

    ammps = clean_ammps(ammps_raw)
    cnops = clean_cnops(cnops_raw)
    cnss = clean_cnss(cnss_raw)

    ammps.to_csv(CLEAN_DIR / "medicaments_ammps.csv", index=False, encoding="utf-8-sig")
    cnops.to_csv(CLEAN_DIR / "medicaments_cnops.csv", index=False, encoding="utf-8-sig")
    cnss.to_csv(CLEAN_DIR / "medicaments_cnss.csv", index=False, encoding="utf-8-sig")

    reference, stats = build_reference(ammps, cnops, cnss)
    reference.to_csv(CLEAN_DIR / "medicaments_reference.csv", index=False, encoding="utf-8-sig")

    report_lines = [
        "=== Rapport de fusion CNOPS + AMMPS + CNSS ===",
        f"AMMPS (source) lignes nettoyees : {stats['ammps_rows']}",
        f"CNOPS (source) lignes nettoyees : {stats['cnops_rows']}",
        f"CNSS  (source) lignes nettoyees : {stats['cnss_rows']}",
        "",
        "-- Fusion AMMPS <-> CNOPS (merge outer sur nom+dosage+forme) --",
        f"Correspondances exactes (nom+dosage+forme) : {stats['matched_both']}",
        f"AMMPS uniquement (pas de correspondance CNOPS) : {stats['ammps_only']}",
        f"CNOPS uniquement (pas de correspondance AMMPS) : {stats['cnops_only']}",
        f"Taux de correspondance CNOPS->AMMPS : {stats['matched_both'] / stats['cnops_rows']:.1%}",
        "",
        "-- Apport CNSS (rattachement par cle, puis ajout des produits inedits) --",
        f"Cles produit distinctes cote CNSS : {stats['cnss_keys']}",
        f"  dont deja presentes (remboursement CNSS ajoute a la ligne existante) : {stats['cnss_keys_matched']}",
        f"  dont inedites (lignes ajoutees a la reference) : {stats['cnss_rows_appended']}",
        f"Taux de correspondance CNSS->AMMPS/CNOPS : {stats['cnss_keys_matched'] / stats['cnss_keys']:.1%}",
        "",
        f"Total table de reference : {stats['reference_rows']}",
    ]
    report = "\n".join(report_lines)
    (CLEAN_DIR / "merge_report.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
