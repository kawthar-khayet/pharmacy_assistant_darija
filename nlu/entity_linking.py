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

# WRatio (used for ranking) takes the max over several scorers, one of which is
# partial_ratio -- so a short reference name that happens to be a near-substring
# of a long query scores high on pure noise ("OXISTAT" vs "BIDON INEXISTANTE
# XYZ123" -> 77, i.e. `a_confirmer`, which in a health context means proposing a
# real drug for a query that means nothing). A word-level check has no such
# blind spot, so it is applied as a floor below which nothing is trusted,
# whatever WRatio says. It is compared against the string that actually produced
# the match -- the `nom` for a direct hit, but the `dci` for an indirect one,
# since a DCI match legitimately yields a very different commercial name
# (query "ibuprofene" -> ADFENE).
TOKEN_OVERLAP_FLOOR = 75


def best_token_similarity(query_norm: str, candidate_norm: str) -> float:
    """Best similarity between any single word of the query and any single word
    of the candidate. Used only as a garbage filter (see TOKEN_OVERLAP_FLOOR),
    never for ranking.

    Compared to token_set_ratio it judges each word pair on its own merits, so a
    one-word query still scores full marks against a multi-word reference entry
    ("DOLIPRAN" vs "DOLIPRANE VITAMINE C" -> 94, where token_set_ratio drops to
    57 merely because of the two extra words) while noise stays low
    ("BIDON INEXISTANTE XYZ123" vs "OXISTAT" -> 67)."""
    q_tokens, c_tokens = query_norm.split(), candidate_norm.split()
    return max((fuzz.ratio(a, b) for a in q_tokens for b in c_tokens), default=0.0)


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


def en_enregistrements(df: pd.DataFrame) -> list[dict]:
    """Convertit un DataFrame en liste de dicts JSON-serialisables.

    pandas represente une cellule vide par float('nan'), que `json.dumps` ecrit
    `NaN` -- ce qui n'est pas du JSON valide (RFC 8259) et fait echouer aussi
    bien un `JSON.parse` navigateur que la serialisation d'une reponse FastAPI
    sans `response_model`. On remplace donc les valeurs manquantes par None,
    qui devient un `null` parfaitement legal.
    """
    return df.astype(object).where(pd.notna(df), None).to_dict(orient="records")


class MedicamentMatcher:
    def __init__(self, reference_path: Path = REFERENCE_PATH):
        self.df = pd.read_csv(reference_path, dtype={"code_cnops": str})
        self.df["nom_norm"] = self.df["nom"].apply(normalize)
        self.df["dci_norm"] = self.df["dci"].fillna("").apply(normalize)

        # cle de dosage sans espaces : "500 MG" et "500MG" designent la meme chose
        self.df["dosage_cle"] = self.df["dosage"].fillna("").apply(normalize).str.replace(" ", "", regex=False)
        self.df["famille_forme"] = self.df["forme"].apply(famille_forme)

        self.unique_noms = sorted(self.df["nom_norm"].dropna().unique())
        self.unique_dcis = sorted(d for d in self.df["dci_norm"].dropna().unique() if d)

    def match(self, query: str, dosage: str | None = None, top_k: int = 5) -> list[dict]:
        query_translit = transliterate(query)
        query_norm = normalize(query_translit)
        if not query_norm:
            return []

        nom_hits = process.extract(query_norm, self.unique_noms, scorer=fuzz.WRatio, limit=top_k * 3)
        dci_hits = process.extract(query_norm, self.unique_dcis, scorer=fuzz.WRatio, limit=top_k * 2)

        # nom_norm -> (best score, text that produced it). The matched text is
        # kept so the confidence floor below can be checked against what was
        # actually compared, not against a commercial name the query never
        # resembled in the first place (see TOKEN_OVERLAP_FLOOR).
        candidates: dict[str, tuple[float, str]] = {}

        def offer(name: str, score: float, matched_text: str) -> None:
            if score > candidates.get(name, (0.0, ""))[0]:
                candidates[name] = (score, matched_text)

        for name, score, _ in nom_hits:
            offer(name, score, name)
        for dci_name, score, _ in dci_hits:
            rows = self.df.loc[self.df["dci_norm"] == dci_name, "nom_norm"].unique()
            for name in rows:
                offer(name, score * 0.95, dci_name)  # slight discount: indirect match

        ranked = sorted(candidates.items(), key=lambda kv: kv[1][0], reverse=True)[: top_k * 2]

        results = []
        seen_noms = set()
        for name_norm, (score, matched_text) in ranked:
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
            if best_token_similarity(query_norm, matched_text) < TOKEN_OVERLAP_FLOOR:
                confidence = "non_fiable"

            variants = display_rows[
                ["nom", "dci", "dosage", "forme", "presentation", "ppv",
                 "taux_remboursement_cnops", "taux_remboursement_cnss", "source",
                 "laboratoire", "classe_therapeutique", "statut_commercialisation"]
            ].drop_duplicates().head(5)
            results.append({
                "nom_candidat": rows["nom"].iloc[0],
                "score": round(float(score), 1),
                "confidence": confidence,
                "nb_variantes": len(rows),
                "variantes": en_enregistrements(variants),
            })

            if len(results) >= top_k:
                break

        return results


