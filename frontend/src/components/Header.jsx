import Icon from './Icon'

/** En-tete de page : surtitre, titre, sous-titre et, si besoin, un indicateur
 *  d'etat ou une action a droite. */
export default function Header({ titre, sousTitre, surtitre, icone, aside, dirTitre = 'auto' }) {
  return (
    <header className="entete">
      <div>
        {surtitre && (
          <p className="entete-surtitre">
            {icone && <Icon nom={icone} taille={14} epaisseur={2.2} />}
            {surtitre}
          </p>
        )}
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
  return <span className="pastille-dispo">En ligne</span>
}
