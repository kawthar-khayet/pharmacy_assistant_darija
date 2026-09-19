/** En-tete de page : titre, sous-titre et, si besoin, un indicateur d'etat
 *  ou une action a droite. */
export default function Header({ titre, sousTitre, aside, dirTitre = 'auto' }) {
  return (
    <header className="entete">
      <div>
        <h1 dir={dirTitre}>{titre}</h1>
        {sousTitre && (
          <p className="entete-sous" dir="auto">
            {sousTitre}
          </p>
        )}
      </div>
      {aside}
    </header>
  )
}

export function Disponible() {
  return <span className="pastille-dispo">Disponible</span>
}
