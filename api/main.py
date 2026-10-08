"""API de DwaTalk, l'assistant pharmacie (Challenge #1).

Le travail est fait par nlp/ : un seul appel LLM par message pour comprendre
la question, puis le code cherche dans data/ et redige une reponse courte,
seulement sur ce qui est demande (voir nlp/moteur.py).

    POST /chat           une question -> une reponse
    POST /chat/audio     voix -> Whisper (local) -> /chat
    POST /transcription  voix -> texte, pour remplir le champ de saisie
    GET  /medicaments    recherche pour la page Medicaments
    GET  /pharmacies     recherche pour la page Pharmacies
    GET  /securite       notice officielle d'une molecule
    GET  /schema         ce que l'analyse a le droit de renvoyer

Lancer :  py -m uvicorn api.main:app --reload --port 8000
Docs :    http://localhost:8000/docs
"""
import uuid
from collections import OrderedDict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api import donnees, resume
from api.parole import ErreurAudio, transcrire
from nlp.analyse.analyseur import charger_schema
from nlp.linking.lieux import charger_pharmacies, resoudre_lieu
from nlp.linking.pharmacies import chercher_pharmacie, distance_km, fiche
from nlp.moteur import Session, repondre
from nlp.outils.pharmacies import plus_proches, type_ouverture
from nlp.outils.resolution import matcher
from nlp.reponse.composeur import telephone_txt
from nlp.reponse.langues import LANGUE_PAR_DEFAUT

app = FastAPI(
    title="DwaTalk API",
    description="Assistant pharmacie en darija, arabe et francais : analyse (1 appel LLM) + bases marocaines",
    version="1.0.0",
)

# Le front de developpement tourne sur sa propre origine. Listees une par une
# plutot que "*" : les routes ne sont pas authentifiees.
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

# Conversations en memoire : session_id -> Session (historique, regime, ville).
# Suffisant pour un serveur de demo a un seul processus ; les plus anciennes
# sont oubliees au-dela de SESSIONS_MAX.
SESSIONS: "OrderedDict[str, Session]" = OrderedDict()
SESSIONS_MAX = 1000


class ChatRequest(BaseModel):
    text: str
    session_id: str | None = None


class TranscriptionResponse(BaseModel):
    texte: str
    langue: str
    confiance_langue: float
    duree_audio: float
    # renseigne quand la transcription est incertaine, pour inviter a relire
    avertissement: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    input: str
    reply: str
    # la meme reponse sans les listes de pharmacies, que l'interface affiche en fiches
    reply_court: str = ""
    langue: str = LANGUE_PAR_DEFAUT
    situation: str | None = None
    intent: str | None = None            # = situation, pour les anciens clients
    demandes: list[str] = []
    pharmacie_matches: list[dict] = []
    # plus de fiche medicament dans le chat : la reponse ne dit que ce qui est demande
    medicament_matches: list[dict] = []
    # texte complet des rubriques de notice demandees, replie sous la reponse
    securite: dict | None = None
    awaiting_localisation: bool = False
    attend: list[str] = []               # ce que le bot vient de demander au patient
    urgence: str | None = None
    validation_errors: list[str] = []    # corrections faites sur l'analyse du LLM
    analyse: dict | None = None
    fournisseur: str | None = None


class ChatAudioResponse(ChatResponse):
    transcription: TranscriptionResponse


def pour_carte(p: dict) -> dict:
    """Une fiche pharmacie telle que l'interface l'affiche : `garde` porte les
    horaires quand la pharmacie est ouverte 24h/24 ou la nuit."""
    carte = dict(p)
    carte["garde"] = p.get("horaires") if type_ouverture(p.get("horaires")) else None
    # "539813017" -> "0539 81 30 17", comme dans la reponse du bot
    carte["telephone"] = telephone_txt(p.get("telephone"))
    return carte