# Familles de formes galeniques, par voie d'administration. Deux produits de
# meme molecule et meme dosage ne sont proposes comme equivalents que s'ils sont
# de la meme famille : un suppositoire ou une injection ne remplace pas un
# comprime. L'ordre compte ("POUDRE POUR SOLUTION INJECTABLE" est injectable,
# pas une poudre orale).
FAMILLES_FORME = [
    ("injectable", r"INJECT|PERFUSION"),
    ("rectale", r"SUPPOSITOIRE|RECTAL|LAVEMENT"),
    ("vaginale", r"OVULE|VAGINAL"),
    ("ophtalmique", r"COLLYRE|OPHTALM"),
    ("auriculaire", r"AURICUL"),
    ("nasale", r"NASAL"),
    ("inhalee", r"INHAL|AEROSOL"),
    ("cutanee", r"CREME|POMMADE|\bGEL\b|LOTION|CUTANE|TRANSDERM|DERMIQUE"),
    ("orale_liquide", r"BUVABLE|SIROP"),
    ("orale_poudre", r"SACHET|GRANULE|POUDRE"),
    ("orale_solide", r"COMPRIME|GELULE|CAPSULE|DRAGEE|LYOPHILISAT|PASTILLE"),
]


PREFERENCE_FAMILLE = {"orale_solide": 0, "orale_poudre": 1, "orale_liquide": 2}


def famille_forme(forme) -> str:
    if forme is None or (isinstance(forme, float) and forme != forme):
        return ""
    cle = normalize(forme)
    for famille, motif in FAMILLES_FORME:
        if re.search(motif, cle):
            return famille
    # forme inconnue : on n'accepte que la meme forme exacte
    return "autre:" + cle


# Seuls ces produits peuvent etre proposes comme equivalents : un produit
# "Non Commercialise", "Retire" ou "Suspendu" du marche, vendu a l'export ou
# seulement sur appel d'offres hospitalier enverrait le patient chercher en
# officine un medicament introuvable. Une ligne sans statut vient de la liste
# CNSS actuelle des medicaments remboursables : elle est consideree disponible.
STATUTS_EN_OFFICINE = {"Commercialisé"}


def equivalents(matcher: "MedicamentMatcher", nom_candidat: str, dosage: str | None = None,
                limite: int = 6) -> dict | None:
    """Produits de meme composition (DCI identique) et de meme dosage que
    `nom_candidat`, disponibles en officine, du moins cher au plus cher.

    Renvoie None si le produit de reference n'a pas de DCI ou de dosage connus :
    sans eux, on ne peut pas affirmer qu'un autre produit est equivalent.
    """
    df = matcher.df
    lignes = df[df["nom_norm"] == normalize(nom_candidat)]
    if dosage:
        cle = normalize(dosage).replace(" ", "")
        filtrees = lignes[lignes["dosage_cle"].str.contains(re.escape(cle), na=False)]
        if len(filtrees):
            lignes = filtrees
    # Composition fiable uniquement : l'AMMPS ("//") et la CNOPS ("/") donnent
    # la composition complete, alors que la liste CNSS decoupe une association
    # en une ligne par molecule (l'Augmentin y apparait comme "amoxicilline"
    # seule). Comparer sur ces lignes proposerait un produit a une seule
    # molecule a la place d'une association.
    composition_fiable = df["source"].str.contains("ammps|cnops", na=False)
    lignes = lignes[
        (lignes["dci_norm"] != "")
        & (lignes["dosage_cle"] != "")
        & lignes["source"].str.contains("ammps|cnops", na=False)
    ]
    if lignes.empty:
        return None

    # Presentation de reference : d'abord une presentation dont le prix est
    # connu (sans prix, rien a comparer), puis, a prix connu egalement, les
    # formes orales -- sans precision du patient, "Spasfon" designe presque
    # toujours le comprime, pas le suppositoire.
    rang = lignes["famille_forme"].map(PREFERENCE_FAMILLE).fillna(len(PREFERENCE_FAMILLE))
    ref = (
        lignes.assign(_rang=rang, _sans_prix=lignes["ppv"].isna())
        .sort_values(["_sans_prix", "_rang"], kind="stable")
        .iloc[0]
    )

    en_officine = df["statut_commercialisation"].isna() | df["statut_commercialisation"].isin(STATUTS_EN_OFFICINE)
    candidats = df[
        (df["dci_norm"] == ref["dci_norm"])
        & (df["dosage_cle"] == ref["dosage_cle"])
        & (df["nom_norm"] != ref["nom_norm"])
        & (df["famille_forme"] == ref["famille_forme"])
        & df["ppv"].notna()
        & en_officine
        & composition_fiable
    ]
    # un produit peut exister en plusieurs conditionnements : on garde le moins cher
    candidats = candidats.sort_values("ppv").drop_duplicates("nom_norm").head(limite)

    forme_ref = normalize(ref["forme"]) if pd.notna(ref["forme"]) else ""
    return {
        "reference": {
            "nom": ref["nom"],
            "dci": ref["dci"],
            "dosage": ref["dosage"],
            "forme": ref["forme"] if pd.notna(ref["forme"]) else None,
            "ppv": float(ref["ppv"]) if pd.notna(ref["ppv"]) else None,
        },
        "equivalents": [
            {
                "nom": r["nom"],
                "dosage": r["dosage"],
                "forme": r["forme"] if pd.notna(r["forme"]) else None,
                "presentation": r["presentation"] if pd.notna(r["presentation"]) else None,
                "ppv": float(r["ppv"]),
                # meme molecule et meme dosage, mais la forme peut differer
                # (comprime / effervescent...) : on le signale plutot que de la cacher
                "meme_forme": pd.notna(r["forme"]) and normalize(r["forme"]) == forme_ref,
            }
            for r in candidats.to_dict(orient="records")
        ],
    }


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
