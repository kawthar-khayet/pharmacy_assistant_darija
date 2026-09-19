// Centres approximatifs des principales villes marocaines, pour cadrer le plan.
//
// Ce sont des reperes de ville, pas des positions de pharmacies : la source de
// l'annuaire (saydalia.ma) ne fournit pas de coordonnees exploitables -- elle
// renvoie le point d'origine de la requete, pas l'etablissement. On situe donc
// la ville sur le plan, sans poser d'epingle qui serait fausse.

const VILLES = {
  casablanca: [33.5731, -7.5898],
  rabat: [34.0209, -6.8416],
  marrakech: [31.6295, -7.9811],
  fes: [34.0181, -5.0078],
  tanger: [35.7595, -5.834],
  agadir: [30.4278, -9.5981],
  meknes: [33.8935, -5.5473],
  oujda: [34.6867, -1.9114],
  kenitra: [34.261, -6.5802],
  tetouan: [35.5785, -5.3684],
  sale: [34.0531, -6.7985],
  temara: [33.9287, -6.9067],
  'el jadida': [33.2316, -8.5007],
  safi: [32.2994, -9.2372],
  mohammedia: [33.6866, -7.383],
  nador: [35.1681, -2.9335],
  'beni mellal': [32.3373, -6.3498],
  khouribga: [32.8811, -6.9063],
  guelmim: [28.987, -10.0574],
  laayoune: [27.1253, -13.1625],
  chefchaouen: [35.1688, -5.2636],
  essaouira: [31.5085, -9.7595],
  'ksar el kebir': [35.0011, -5.9036],
  berrechid: [33.2655, -7.5872],
  settat: [33.0011, -7.6166],
  taza: [34.21, -4.01],
  taourirt: [34.4073, -2.8967],
}

const sansAccent = (s) =>
  String(s)
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()

export function coordonneesVille(nom) {
  if (!nom) return null
  const cle = sansAccent(nom)
  if (VILLES[cle]) return VILLES[cle]
  // tolere "Maarif Casablanca" ou "pharmacie de Rabat"
  const trouve = Object.keys(VILLES).find((v) => cle.includes(v))
  return trouve ? VILLES[trouve] : null
}

/** Cadre OpenStreetMap autour d'un point, sans cle d'API ni traceur. */
export function urlPlan([lat, lon], rayon = 0.045) {
  const bbox = [lon - rayon, lat - rayon * 0.62, lon + rayon, lat + rayon * 0.62]
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox.join('%2C')}&layer=mapnik`
}

export function urlItineraire(adresse, ville) {
  const requete = [adresse, ville, 'Maroc'].filter(Boolean).join(', ')
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(requete)}`
}
