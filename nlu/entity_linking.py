"""Entity Linking: resolve a MEDICAMENT entity extracted by the NLU
(often misspelled, incomplete, or in Arabic script) against the
official reference table (data/clean/medicaments_reference.csv).

Pipeline: normalisation -> transliteration darija/arabe -> latin (table
de correspondances pour les cas connus, puis translitteration lettre a
lettre pour le reste) -> fuzzy matching (RapidFuzz) on `nom` and `dci`,
double d'une passe sur la **cle phonetique** pour les graphies que la
comparaison lettre a lettre ne rapproche pas -> ranked candidates with a
confidence tier.

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

from translitteration import cle_phonetique, translitterer

ROOT = Path(__file__).resolve().parent.parent
REFERENCE_PATH = ROOT / "data" / "clean" / "medicaments_reference.csv"

# Correspondances exactes pour les medicaments dont la graphie arabe courante
# s'ecarte trop de leur nom latin pour que la translitteration lettre a lettre
# les rapproche. Elles priment sur la translitteration automatique, qui prend
# le relais pour tout le reste.
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

# La cle phonetique ecrase des distinctions (p/b, s/z, i/e, voyelles longues) :
# deux mots sans rapport s'y ressemblent plus facilement qu'en toutes lettres
# ("BIDON INEXISTANTE" dicte en arabe donne `bidon`, a 80 de `ibido`, la cle
# d'EPIDUO). Le meme garde-fou est donc exige plus haut sur cette passe.
TOKEN_OVERLAP_FLOOR_PHON = 85


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
    """Ramene en latin la part de graphie arabe d'une requete.

    Chaque mot arabe passe d'abord par la table de correspondances ; sinon il
    est translittere lettre a lettre (voir translitteration.py). Les mots deja
    en latin sont laisses intacts : les patients melangent les deux graphies
    dans une meme phrase."""
    if not has_arabic(query):
        return query
    mots = []
    for tok in query.split():
        if tok in ARABIC_TO_LATIN:
            mots.append(ARABIC_TO_LATIN[tok])
        elif has_arabic(tok):
            mots.append(translitterer(tok))
        else:
            mots.append(tok)
    return " ".join(mots)


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

        # Index phonetique : cle sonore -> noms de la base qui la portent.
        # Plusieurs noms peuvent partager une cle (les distinctions p/b, s/z,
        # i/e n'y survivent pas) ; c'est justement ce qui permet de retrouver
        # un nom dicte en arabe, et ce qui impose de ne pas trancher seul
        # quand la cle est ambigue (voir match()).
        self.df["nom_phon"] = self.df["nom_norm"].apply(cle_phonetique)
        self.phon_vers_noms: dict[str, list[str]] = {}
        for phon, nom in zip(self.df["nom_phon"], self.df["nom_norm"]):
            if phon:
                noms = self.phon_vers_noms.setdefault(phon, [])
                if nom not in noms:
                    noms.append(nom)
        self.unique_phons = sorted(self.phon_vers_noms)

    def match(self, query: str, dosage: str | None = None, top_k: int = 5) -> list[dict]:
        query_translit = transliterate(query)
        query_norm = normalize(query_translit)
        if not query_norm:
            return []

        query_phon = cle_phonetique(query_translit)

        nom_hits = process.extract(query_norm, self.unique_noms, scorer=fuzz.WRatio, limit=top_k * 3)
        dci_hits = process.extract(query_norm, self.unique_dcis, scorer=fuzz.WRatio, limit=top_k * 2)
        phon_hits = (
            process.extract(query_phon, self.unique_phons, scorer=fuzz.WRatio, limit=top_k * 2)
            if query_phon else []
        )

        # nom_norm -> (best score, texte compare cote requete, texte compare
        # cote base, passe qui l'a propose). Les deux textes compares sont
        # gardes pour que le garde-fou anti-bruit (TOKEN_OVERLAP_FLOOR) juge la
        # paire qui a reellement produit le score, et non un nom commercial
        # auquel la requete n'a jamais ressemble.
        candidates: dict[str, tuple[float, str, str, str]] = {}

        def offer(name: str, score: float, cote_requete: str, cote_base: str, passe: str) -> None:
            if score > candidates.get(name, (0.0,))[0]:
                candidates[name] = (score, cote_requete, cote_base, passe)

        for name, score, _ in nom_hits:
            offer(name, score, query_norm, name, "nom")
        for dci_name, score, _ in dci_hits:
            rows = self.df.loc[self.df["dci_norm"] == dci_name, "nom_norm"].unique()
            for name in rows:
                offer(name, score * 0.95, query_norm, dci_name, "dci")  # slight discount: indirect match
        for phon, score, _ in phon_hits:
            for name in self.phon_vers_noms[phon]:
                # meme decote qu'un match indirect : passer par la cle sonore
                # fait perdre les distinctions p/b, s/z, i/e
                offer(name, score * 0.95, query_phon, phon, "phon")

        ranked = sorted(candidates.items(), key=lambda kv: kv[1][0], reverse=True)[: top_k * 2]

        results = []
        seen_noms = set()
        for name_norm, (score, cote_requete, cote_base, passe) in ranked:
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
            plancher = TOKEN_OVERLAP_FLOOR_PHON if passe == "phon" else TOKEN_OVERLAP_FLOOR
            if best_token_similarity(cote_requete, cote_base) < plancher:
                confidence = "non_fiable"
            # Un nom retrouve uniquement par sa sonorite, alors que d'autres
            # produits sonnent pareil, ne peut pas etre donne pour acquis : la
            # cle ne sait pas lequel des homophones le patient a dicte.
            if confidence == "auto" and passe == "phon" and len(self.phon_vers_noms.get(cote_base, [])) > 1:
                confidence = "a_confirmer"

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
