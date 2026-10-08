/** Signe DwaTalk : une croix de pharmacie traversee par un trait de pouls.
 *  La croix dit « sante » avant meme qu'on lise le nom ; le pouls, qu'il
 *  s'agit d'un service vivant, qui repond. */
export function Signe({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M9 3.5h6v5.5h5.5v6H15v5.5H9V15H3.5V9H9z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path
        d="M5 12h3.2l1.6-2.6 2.6 5.2 1.6-2.6H19"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Logo({ compact = false }) {
  return (
    <span className="marque">
      <span className="marque-signe">
        <Signe />
      </span>
      {!compact && (
        <span className="marque-mot">
          Dwa<em>Talk</em>
        </span>
      )}
    </span>
  )
}
