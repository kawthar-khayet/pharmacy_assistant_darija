"""Validation 1 : verifie et corrige l'analyse renvoyee par le LLM.

Le LLM peut se tromper de format ou inventer une valeur. Ici, tout ce qui
n'est pas dans schema.json est ramene vers un cas sur (pas_d_info, preciser,
'inconnu'...), et chaque correction est notee dans `corrections` pour qu'on la
voie pendant les tests. Aucune donnee n'est lue ici : verifier qu'un
medicament existe vraiment est le travail de linking/.
"""
import csv
import re

from pydantic import BaseModel, Field

from nlp.analyse.analyseur import SYMPTOMES_PATH, charger_schema

PATIENTS = {"adulte", "enfant", "bebe", "inconnu"}
GROSSESSE = {"oui", "non", "inconnu"}
URGENCES = {"intoxication", "detresse"}
REGIMES = {"cnops", "cnss", "aucun", "inconnu"}
# Situations qui ne portent aucune demande : si le LLM en met quand meme,
# on les retire (on ne donne pas un prix a quelqu'un en pleine urgence).
SANS_DEMANDE = {"urgence", "medical", "conseil_symptome", "pas_d_info",
                "incompris", "salutation", "hors_sujet"}
_LETTRE_ARABE = re.compile(r"[؀-ۿ]")


class MedicamentCite(BaseModel):
    nom: str                    # tel qu'ecrit par le patient, fautes comprises
    dosage: str | None = None
    forme: str | None = None


class Analyse(BaseModel):
    situation: str
    urgence_type: str | None = None
    demandes: list[str] = Field(default_factory=list)
    medicaments: list[MedicamentCite] = Field(default_factory=list)
    lieu: str | None = None
    pharmacie: str | None = None
    manque: list[str] = Field(default_factory=list)
    symptomes: list[str] = Field(default_factory=list)
    patient: str = "inconnu"
    grossesse: str = "inconnu"
    duree_jours: int | None = None
    regime: str = "inconnu"
    langue: str = "fr"
    comprise: str = ""
    # ajoutees par la validation, jamais par le LLM : pour comprendre pendant
    # les tests pourquoi le bot n'a pas suivi l'analyse telle quelle
    corrections: list[str] = Field(default_factory=list)


def _texte(valeur) -> str | None:
    """Chaine utile, ou None ("", "null", un nombre... ne comptent pas)."""
    if isinstance(valeur, str) and valeur.strip().lower() not in {"", "null", "none"}:
        return valeur.strip()
    return None


def _liste(valeur) -> list:
    return valeur if isinstance(valeur, list) else []


def _symptomes_connus() -> set[str]:
    if not SYMPTOMES_PATH.exists():
        return set()
    with SYMPTOMES_PATH.open(encoding="utf-8-sig", newline="") as f:
        return {(l.get("id") or "").strip() for l in csv.DictReader(f)} - {""}


def _duree(valeur) -> int | None:
    try:
        jours = int(float(valeur))
    except (TypeError, ValueError):
        return None
    return jours if jours >= 0 else None


def valider(brut: dict, message: str) -> Analyse:
    """Transforme la reponse brute du LLM en une Analyse sure et complete.

    `message` (le dernier message du patient) ne sert qu'a deviner la langue
    si le LLM ne l'a pas donnee correctement.
    """
    schema = charger_schema()
    demandes_connues = schema["demandes"]
    corrections: list[str] = []

    situation = brut.get("situation")
    if situation not in schema["situations"]:
        corrections.append(f"situation inconnue {situation!r} -> pas_d_info")
        situation = "pas_d_info"

    medicaments = []
    for m in _liste(brut.get("medicaments")):
        if isinstance(m, str):          # ["doliprane"] au lieu de [{"nom": ...}]
            m = {"nom": m}
        if isinstance(m, dict) and _texte(m.get("nom")):
            medicaments.append(MedicamentCite(
                nom=_texte(m["nom"]), dosage=_texte(m.get("dosage")), forme=_texte(m.get("forme")),
            ))
    lieu = _texte(brut.get("lieu"))
    pharmacie = _texte(brut.get("pharmacie"))

    demandes = []
    for d in _liste(brut.get("demandes")):
        if d not in demandes_connues:
            corrections.append(f"demande inconnue {d!r} retiree")
        elif d not in demandes:
            demandes.append(d)

    if situation in SANS_DEMANDE and demandes:
        corrections.append(f"demandes {demandes} retirees : sans objet pour {situation}")
        demandes = []
    if situation in {"repondre", "preciser"} and not demandes:
        corrections.append(f"{situation} sans demande valide -> pas_d_info")
        situation = "pas_d_info"

    # Ce qui manque se deduit des besoins de chaque demande (schema.json) :
    # on ne se fie pas au champ 'manque' du LLM.
    regime = brut.get("regime")
    regime = regime.strip().lower() if isinstance(regime, str) else regime
    if regime not in REGIMES:
        if regime is not None:
            corrections.append(f"regime {regime!r} -> inconnu")
        regime = "inconnu"

    presents = {"medicament": bool(medicaments), "lieu": bool(lieu), "pharmacie": bool(pharmacie),
                "regime": regime != "inconnu"}
    manque = []
    for d in demandes:
        for besoin in demandes_connues[d]["besoin"]:
            if not presents.get(besoin) and besoin not in manque:
                manque.append(besoin)
    if situation == "repondre" and manque:
        corrections.append(f"repondre -> preciser : manque {manque}")
        situation = "preciser"
    elif situation == "preciser" and not manque:
        corrections.append("preciser alors que rien ne manque -> repondre")
        situation = "repondre"

    urgence_type = brut.get("urgence_type")
    if situation != "urgence":
        urgence_type = None
    elif urgence_type not in URGENCES:
        corrections.append(f"urgence_type {urgence_type!r} -> detresse")
        urgence_type = "detresse"

    symptomes = []
    if situation == "conseil_symptome":
        connus = _symptomes_connus()
        for s in _liste(brut.get("symptomes")):
            if s not in connus and s != "autre":
                corrections.append(f"symptome inconnu {s!r} -> autre")
                s = "autre"
            if s not in symptomes:
                symptomes.append(s)
        if not symptomes:
            symptomes = ["autre"]

    patient = brut.get("patient")
    if patient not in PATIENTS:
        if patient is not None:
            corrections.append(f"patient {patient!r} -> inconnu")
        patient = "inconnu"
    grossesse = brut.get("grossesse")
    if grossesse not in GROSSESSE:
        if grossesse is not None:
            corrections.append(f"grossesse {grossesse!r} -> inconnu")
        grossesse = "inconnu"

    langue = brut.get("langue")
    if langue not in schema["langues"]:
        devinee = "ary_ar" if _LETTRE_ARABE.search(message) else "fr"
        corrections.append(f"langue {langue!r} -> {devinee}")
        langue = devinee

    return Analyse(
        situation=situation,
        urgence_type=urgence_type,
        demandes=demandes,
        medicaments=medicaments,
        lieu=lieu,
        pharmacie=pharmacie,
        manque=manque if situation == "preciser" else [],
        symptomes=symptomes,
        patient=patient,
        grossesse=grossesse,
        duree_jours=_duree(brut.get("duree_jours")),
        regime=regime,
        langue=langue,
        comprise=_texte(brut.get("comprise")) or "",
        corrections=corrections,
    )
