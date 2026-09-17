/** Khatim : l'etoile a huit branches du zellige, redessinee en trait fin.
 *  Seule citation marocaine explicite de l'interface -- tout le reste du
 *  vocabulaire visuel reste contemporain. */
export function Khatim({ className }) {
  return (
    <svg className={className} viewBox="0 0 64 64" aria-hidden="true">
      <path
        d="M32 5 L39 19 L54 14 L49 29 L63 32 L49 35 L54 50 L39 45 L32 59 L25 45 L10 50 L15 35 L1 32 L15 29 L10 14 L25 19 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="4.5"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function Logo({ compact = false }) {
  return (
    <span className="marque">
      <span className="marque-signe">
        <Khatim />
      </span>
      {!compact && (
        <span className="marque-mot">
          Dwa<em>Talk</em>
        </span>
      )}
    </span>
  )
}