def _session(session_id: str) -> Session:
    session = SESSIONS.get(session_id)
    if session is None:
        session = SESSIONS[session_id] = Session()
        while len(SESSIONS) > SESSIONS_MAX:
            SESSIONS.popitem(last=False)
    SESSIONS.move_to_end(session_id)
    return session


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Le champ 'text' est vide.")
    session_id = req.session_id or str(uuid.uuid4())
    r = repondre(text, _session(session_id))
    return ChatResponse(
        session_id=session_id,
        input=text,
        reply=r.texte,
        reply_court=r.texte_court,
        langue=r.langue,
        situation=r.situation,
        intent=r.situation,
        demandes=r.demandes,
        pharmacie_matches=[pour_carte(p) for p in r.pharmacies],
        securite=r.securite,
        awaiting_localisation=bool({"lieu", "lieu_precis"} & set(r.attend)),
        attend=r.attend,
        urgence=r.urgence,
        validation_errors=r.corrections,
        analyse=r.analyse,
        fournisseur=r.fournisseur,
    )


async def _transcrire_upload(fichier: UploadFile, langue: str | None) -> TranscriptionResponse:
    contenu = await fichier.read()
    try:
        # Whisper occupe le CPU plusieurs secondes : hors de la boucle
        # d'evenements, sinon toute l'API gele pendant la transcription.
        t = await run_in_threadpool(transcrire, contenu, langue or None)
    except ErreurAudio as e:
        raise HTTPException(status_code=422, detail=str(e))
    return TranscriptionResponse(**t.__dict__)


@app.post("/transcription", response_model=TranscriptionResponse)
async def transcription(
    fichier: UploadFile = File(..., description="Enregistrement audio (webm, ogg, mp4, wav...)"),
    langue: str | None = Form(None, description="Force la langue : 'ar' ou 'fr'. Detection automatique sinon."),
):
    """Transcrit un enregistrement vocal (Whisper, en local). L'interface remplit
    le champ de saisie avec le texte : l'utilisateur peut le corriger avant
    d'envoyer, ce qui compte pour la darija, que Whisper connait mal."""
    return await _transcrire_upload(fichier, langue)


@app.post("/chat/audio", response_model=ChatAudioResponse)
async def chat_audio(
    fichier: UploadFile = File(...),
    session_id: str | None = Form(None),
    langue: str | None = Form(None),
):
    """Audio -> transcription -> meme traitement que /chat (meme session)."""
    t = await _transcrire_upload(fichier, langue)
    reponse = await run_in_threadpool(chat, ChatRequest(text=t.texte, session_id=session_id))
    return ChatAudioResponse(**reponse.model_dump(), transcription=t)


def _dci_du_match(match: dict) -> str | None:
    for variante in match.get("variantes", []):
        dci = variante.get("dci")
        if isinstance(dci, str) and dci.strip():
            return dci
    return None


@app.get("/medicaments")
def medicaments(q: str, dosage: str | None = None, limit: int = 12):
    """Recherche de medicaments par nom ou DCI, pour la page dediee : le meme
    matcher que le bot, donc les memes resultats."""
    q = q.strip()
    if not q:
        return {"query": q, "resultats": []}
    limit = max(1, min(limit, 30))
    # Comme dans le chat : un candidat "non_fiable" ne ressemble pas vraiment a
    # la recherche ("Gran" pour "doliprane") et n'est jamais montre.
    resultats = [m for m in matcher().match(q, dosage=dosage, top_k=limit) if m["confidence"] != "non_fiable"]
    for match in resultats:
        dci = _dci_du_match(match)
        match["classes_atc"] = donnees.classes_atc(dci)
        # evite a l'interface un appel par resultat : elle ne charge la notice
        # que du medicament qu'on ouvre
        match["securite_disponible"] = donnees.securite(dci) is not None
    return {"query": q, "resultats": resultats}


