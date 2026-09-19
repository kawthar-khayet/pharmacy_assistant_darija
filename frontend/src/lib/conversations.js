// Historique des conversations, conserve dans le navigateur.
//
// Choix assume : l'API garde son etat de dialogue en memoire et n'expose aucun
// endpoint d'historique, donc rien n'est stocke cote serveur. L'historique est
// par consequent propre a cet appareil et disparait si le cache est vide.

const CLE = 'dwatalk:conversations'

export const ACCUEIL_BOT = {
  role: 'bot',
  text: 'Salam ! Sawwelni 3la shi dwa wla shi saydaliya. Ktebli b darija, b l3arbiya wla b lfrancais.',
}

export function nouvelleConversation() {
  return {
    id: crypto.randomUUID(),
    titre: 'Nouvelle discussion',
    majLe: Date.now(),
    tours: [ACCUEIL_BOT],
    sessionId: null,
    attendLieu: false,
  }
}

/** localStorage peut lever (navigation privee, stockage bloque ou plein) : on
 *  ne laisse jamais ca casser le rendu, quitte a repartir d'un historique vide. */
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
    // quota atteint ou stockage bloque : la conversation en cours reste
    // utilisable en memoire, seule la persistance est perdue
  }
}

/** Titre tire du premier message reellement ecrit par l'utilisateur, pour que
 *  l'historique soit lisible sans avoir a ouvrir chaque discussion. */
export function titrer(tours) {
  const premier = tours.find((t) => t.role === 'moi')
  if (!premier) return 'Nouvelle discussion'
  const texte = premier.text.trim().replace(/\s+/g, ' ')
  return texte.length > 48 ? `${texte.slice(0, 48)}…` : texte
}

export function dateLisible(horodatage) {
  const date = new Date(horodatage)
  const maintenant = new Date()
  const heure = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })

  if (date.toDateString() === maintenant.toDateString()) return `Aujourd'hui · ${heure}`

  const hier = new Date(maintenant)
  hier.setDate(hier.getDate() - 1)
  if (date.toDateString() === hier.toDateString()) return `Hier · ${heure}`

  return `${date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })} · ${heure}`
}
