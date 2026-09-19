/** Puce de question prete a l'emploi. Les exemples sont en darija reelle :
 *  c'est le meilleur moyen de faire comprendre en un coup d'oeil qu'on peut
 *  ecrire comme on parle. */
export default function SuggestionCard({ glyphe, texte, onClick, disabled }) {
  return (
    <button className="puce" onClick={() => onClick(texte)} disabled={disabled} dir="auto">
      <span aria-hidden="true">{glyphe}</span>
      <span>{texte}</span>
    </button>
  )
}
