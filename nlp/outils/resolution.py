"""Le matcher de medicaments, partage par tout le serveur."""
import re
from functools import lru_cache

from nlp.linking.medicaments import MedicamentMatcher, normalize

# Une ligne presque sans lettres ("1000 MG", "0.25 %") ne peut distinguer
# aucun produit : son nombre de lettres compte plus que de produits les
# contiennent dans leur dosage (verifie en evaluation -- "1000 MG" seul
# matche "ACOL 1000 MG", "ALFAMOX 1000 MG"... a 90 "auto", un faux-positif
# par ligne de boite sur deux).
MIN_LETTRES_LIGNE = 3

# Une ligne qui ne porte QUE du vocabulaire pharmaceutique generique
# ("COMPRIME", "SOLUTION INJECTABLE") n'identifie aucun produit precis :
# presque toute boite de comprimes le dit. Liste de mots exacts plutot que
# des fragments : retirer "INJECT" d'une ligne OCR "INJECTABLE" laisserait
# le residu "ABLE", assez long pour passer a tort le filtre MIN_LETTRES_LIGNE.
MOTS_GENERIQUES = {
    "COMPRIME", "COMPRIMES", "GELULE", "GELULES", "CAPSULE", "CAPSULES",
    "DRAGEE", "DRAGEES", "PASTILLE", "PASTILLES", "SACHET", "SACHETS",
    "GRANULE", "GRANULES", "POUDRE", "SIROP", "SOLUTION", "SUSPENSION",
    "BUVABLE", "INJECTABLE", "PERFUSION", "SUPPOSITOIRE", "OVULE", "COLLYRE",
    "POMMADE", "CREME", "GEL", "LOTION", "AEROSOL", "LYOPHILISAT",
    "BOITE", "FLACON", "TUBE", "AMPOULE", "PLAQUETTE", "BLISTER",
    "VOIE", "ORALE", "ORAL", "USAGE", "EXTERNE", "UI", "MG", "ML", "G",
}


@lru_cache(maxsize=1)
def matcher() -> MedicamentMatcher:
    """La base (~20 000 lignes) n'est chargee qu'une fois par serveur."""
    return MedicamentMatcher()


def reconnaitre_depuis_lignes(lignes: list[str], top_k: int = 5) -> list[dict]:
    """Plusieurs lignes de texte (OCR d'une boite, Challenge #2) -> candidats
    medicaments, classes par score.

    Interroge le matcher une fois PAR LIGNE plutot qu'une fois sur tout le
    texte joint : une boite melange nom, dosage, forme et labo sur des lignes
    separees, et les joindre noie le nom du medicament dans du bruit (une
    requete comme "HEVAZ 600 MG COMPRIME EFAVIRENZ PELLICULE GENPHARMA"
    decroche sur un faux candidat la ou "HEVAZ" seul matche a 100). Un
    candidat vu sur plusieurs lignes garde son meilleur score.

    Seuls les candidats trouves par ressemblance de NOM (passe "nom"/"phon")
    sont gardes : la boite photographiee est UN produit precis, pas "n'importe
    quel produit partageant sa molecule". Sans ce filtre, une ligne qui lit la
    DCI (souvent imprimee sur la boite, ex. "PARACETAMOL") fait apparaitre
    d'autres marques (ex. "PARACETAMOL B.BRAUN") a un score tout aussi haut
    que le produit reellement photographie -- utile pour "cherche-moi du
    paracetamol" au clavier, trompeur ici."""
    candidats: dict[str, dict] = {}
    for ligne in lignes:
        reste = " ".join(w for w in normalize(ligne).split() if w not in MOTS_GENERIQUES)
        if len(re.findall(r"[^\W\d_]", reste, re.UNICODE)) < MIN_LETTRES_LIGNE:
            continue
        for m in matcher().match(ligne, top_k=top_k):
            if m["confidence"] == "non_fiable" or m["passe"] not in ("nom", "phon"):
                continue
            nom = m["nom_candidat"]
            if nom not in candidats or m["score"] > candidats[nom]["score"]:
                candidats[nom] = m
    # le candidat gagnant peut rester loin de 100 (OCR imparfait) ; les
    # suivants ne sont gardes que s'ils restent proches de lui -- sinon ce
    # sont des bribes d'une autre ligne, pas des variantes du bon produit
    classes = sorted(candidats.values(), key=lambda m: m["score"], reverse=True)
    if not classes:
        return []
    plancher = classes[0]["score"] - 10
    return [c for c in classes if c["score"] >= plancher][:top_k]
