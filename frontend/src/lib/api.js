// Client de l'API DwaTalk (FastAPI). Voir ../../../api/README.md
export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

export class ApiError extends Error {}

const HORS_LIGNE =
  `Impossible de joindre l'API sur ${API_BASE}. Le serveur est-il demarre ? ` +
  '(uvicorn api.main:app --port 8000)'

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
  let response
  try {
    response = await fetch(`${API_BASE}${chemin}`, options)
  } catch {
    // fetch ne rejette que sur une panne reseau, ce qui ici veut presque
    // toujours dire que l'API n'est pas lancee : autant le dire franchement.
    throw new ApiError(HORS_LIGNE)
  }
  return lire(response)
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
