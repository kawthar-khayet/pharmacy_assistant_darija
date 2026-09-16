"""API for the pharmacy-assistant chatbot (Challenge #1).

Wires the pieces built so far into one service:
  NLU (intent + entities, LLM few-shot on Ollama Cloud)
    -> Entity Linking medicaments (RapidFuzz vs medicaments_reference.csv)
    -> Entity Linking pharmacies (RapidFuzz vs pharmacies_reference.csv)
    -> one structured JSON response + a natural-language `reply`

Multi-turn: when the patient asks about a medicament without saying where
they are, the bot asks for a city/neighborhood (in-memory session state,
keyed by `session_id`) instead of answering with an empty pharmacy list.
The follow-up turn (just the city) is treated as the answer to that
question rather than a fresh, unrelated message.

`reply` is built from templates, not a second LLM call -- keeps latency
and cost down. Swap in an LLM call later for more natural phrasing if
needed; the data plumbing (session state, matches) stays the same.

Run locally:  uvicorn api.main:app --reload --port 8000
Docs UI:      http://localhost:8000/docs
"""
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

NLU_DIR = Path(__file__).resolve().parent.parent / "nlu"
sys.path.insert(0, str(NLU_DIR))

from llm_prototype import run as run_nlu, load_schema  # noqa: E402
from entity_linking import MedicamentMatcher  # noqa: E402
from pharmacy_linking import PharmacyMatcher  # noqa: E402

app = FastAPI(
    title="Assistant Pharmacie API",
    description="NLU (intent + entites) + Entity Linking medicaments/pharmacies pour le Challenge #1",
    version="0.2.0",
)

_schema = load_schema()
_med_matcher: MedicamentMatcher | None = None
_pharma_matcher: PharmacyMatcher | None = None

# In-memory conversation state: session_id -> pending context.
# Fine for a single-process dev/demo server; a real deployment would move
# this to a shared store (Redis, DB) so it survives restarts / scales
# across workers.
SESSIONS: dict[str, dict] = {}

STOCK_RELATED_INTENTS = {"disponibilite_medicament", "commande_reservation"}


def get_med_matcher() -> MedicamentMatcher:
    global _med_matcher
    if _med_matcher is None:
        _med_matcher = MedicamentMatcher()
    return _med_matcher


def get_pharma_matcher() -> PharmacyMatcher:
    global _pharma_matcher
    if _pharma_matcher is None:
        _pharma_matcher = PharmacyMatcher()
    return _pharma_matcher


class ChatRequest(BaseModel):
    text: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    input: str
    reply: str
    intent: str | None = None
    entities: list[dict] = []
    medicament_matches: list[dict] = []
    pharmacie_matches: list[dict] = []
    validation_errors: list[str] = []
    awaiting_localisation: bool = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schema")
def schema():
    """Expose the intent/entite taxonomy the NLU was built against."""
    return _schema


def has_value(x) -> bool:
    """True for real values; False for None/NaN (pandas emits float('nan') for
    missing numeric cells, which is truthy in plain Python -- `if x:` alone
    would treat a missing price as present)."""
    return x is not None and not (isinstance(x, float) and x != x)


def describe_medicament(match: dict) -> str:
    variants = match["variantes"]
    variant = variants[0] if variants else {}
    # the first variant may lack a price even if another one has it (e.g.
    # different packagings of the same product) -- prefer a priced one.
    priced_variant = next((v for v in variants if has_value(v.get("ppv"))), variant)

    parts = [match["nom_candidat"]]
    if has_value(variant.get("dosage")):
        parts.append(f"({variant['dosage']}, {str(variant.get('forme', '')).lower()})")
    desc = " ".join(parts)

    price_bits = []
    if has_value(priced_variant.get("ppv")):
        price_bits.append(f"{priced_variant['ppv']} DH")
    taux = priced_variant.get("taux_remboursement_cnops")
    if not has_value(taux):
        taux = variant.get("taux_remboursement_cnops")
    if has_value(taux):
        price_bits.append(f"rembourse a {taux:.0f}%")
    if price_bits:
        desc += " -- " + ", ".join(price_bits)
    return desc


