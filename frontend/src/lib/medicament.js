// Mise en forme des resultats bruts du matcher en un modele d'affichage.

const present = (v) => v !== null && v !== undefined && v !== ''

/** Les noms de la base sont en majuscules (normalisation du nettoyage) :
 *  affiches tels quels ils crient, alors on les remet en casse de titre. */
export function casseTitre(texte) {
  if (!texte) return ''
  return String(texte)
    .toLowerCase()
    .replace(/(^|[\s('/-])([\p{L}])/gu, (_, avant, lettre) => avant + lettre.toUpperCase())
}

export function prixLisible(ppv) {
  if (!present(ppv)) return null
  // les prix marocains s'ecrivent avec deux decimales quand il y en a
  const n = Number(ppv)
  return `${Number.isInteger(n) ? n : n.toFixed(2)} DH`
}

/**
 * CNOPS et CNSS publient chacune son taux : un produit peut etre pris en charge
 * par l'une et pas par l'autre, donc on nomme toujours le regime. Un taux de 0
 * veut dire "inscrit sur la liste mais non rembourse", ce qui se lirait comme
 * une erreur s'il etait affiche "rembourse a 0%".
 */
export function remboursementLisible(variante) {
  if (!variante) return null
  const taux = {}
  if (present(variante.taux_remboursement_cnops)) taux.CNOPS = Number(variante.taux_remboursement_cnops)
  if (present(variante.taux_remboursement_cnss)) taux.CNSS = Number(variante.taux_remboursement_cnss)

  const regimes = Object.keys(taux)
  if (regimes.length === 0) return null

  const valeurs = new Set(Object.values(taux))
  if (valeurs.size === 1) {
    const v = [...valeurs][0]
    const qui = regimes.join(' et ')
    return v === 0 ? { texte: 'Non rembourse', detail: qui } : { texte: `${v}%`, detail: qui }
  }
  return {
    texte: regimes.map((r) => `${r} ${taux[r]}%`).join(' · '),
    detail: null,
  }
}

/** Reduit un resultat du matcher a ce dont l'interface a besoin. */
export function versModele(resultat) {
  const variantes = resultat?.variantes ?? []
  const base = variantes[0] ?? {}
  // la premiere variante peut ne pas porter de prix alors qu'une autre en a
  // (conditionnements differents du meme produit) : on prefere celle qui en a un
  const avecPrix = variantes.find((v) => present(v.ppv)) ?? base
  const avecClasse = variantes.find((v) => present(v.classe_therapeutique)) ?? base
  const avecLabo = variantes.find((v) => present(v.laboratoire)) ?? base

  return {
    nom: casseTitre(resultat?.nom_candidat ?? base.nom),
    nomBrut: resultat?.nom_candidat ?? base.nom,
    dci: casseTitre(base.dci),
    dosage: base.dosage ?? null,
    forme: casseTitre(base.forme),
    presentation: casseTitre(base.presentation),
    laboratoire: casseTitre(avecLabo.laboratoire),
    classe: casseTitre(avecClasse.classe_therapeutique),
    statut: casseTitre(base.statut_commercialisation),
    prix: prixLisible(avecPrix.ppv),
    remboursement: remboursementLisible(avecPrix) ?? remboursementLisible(base),
    confiance: resultat?.confidence ?? null,
    score: resultat?.score ?? null,
    nbVariantes: resultat?.nb_variantes ?? variantes.length,
    variantes: variantes.map((v) => ({
      dosage: v.dosage,
      forme: casseTitre(v.forme),
      presentation: casseTitre(v.presentation),
      prix: prixLisible(v.ppv),
      source: v.source,
    })),
  }
}