def _trier(fiches: list[dict], position: tuple[float, float] | None) -> list[dict]:
    """Avec la position du navigateur : distance ajoutee, du plus proche au plus
    loin ; une position qui ne situe que la ville passe apres les autres."""
    if not position:
        return fiches
    for f in fiches:
        if f.get("latitude") is not None and f.get("longitude") is not None:
            f["distance_km"] = round(distance_km(*position, f["latitude"], f["longitude"]), 2)

    def cle(f):
        approximative = f.get("precision_gps") in (None, "ville", "inconnue")
        return (f.get("distance_km") is None, approximative, f.get("distance_km") or 0.0)

    return sorted(fiches, key=cle)


@app.get("/pharmacies")
def pharmacies(
    q: str | None = None,
    ville: str | None = None,
    limit: int = 12,
    lat: float | None = None,
    lon: float | None = None,
):
    """Pharmacies par nom, par ville ou quartier, ou autour d'un point.

    `lat`/`lon` (position du navigateur) trient du plus proche au plus loin et
    ajoutent `distance_km` ; seuls, ils suffisent ("autour de moi").
    """
    nom = (q or "").strip() or None
    texte_lieu = (ville or "").strip() or None
    position = (lat, lon) if lat is not None and lon is not None else None
    limit = max(1, min(limit, 30))
    note = None

    if nom:
        lieu = resoudre_lieu(texte_lieu) if texte_lieu else None
        ville_lieu = lieu.ville if lieu and lieu.statut in ("quartier", "ville") else None
        pres_de = (lieu.latitude, lieu.longitude) if lieu and lieu.statut == "quartier" else position
        r = chercher_pharmacie(nom, ville=ville_lieu, pres_de=pres_de)
        if r.statut == "ambigu":
            # Sur la page, on montre toutes les homonymes, ville par ville.
            fiches = [f for v in r.villes_possibles for f in chercher_pharmacie(nom, ville=v).pharmacies]
            note = f"« {r.nom} » existe dans {len(r.villes_possibles)} villes : precise la ville pour affiner."
        else:
            fiches = r.pharmacies
            if lieu is not None and lieu.statut not in ("quartier", "ville"):
                note = f"Lieu « {texte_lieu} » non reconnu : recherche dans tout le Maroc."
    elif texte_lieu:
        lieu = resoudre_lieu(texte_lieu)
        if lieu.statut == "quartier":
            fiches = plus_proches(lieu.latitude, lieu.longitude, limit)
        elif lieu.statut == "ville":
            df = charger_pharmacies()
            dans_ville = df[df["ville"] == lieu.ville].sort_values("nom")
            fiches = [fiche(r) for _, r in dans_ville.iterrows()]
            if not position and len(fiches) > limit:
                note = f"{len(fiches)} pharmacies a {lieu.ville} : precise le quartier pour voir les plus proches."
        elif lieu.statut == "ambigu":
            fiches = []
            note = f"« {lieu.nom} » existe a : {', '.join(lieu.villes_possibles)}. Precise la ville."
        else:
            fiches = []
            note = f"Lieu « {texte_lieu} » non reconnu."
    elif position:
        fiches = plus_proches(*position, limit)
    else:
        return {"resultats": [], "note": None}

    fiches = _trier(fiches, position)
    return {"resultats": [pour_carte(f) for f in fiches[:limit]], "note": note}


@app.get("/securite")
def securite(dci: str, langue: str = LANGUE_PAR_DEFAUT):
    """Notice officielle d'une molecule (BDPM / ANSM), mot pour mot : elle decrit
    la molecule, pas la boite vendue au Maroc.

    `langue` ajoute un resume court dans la langue du patient : calcule une
    fois par le LLM a partir du seul texte officiel, puis mis en cache.
    """
    trouve = donnees.securite(dci)
    if not trouve:
        raise HTTPException(status_code=404, detail=f"Aucune fiche de securite pour « {dci} ».")
    # Un resume indisponible (pas de cle, pas de reseau) n'est pas une erreur.
    trouve["resume"] = resume.resumer(trouve, langue)
    trouve["resume_langue"] = langue if trouve["resume"] else None
    return trouve


@app.get("/schema")
def schema():
    """Le vocabulaire de l'analyse : situations, demandes, langues."""
    return charger_schema()
