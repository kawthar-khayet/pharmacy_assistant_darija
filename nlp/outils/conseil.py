"""Conseil symptomes : la liste blanche data/clean/conseil_symptomes.csv, ecrite
a la main (a faire relire par un pharmacien), devient les fiches "conseil" du
RAG (nlp/rag/fiches.py). Une molecule n'y figure que si elle est commercialisee
au Maroc sous une forme non injectable. On ne cite pas de marque : le
pharmacien choisit le produit.
"""
from nlp.linking.medicaments import STATUTS_EN_OFFICINE
from nlp.outils.resolution import matcher


def commercialisee(dci: str) -> bool:
    """La molecule existe-t-elle en officine au Maroc, sous une forme non
    injectable, avec une DCI EXACTEMENT egale a une des ecritures donnees
    ("CETIRIZINE (DICHLORHYDRATE)|CETIRIZINE") ?"""
    ecritures = {e.strip().upper() for e in dci.split("|") if e.strip()}
    df = matcher().df
    lignes = df[df["dci"].fillna("").str.upper().isin(ecritures)]
    en_officine = (lignes["statut_commercialisation"].isna()
                   | lignes["statut_commercialisation"].isin(STATUTS_EN_OFFICINE))
    return bool((en_officine & (lignes["famille_forme"] != "injectable")).any())
