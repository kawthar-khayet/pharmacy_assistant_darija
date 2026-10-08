"""Resolution des medicaments cites : du nom ecrit par le patient aux produits
de la base, une seule fois par message.

Tous les outils qui portent sur un medicament (prix, formes, securite,
conseil) partent de ce resultat au lieu de refaire la recherche.
"""
from dataclasses import dataclass, field
from functools import lru_cache

from nlp.analyse.validation import MedicamentCite
from nlp.linking.medicaments import MedicamentMatcher, normalize


@lru_cache(maxsize=1)
def matcher() -> MedicamentMatcher:
    """La base (~20 000 lignes) n'est chargee qu'une fois par serveur."""
    return MedicamentMatcher()


@dataclass
class MedicamentResolu:
    cite: MedicamentCite                 # tel qu'ecrit par le patient
    statut: str                          # "trouve" | "a_confirmer" | "introuvable"
    nom: str | None = None               # nom officiel retenu
    variantes: list[dict] = field(default_factory=list)   # lignes de la base : dosage, forme, prix...
    autres: list[str] = field(default_factory=list)       # autres noms proches, si a_confirmer


def _filtrer_forme(variantes: list[dict], forme: str | None) -> list[dict]:
    """"sirop doliprane" -> seulement les sirops, s'il en existe ; sinon tout."""
    if not forme:
        return variantes
    cle = normalize(forme)
    gardees = [v for v in variantes if cle in normalize(v.get("forme") or "")]
    return gardees or variantes


def resoudre(cite: MedicamentCite) -> MedicamentResolu:
    # Le matcher renvoie toujours ses meilleurs candidats, meme quand aucun ne
    # ressemble a la requete : un candidat "non_fiable" n'est jamais montre
    # ("qwerty" ne doit pas donner le prix d'un vrai medicament).
    candidats = [
        c for c in matcher().match(cite.nom, dosage=cite.dosage, top_k=3)
        if c["confidence"] != "non_fiable"
    ]
    if not candidats:
        return MedicamentResolu(cite=cite, statut="introuvable")

    meilleur = candidats[0]
    statut = "trouve" if meilleur["confidence"] == "auto" else "a_confirmer"
    return MedicamentResolu(
        cite=cite,
        statut=statut,
        nom=meilleur["nom_candidat"],
        variantes=_filtrer_forme(meilleur["variantes"], cite.forme),
        autres=[c["nom_candidat"] for c in candidats[1:]] if statut == "a_confirmer" else [],
    )


def resoudre_tous(medicaments: list[MedicamentCite]) -> list[MedicamentResolu]:
    return [resoudre(m) for m in medicaments]
