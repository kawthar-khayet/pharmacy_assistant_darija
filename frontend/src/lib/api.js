// Client de l'API DwaTalk (FastAPI). Voir ../../../api/README.md
export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

export class ApiError extends Error {}

const HORS_LIGNE = import.meta.env.VITE_API_BASE
  ? 'Le serveur ne répond pas pour le moment. Réessaie dans quelques minutes.'
  : `Impossible de joindre l'API sur ${API_BASE}. Le serveur est-il demarre ? ` +
    '(uvicorn api.main:app --port 8000)'

// --- Reveil de l'API ---------------------------------------------------------
// Sur Azure, l'API s'eteint apres quelques minutes sans visite et met 1 a 3 min
// a redemarrer. On la reveille des l'ouverture du site (sans attendre la 1re
// question), on previent le bandeau si elle tarde, et les appels attendent
// son reveil au lieu d'afficher une erreur.
const ATTENTE_MAX_MS = 3 * 60 * 1000
const PAUSE_MS = 4000
const DELAI_BANDEAU_MS = 3000

let demarrage = false
let reveilEnCours = null
const abonnes = new Set()

function signalerDemarrage(valeur) {
  if (demarrage === valeur) return
  demarrage = valeur
  abonnes.forEach((f) => f(valeur))
}

/** Pour le bandeau : f(true) quand l'API demarre, f(false) quand elle est prete. */
export function surDemarrage(f) {
  abonnes.add(f)
  f(demarrage)
  return () => abonnes.delete(f)
}

const pause = (ms) => new Promise((r) => setTimeout(r, ms))

/** Interroge /health jusqu'a ce que l'API reponde (3 min au plus). Un seul
 *  reveil a la fois : les appels qui arrivent pendant ce temps l'attendent. */
export function reveillerApi() {
  if (reveilEnCours) return reveilEnCours
  const bandeau = setTimeout(() => signalerDemarrage(true), DELAI_BANDEAU_MS)
  reveilEnCours = (async () => {
    const limite = Date.now() + ATTENTE_MAX_MS
    while (Date.now() < limite) {
      try {
        if ((await fetch(`${API_BASE}/pret`)).ok) return true
      } catch {
        // API encore eteinte : on reessaie
      }
      await pause(PAUSE_MS)
    }
    return false
  })().finally(() => {
    clearTimeout(bandeau)
    signalerDemarrage(false)
    reveilEnCours = null
  })
  return reveilEnCours
}

// Reponses d'Azure pendant le demarrage. FastAPI, lui, renvoie toujours du JSON :
// son 503 « index absent » n'est donc pas confondu avec un reveil.
function estDemarrage(response) {
  return [502, 503, 504].includes(response.status) &&
    !response.headers.get('content-type')?.includes('application/json')
}

async function lire(response) {
  if (!response.ok) {
    let detail = `Erreur ${response.status}`
    try {
      const corps = await response.json()
      // 422 de FastAPI : `detail` est une liste d'erreurs de validation
      if (Array.isArray(corps?.detail)) detail = corps.detail.map((e) => e.msg).join(', ')
      else if (corps?.detail) detail = corps.detail
    } catch {
      // corps non JSON : on garde le message tire du code HTTP
    }
    throw new ApiError(detail)
  }
  return response.json()
}

async function appeler(chemin, options) {
  for (let essai = 0; essai < 2; essai++) {
    let response = null
    try {
      response = await fetch(`${API_BASE}${chemin}`, options)
    } catch {
      if (options?.signal?.aborted) break
    }
    if (response && !estDemarrage(response)) return lire(response)
    // API eteinte ou en train de demarrer : on attend son reveil, puis on reessaie une fois
    if (essai > 0 || !(await reveillerApi())) break
  }
  throw new ApiError(HORS_LIGNE)
}

export function envoyerMessage(texte, sessionId, signal) {
  return appeler('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: texte, session_id: sessionId ?? null }),
    signal,
  })
}

export function chercherMedicaments(q, { limit = 12, signal } = {}) {
  const params = new URLSearchParams({ q, limit: String(limit) })
  return appeler(`/medicaments?${params}`, { signal })
}

/** `position` ({lat, lon}) trie les resultats par distance et renseigne
 *  `distance_km`. Seule, elle suffit : c'est la recherche « autour de moi ». */
export function chercherPharmacies({ q, ville, position, limit = 12, signal } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (q) params.set('q', q)
  if (ville) params.set('ville', ville)
  if (position) {
    params.set('lat', String(position.lat))
    params.set('lon', String(position.lon))
  }
  return appeler(`/pharmacies?${params}`, { signal })
}

/** Pharmacies de garde du jour dans une ville. `connu` est faux quand le tour
 *  de garde de cette ville n'est pas disponible ; `position` trie par distance. */
export function chercherPharmaciesDeGarde(ville, { position, signal } = {}) {
  const params = new URLSearchParams({ ville })
  if (position) {
    params.set('lat', String(position.lat))
    params.set('lon', String(position.lon))
  }
  return appeler(`/pharmacies/garde?${params}`, { signal })
}

/** Rubriques de securite d'une molecule (notice officielle, verbatim).
 *  Renvoie null quand la molecule n'est pas couverte : c'est un cas normal,
 *  pas une panne, et l'appelant affiche simplement la fiche sans ces sections. */
export async function chercherSecurite(dci, { langue = 'fr', signal } = {}) {
  if (!dci) return null
  try {
    return await appeler(`/securite?${new URLSearchParams({ dci, langue })}`, { signal })
  } catch (err) {
    if (err instanceof ApiError && /Aucune fiche/.test(err.message)) return null
    throw err
  }
}

/** Position du navigateur, en promesse. Le refus de l'utilisateur est une
 *  reponse legitime, pas une erreur a afficher en rouge. */
export function positionActuelle({ timeout = 10000 } = {}) {
  return new Promise((resoudre, rejeter) => {
    if (!navigator.geolocation) {
      rejeter(new Error("Ton navigateur ne sait pas donner ta position."))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (p) => resoudre({ lat: p.coords.latitude, lon: p.coords.longitude }),
      (err) =>
        rejeter(
          new Error(
            err.code === err.PERMISSION_DENIED
              ? "Tu as refuse le partage de ta position."
              : "Position indisponible pour le moment.",
          ),
        ),
      { timeout, enableHighAccuracy: true },
    )
  })
}

/** Envoie un enregistrement a Whisper (cote API) et renvoie le texte entendu.
 *  Pas d'en-tete Content-Type : le navigateur doit le poser lui-meme pour y
 *  inclure la frontiere du multipart. */
export function transcrire(audio, { langue } = {}) {
  const corps = new FormData()
  const extension = audio.type.includes('mp4') ? 'mp4' : audio.type.includes('ogg') ? 'ogg' : 'webm'
  corps.append('fichier', audio, `question.${extension}`)
  if (langue) corps.append('langue', langue)
  return appeler('/transcription', { method: 'POST', body: corps })
}
