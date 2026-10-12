// Entrees de navigation, partagees par la barre laterale et la barre basse.
// `cle` renvoie vers le dictionnaire de traductions de lib/langues.js.
// `icone` designe un trace de components/Icon.jsx.

export const NAVIGATION = [
  { to: '/', icone: 'accueil', cle: 'nav_accueil', exact: true },
  { to: '/assistant', icone: 'message', cle: 'nav_assistant' },
  { to: '/medicaments', icone: 'pilule', cle: 'nav_medicaments' },
  { to: '/pharmacies', icone: 'lieu', cle: 'nav_pharmacies', exact: true },
  { to: '/garde', icone: 'lune', cle: 'nav_garde' },
  { to: '/historique', icone: 'historique', cle: 'nav_historique' },
]

/** Fait defiler la page d'accueil jusqu'a une de ses sections. */
export function allerA(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
