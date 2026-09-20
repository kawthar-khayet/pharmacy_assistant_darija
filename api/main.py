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

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

NLU_DIR = Path(__file__).resolve().parent.parent / "nlu"
sys.path.insert(0, str(NLU_DIR))

from llm_prototype import run as run_nlu, load_schema  # noqa: E402
from entity_linking import MedicamentMatcher, equivalents  # noqa: E402
from pharmacy_linking import PharmacyMatcher  # noqa: E402

from api.parole import ErreurAudio, transcrire  # noqa: E402

app = FastAPI(
    title="Assistant Pharmacie API",
    description="NLU (intent + entites) + Entity Linking medicaments/pharmacies pour le Challenge #1",
    version="0.2.0",
)

# The React dev server runs on its own origin, so the browser blocks its calls
# to this API unless they are explicitly allowed. Listed one by one rather than
# with "*": the endpoints are unauthenticated, so there is no reason to let any
# site on the web drive them. Add the deployed front's origin here when there
# is one.
FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_schema = load_schema()
_med_matcher: MedicamentMatcher | None = None
_pharma_matcher: PharmacyMatcher | None = None

# In-memory conversation state: session_id -> pending context.
# Fine for a single-process dev/demo server; a real deployment would move
# this to a shared store (Redis, DB) so it survives restarts / scales
# across workers.
SESSIONS: dict[str, dict] = {}

INTENTS_CONNUS = {i["id"] for i in load_schema()["intents"]}

# Anciennes intentions (taxonomie v1) qu'un modele pourrait encore produire par
# habitude : on les rabat sur leur equivalent v2 plutot que de les ignorer.
INTENTS_V1 = {"autre": "hors_sujet", "commande_reservation": "disponibilite_medicament"}

# Numeros verifies sur la page d'urgence de l'ambassade de France au Maroc
# (ma.diplomatie.gouv.fr/fr/urgence) : SAMU 141, Protection civile 15, Centre
# antipoison et de pharmacovigilance 0801 000 180.
MESSAGE_CONSEIL_MEDICAL = (
    "Je ne peux pas donner d'avis medical ni conseiller un traitement a partir de "
    "symptomes. Parle a un pharmacien ou a un medecin : eux pourront t'examiner et "
    "te conseiller.\n\n"
    "En cas d'urgence : SAMU 141 - Protection civile 15.\n"
    "Intoxication ou surdosage de medicament : Centre antipoison 0801 000 180."
)

MESSAGE_HORS_SUJET = (
    "Je suis un assistant pharmacie : je peux t'aider pour les medicaments (prix, "
    "remboursement, equivalents moins chers) et pour trouver une pharmacie. Pour le "
    "reste, je ne suis pas la bonne adresse."
)

NOTE_GARDE = (
    "Les pharmacies de garde changent chaque jour et notre annuaire n'est pas mis a "
    "jour en direct : appelle avant de te deplacer pour confirmer."
)


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


class TranscriptionResponse(BaseModel):
    texte: str
    langue: str
    confiance_langue: float
    duree_audio: float


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
    # equivalents moins chers (intention alternative_moins_chere) :
    # {"reference": {...}, "equivalents": [...]} ou None
    alternatives: dict | None = None


class ChatAudioResponse(ChatResponse):
    # ce que Whisper a entendu, pour que l'interface puisse l'afficher et que
    # l'utilisateur comprenne une reponse a cote de la plaque
    transcription: TranscriptionResponse


@app.get("/health")
def health():
    return {"status": "ok"}


async def _transcrire_upload(fichier: UploadFile, langue: str | None) -> TranscriptionResponse:
    contenu = await fichier.read()
    try:
        # Whisper occupe le CPU plusieurs secondes : appele tel quel dans une
        # route async, il bloquerait la boucle d'evenements et gelerait toute
        # l'API -- /health compris -- le temps de la transcription.
        t = await run_in_threadpool(transcrire, contenu, langue or None)
    except ErreurAudio as e:
        raise HTTPException(status_code=422, detail=str(e))
    return TranscriptionResponse(**t.__dict__)


@app.post("/transcription", response_model=TranscriptionResponse)
async def transcription(
    fichier: UploadFile = File(..., description="Enregistrement audio (webm, ogg, mp4, wav...)"),
    langue: str | None = Form(None, description="Force la langue : 'ar' ou 'fr'. Detection automatique sinon."),
):
    """Transcrit un enregistrement vocal (Whisper, en local).

    Utilise par l'interface pour remplir le champ de saisie : l'utilisateur voit
    ce qui a ete compris et peut le corriger avant d'envoyer, ce qui compte pour
    la darija, que Whisper ne connait qu'approximativement.
    """
    return await _transcrire_upload(fichier, langue)


