"""Outil medicament : formes et dosages d'un medicament commercialise au Maroc.

Reutilise le tri de prix.py (produits en officine, sources AMMPS / CNOPS / CNSS
reunies) mais ne renvoie ni prix ni remboursement : seulement ce qui existe.
"""
from nlp.linking.medicaments import normalize
from nlp.outils.prix import lignes_du_produit, presentations
from nlp.outils.resolution import MedicamentResolu

# Au-dela, la liste devient illisible dans un chat.
MAX_DOSAGES = 6


def formes_dosages(resolu: MedicamentResolu) -> dict:
    """Dosages et formes existants, et si la forme demandee existe.

    statut : "trouve" | "a_confirmer" | "introuvable" | "plus_commercialise".
    """
    if resolu.statut == "introuvable":
        return {"statut": "introuvable", "cite": resolu.cite.nom}

    trouvees = presentations(lignes_du_produit(resolu, filtrer_forme=False))
    if not trouvees:
        return {"statut": "plus_commercialise", "nom": resolu.nom}

    par_dosage: dict[str, list[str]] = {}
    for p in trouvees:
        formes = par_dosage.setdefault(p["dosage"] or "", [])
        if p["forme"] and p["forme"] not in formes:
            formes.append(p["forme"])

    forme_existe = None
    if resolu.cite.forme:
        cle = normalize(resolu.cite.forme)
        forme_existe = any(cle in normalize(p["forme"] or "") for p in trouvees)

    return {
        "statut": resolu.statut,
        "nom": resolu.nom,
        "autres": resolu.autres,
        "par_dosage": [
            {"dosage": dosage or None, "formes": formes}
            for dosage, formes in list(par_dosage.items())[:MAX_DOSAGES]
        ],
        "liste_coupee": len(par_dosage) > MAX_DOSAGES,
        "forme_demandee": resolu.cite.forme,
        "forme_existe": forme_existe,     # None si le patient n'a pas demande de forme
    }