def describe_pharmacies(pharmacies: list[dict]) -> str:
    lines = []
    for p in pharmacies:
        garde = f" (garde: {p['garde']})" if p.get("garde") else ""
        lines.append(f"  - {p['nom']}, {p['telephone']}, {p['adresse']}{garde}")
    return "\n".join(lines)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Le champ 'text' est vide.")

    session_id = req.session_id or str(uuid.uuid4())
    pending = SESSIONS.get(session_id)

    # --- Turn that answers a pending "which city?" question ---
    if pending and pending.get("awaiting") == "localisation":
        location = text
        # if the reply is a fuller sentence, try to pull a LOCALISATION entity
        # out of it via the NLU; fall back to the raw text otherwise.
        try:
            nlu_result = run_nlu(text)
            loc_entity = next(
                (e for e in nlu_result["output"].get("entities", []) if e["type"] == "LOCALISATION"), None
            )
            if loc_entity:
                location = loc_entity["value"]
        except SystemExit:
            pass  # no API key etc: just use the raw text as the location

        pharma_matcher = get_pharma_matcher()
        pharma_matches = pharma_matcher.match(nom=None, location=location, top_k=3)
        location_note = pharma_matcher.last_location_note
        med_desc = pending["med_desc"]

        if pharma_matches:
            reply = (
                f"{med_desc}\nVoici des pharmacies pres de {location} a contacter "
                f"pour confirmer la disponibilite (pas de suivi de stock en temps reel) :\n"
                + describe_pharmacies(pharma_matches)
            )
            if location_note:
                reply += f"\n\n({location_note})"
        else:
            reply = f"{med_desc}\nJe n'ai pas trouve de pharmacie repertoriee pres de {location}."

        del SESSIONS[session_id]
        return ChatResponse(
            session_id=session_id, input=text, reply=reply,
            pharmacie_matches=pharma_matches,
        )

    # --- Fresh turn ---
    try:
        nlu_result = run_nlu(text)
    except SystemExit as e:
        raise HTTPException(status_code=500, detail=str(e))

    output = nlu_result["output"]
    intent = output.get("intent", "autre")
    entities = output.get("entities", [])

    medicament_matches: list[dict] = []
    pharmacie_matches: list[dict] = []

    med_entity = next((e for e in entities if e["type"] == "MEDICAMENT"), None)
    dosage_entity = next((e for e in entities if e["type"] == "DOSAGE"), None)
    if med_entity:
        medicament_matches = get_med_matcher().match(
            med_entity["value"], dosage=dosage_entity["value"] if dosage_entity else None, top_k=3,
        )

    pharm_entity = next((e for e in entities if e["type"] == "PHARMACIE"), None)
    loc_entity = next((e for e in entities if e["type"] == "LOCALISATION"), None)
    location_note = None
    if pharm_entity or loc_entity:
        pharma_matcher = get_pharma_matcher()
        pharmacie_matches = pharma_matcher.match(
            nom=pharm_entity["value"] if pharm_entity else None,
            location=loc_entity["value"] if loc_entity else None,
            top_k=3,
        )
        location_note = pharma_matcher.last_location_note

    awaiting_localisation = False

    if intent in STOCK_RELATED_INTENTS and medicament_matches:
        med_desc = describe_medicament(medicament_matches[0])
        if loc_entity:
            if pharmacie_matches:
                reply = (
                    f"{med_desc}\nVoici des pharmacies pres de {loc_entity['value']} a contacter "
                    f"pour confirmer la disponibilite (pas de suivi de stock en temps reel) :\n"
                    + describe_pharmacies(pharmacie_matches)
                )
                if location_note:
                    reply += f"\n\n({location_note})"
            else:
                reply = f"{med_desc}\nJe n'ai pas trouve de pharmacie repertoriee pres de {loc_entity['value']}."
        else:
            reply = f"{med_desc}\nDans quelle ville ou quel quartier es-tu, pour que je te propose des pharmacies a contacter ?"
            SESSIONS[session_id] = {"awaiting": "localisation", "med_desc": med_desc}
            awaiting_localisation = True

    elif intent == "prix_remboursement" and medicament_matches:
        reply = describe_medicament(medicament_matches[0])

    elif intent == "info_pharmacie":
        if pharmacie_matches:
            reply = "Voici ce que j'ai trouve :\n" + describe_pharmacies(pharmacie_matches)
            if location_note:
                reply += f"\n\n({location_note})"
        else:
            reply = "Precise le nom de la pharmacie ou ta ville/quartier pour que je puisse chercher."

    elif intent == "posologie_information":
        reply = (
            "Je n'ai pas d'information de posologie fiable dans ma base actuelle -- "
            "merci de te referer a la notice ou de demander a un pharmacien."
        )

    elif intent == "salutation":
        reply = "Bonjour ! Je peux t'aider a trouver un medicament ou une pharmacie, pose ta question."

    else:
        reply = "Je n'ai pas bien compris ta demande -- peux-tu reformuler ?"

    return ChatResponse(
        session_id=session_id,
        input=text,
        reply=reply,
        intent=intent,
        entities=entities,
        medicament_matches=medicament_matches,
        pharmacie_matches=pharmacie_matches,
        validation_errors=nlu_result["validation_errors"],
        awaiting_localisation=awaiting_localisation,
    )