@app.post("/chat/audio", response_model=ChatAudioResponse)
async def chat_audio(
    fichier: UploadFile = File(...),
    session_id: str | None = Form(None),
    langue: str | None = Form(None),
):
    """Pipeline vocal complet : audio -> transcription -> NLU -> entity linking -> reponse.

    Meme traitement que /chat une fois le texte obtenu, conversation multi-tours
    comprise (meme session_id).
    """
    t = await _transcrire_upload(fichier, langue)
    # chat() est synchrone et attend le LLM : meme raison, hors de la boucle
    reponse = await run_in_threadpool(chat, ChatRequest(text=t.texte, session_id=session_id))
    return ChatAudioResponse(**reponse.model_dump(), transcription=t)


@app.get("/medicaments")
def medicaments(q: str, dosage: str | None = None, limit: int = 12):
    """Recherche de medicaments par nom ou DCI, pour la page dediee du front.

    Reutilise le meme matcher que /chat : le front n'a donc pas de base a lui et
    les resultats sont exactement ceux que l'assistant utiliserait.
    """
    q = q.strip()
    if not q:
        return {"query": q, "resultats": []}
    limit = max(1, min(limit, 30))
    return {"query": q, "resultats": get_med_matcher().match(q, dosage=dosage, top_k=limit)}


@app.get("/pharmacies")
def pharmacies(q: str | None = None, ville: str | None = None, limit: int = 12):
    """Recherche de pharmacies par nom et/ou localisation."""
    nom = (q or "").strip() or None
    lieu = (ville or "").strip() or None
    if not nom and not lieu:
        return {"resultats": [], "note": None}
    limit = max(1, min(limit, 30))
    matcher = get_pharma_matcher()
    resultats = matcher.match(nom=nom, location=lieu, top_k=limit)
    return {"resultats": resultats, "note": matcher.last_location_note}


@app.get("/schema")
def schema():
    """Expose the intent/entite taxonomy the NLU was built against."""
    return _schema


def has_value(x) -> bool:
    """True for real values; False for None/NaN (pandas emits float('nan') for
    missing numeric cells, which is truthy in plain Python -- `if x:` alone
    would treat a missing price as present)."""
    return x is not None and not (isinstance(x, float) and x != x)


# CNOPS and CNSS are two different insurers publishing their own rates, so a
# product can be covered by one and not the other -- the regime has to be named.
REMBOURSEMENT_REGIMES = (
    ("taux_remboursement_cnops", "CNOPS"),
    ("taux_remboursement_cnss", "CNSS"),
)


def remboursement_phrase(priced_variant: dict, variant: dict) -> str | None:
    """Wording for the reimbursement part of a reply, or None if no rate is
    known for either insurer.

    A rate of 0 means "on the list but not reimbursed": phrasing that as
    "rembourse a 0%" would read as a wrong answer, so it is stated plainly.
    """
    rates: dict[str, float] = {}
    for col, label in REMBOURSEMENT_REGIMES:
        taux = priced_variant.get(col)
        if not has_value(taux):
            taux = variant.get(col)
        if has_value(taux):
            rates[label] = float(taux)

    if not rates:
        return None
    if len(set(rates.values())) == 1:
        taux = next(iter(rates.values()))
        who = " et ".join(rates)
        return f"non rembourse ({who})" if taux == 0 else f"rembourse a {taux:.0f}% ({who})"
    return "remboursement : " + ", ".join(f"{label} {v:.0f}%" for label, v in rates.items())


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
    remboursement = remboursement_phrase(priced_variant, variant)
    if remboursement:
        price_bits.append(remboursement)
    if price_bits:
        desc += " -- " + ", ".join(price_bits)
    if match.get("confidence") == "a_confirmer":
        # nom seulement approchant : on le presente comme une hypothese a
        # verifier, pas comme la reponse
        desc = f"Tu parles peut-etre de {desc}. Verifie que c'est bien ce medicament."
    return desc


def describe_alternatives(nom: str, resultat: dict | None) -> str:
    if resultat is None:
        return (
            f"Je n'ai pas la composition complete de {nom} dans ma base : je ne peux "
            "pas te proposer d'equivalent fiable. Ton pharmacien pourra te renseigner."
        )
    ref = resultat["reference"]
    desc_ref = f"{ref['nom']} {ref['dosage']}"
    if not resultat["equivalents"]:
        return (
            f"Je n'ai pas trouve d'autre medicament commercialise avec la meme "
            f"composition, le meme dosage et la meme voie d'administration que "
            f"{desc_ref}. Ton pharmacien pourra verifier s'il existe une alternative."
        )
    prix_ref = f", {ref['ppv']} DH" if ref["ppv"] is not None else ""
    lignes = [
        f"Equivalents de {desc_ref} ({ref['dci']}, {str(ref['forme'] or '').lower()}{prix_ref}), "
        "du moins cher au plus cher :"
    ]
    for e in resultat["equivalents"]:
        ecart = ""
        if ref["ppv"] is not None and e["ppv"] < ref["ppv"]:
            ecart = f" ({ref['ppv'] - e['ppv']:.1f} DH de moins)"
        lignes.append(f"  - {e['nom']}, {str(e['forme'] or '').lower()} -- {e['ppv']} DH{ecart}")
    lignes.append(
        "Meme molecule et meme dosage, mais le changement se fait sur avis de ton "
        "pharmacien : la forme exacte et les excipients peuvent differer."
    )
    return "\n".join(lignes)


