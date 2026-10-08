import Icon from './Icon'

/** Puce de question prete a l'emploi. Les exemples sont en darija reelle :
 *  c'est le meilleur moyen de faire comprendre en un coup d'oeil qu'on peut
 *  ecrire comme on parle. */
export default function SuggestionCard({ icone, texte, onClick, disabled }) {
  return (
    <button className="puce" onClick={() => onClick(texte)} disabled={disabled} dir="auto">
      {icone && <Icon nom={icone} taille={15} />}
      <span>{texte}</span>
    </button>
  )
}
