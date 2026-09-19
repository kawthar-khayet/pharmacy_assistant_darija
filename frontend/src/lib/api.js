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

export function chercherPharmacies({ q, ville, limit = 12, signal } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (q) params.set('q', q)
  if (ville) params.set('ville', ville)
  return appeler(`/pharmacies?${params}`, { signal })
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