def note_garde(texte: str, pharmacies: list[dict]) -> str | None:
    """Avertissement ajoute des qu'il est question de garde : l'annuaire est un
    instantane, alors que les gardes tournent chaque jour."""
    if "garde" in texte.lower() or any(p.get("garde") for p in pharmacies):
        return NOTE_GARDE
    return None


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
    intent = output.get("intent") or "hors_sujet"
    intent = INTENTS_V1.get(intent, intent)
    if intent not in INTENTS_CONNUS:
        intent = "hors_sujet"
    entities = output.get("entities", [])

    medicament_matches: list[dict] = []
    pharmacie_matches: list[dict] = []

    med_entity = next((e for e in entities if e["type"] == "MEDICAMENT"), None)
    dosage_entity = next((e for e in entities if e["type"] == "DOSAGE"), None)
    if med_entity:
        medicament_matches = get_med_matcher().match(
            med_entity["value"], dosage=dosage_entity["value"] if dosage_entity else None, top_k=3,
        )
        # Le matcher renvoie toujours ses meilleurs candidats, meme quand aucun
        # ne ressemble a la requete : c'est a nous d'appliquer ses paliers de
        # confiance. Sans ce filtre, "qwerty" obtenait une reponse chiffree sur
        # un vrai medicament (ERY, 37,4 DH) -- inacceptable dans un contexte de
        # sante. Un candidat "non_fiable" n'est donc jamais montre.
        medicament_matches = [m for m in medicament_matches if m["confidence"] != "non_fiable"]
    medicament_inconnu = med_entity is not None and not medicament_matches

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
        # meme regle pour un nom de pharmacie ; les listes par lieu ("liste_
        # localisation") n'ont pas de score et restent affichees
        pharmacie_matches = [p for p in pharmacie_matches if p["confidence"] != "non_fiable"]

    awaiting_localisation = False
    alternatives = None

    if intent == "conseil_medical":
        # Traite en premier : un patient qui decrit un symptome doit toujours
        # etre oriente vers un professionnel, meme s'il cite un medicament. On
        # n'affiche alors aucune fiche, qui passerait pour une recommandation.
        reply = MESSAGE_CONSEIL_MEDICAL
        medicament_matches = []

    elif medicament_inconnu and intent not in {"info_pharmacie", "salutation", "hors_sujet"}:
        reply = (
            f"Je ne trouve pas « {med_entity['value']} » parmi les medicaments autorises "
            "au Maroc. Verifie l'orthographe, ou essaie le nom de la molecule "
            "(par exemple « paracetamol »)."
        )

    elif intent == "disponibilite_medicament" and medicament_matches:
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

    elif intent == "alternative_moins_chere":
        if medicament_matches:
            nom = medicament_matches[0]["nom_candidat"]
            alternatives = equivalents(
                get_med_matcher(), nom, dosage=dosage_entity["value"] if dosage_entity else None,
            )
            reply = describe_alternatives(nom, alternatives)
        else:
            reply = (
                "De quel medicament veux-tu un equivalent moins cher ? Donne-moi son nom, "
                "et son dosage si tu le connais."
            )

    elif intent == "info_pharmacie":
        if pharmacie_matches:
            reply = "Voici ce que j'ai trouve :\n" + describe_pharmacies(pharmacie_matches)
            if location_note:
                reply += f"\n\n({location_note})"
            garde = note_garde(text, pharmacie_matches)
            if garde:
                reply += f"\n\n{garde}"
        else:
            reply = "Precise le nom de la pharmacie ou ta ville/quartier pour que je puisse chercher."

    elif intent == "posologie_information":
        # La base est un registre d'autorisation et de remboursement : elle ne
        # contient ni posologie ni effets indesirables. On le dit -- mais si le
        # medicament a ete reconnu, autant donner ce qu'on sait vraiment de lui
        # plutot que de renvoyer l'utilisateur les mains vides.
        reply = (
            "Je n'ai pas d'information de posologie fiable dans ma base -- "
            "refere-toi a la notice ou demande a un pharmacien."
        )
        if medicament_matches:
            reply = f"{describe_medicament(medicament_matches[0])}\n{reply}"

    elif intent == "salutation":
        reply = "Bonjour ! Je peux t'aider a trouver un medicament ou une pharmacie, pose ta question."

    elif medicament_matches:
        # Intention hors perimetre (hors_sujet) mais un medicament a bien ete
        # extrait et resolu : une question comme "chno kaydir doliprane ?" tombe
        # ici. Repondre "je n'ai pas compris" en tenant le resultat sous la main
        # serait absurde -- on presente la fiche et on assume la limite.
        reply = (
            f"{describe_medicament(medicament_matches[0])}\n"
            "Je ne suis pas sur d'avoir bien compris ta question, mais voila ce que "
            "je sais de ce medicament. Pour son usage precis, demande a ton pharmacien."
        )

    elif intent == "hors_sujet":
        reply = MESSAGE_HORS_SUJET

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
        alternatives=alternatives,
    )
