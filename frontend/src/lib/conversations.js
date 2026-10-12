// Historique des conversations, conserve dans le navigateur.
//
// Choix assume : l'API garde son etat de dialogue en memoire et n'expose aucun
// endpoint d'historique, donc rien n'est stocke cote serveur. L'historique est
// par consequent propre a cet appareil et disparait si le cache est vide.

import { estArabe } from './langues'

const CLE = 'dwatalk:conversations'

export const ACCUEIL_BOT = {
  role: 'bot',
  text: 'السلام عليكم ! سولني على أي دواء، الثمن، التعويض ولا صيدلية قريبة منك.',
}

export function nouvelleConversation() {
  return {
    id: crypto.randomUUID(),
    titre: 'محادثة جديدة',
    majLe: Date.now(),
    tours: [ACCUEIL_BOT],
    sessionId: null,
    attendLieu: false,
  }
}

export function lireToutes() {
  try {
    const brut = localStorage.getItem(CLE)
    const liste = brut ? JSON.parse(brut) : []
    return Array.isArray(liste) ? liste : []
  } catch {
    return []
  }
}

export function ecrireToutes(conversations) {
  try {
    localStorage.setItem(CLE, JSON.stringify(conversations))
  } catch {
    // quota atteint ou stockage bloque
  }
}

export function titrer(tours) {
  const premier = tours.find((t) => t.role === 'moi')
  if (!premier) return 'محادثة جديدة'
  const texte = premier.text.trim().replace(/\s+/g, ' ')
  return texte.length > 48 ? `${texte.slice(0, 48)}…` : texte
}

export function dateLisible(horodatage, langue = 'ary_ar') {
  const date = new Date(horodatage)
  const maintenant = new Date()
  const arabe = estArabe(langue)
  const locale = arabe ? 'ar-MA' : 'fr-FR'
  const heure = date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })

  if (date.toDateString() === maintenant.toDateString()) {
    return arabe ? `اليوم · ${heure}` : `Aujourd'hui · ${heure}`
  }

  const hier = new Date(maintenant)
  hier.setDate(hier.getDate() - 1)
  if (date.toDateString() === hier.toDateString()) {
    return arabe ? `البارح · ${heure}` : `Hier · ${heure}`
  }

  return `${date.toLocaleDateString(locale, { day: 'numeric', month: 'long' })} · ${heure}`
}
