/** Squelettes plutot qu'un spinner : en montrant la forme du contenu a venir,
 *  l'attente parait plus courte et la page ne saute pas a l'arrivee. */
export default function LoadingState({ variante = 'fiches', nombre = 4 }) {
  if (variante === 'lignes') {
    return (
      <div className="liste" aria-busy="true" aria-label="Chargement">
        {Array.from({ length: nombre }, (_, i) => (
          <div key={i} className="squelette squelette-ligne" style={{ width: `${88 - i * 11}%` }} />
        ))}
      </div>
    )
  }

  return (
    <div className={variante === 'liste' ? 'liste' : 'grille-fiches'} aria-busy="true" aria-label="Chargement">
      {Array.from({ length: nombre }, (_, i) => (
        <div key={i} className="squelette squelette-fiche" />
      ))}
    </div>
  )
}

export function IndicateurFrappe() {
  return (
    <div className="frappe" role="status" aria-label="DwaTalk ecrit">
      <span />
      <span />
      <span />
    </div>
  )
}
