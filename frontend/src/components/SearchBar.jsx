import { useEffect, useRef } from 'react'
import { useDictee } from '../lib/voix'

function Loupe() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
      <path d="M20 20l-3.6-3.6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function Micro() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="9" y="3" width="6" height="11" rx="3" stroke="currentColor" strokeWidth="2" />
      <path
        d="M5 11a7 7 0 0 0 14 0M12 18v3"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  )
}

function Fleche() {
  return (
    <svg width="17" height="17" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 19V5M5.5 11.5L12 5l6.5 6.5"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/**
 * Champ de saisie unique de DwaTalk : sert de barre de recherche sur les pages
 * Medicaments et Pharmacies, et de zone de message sur l'Assistant.
 *
 * C'est un textarea et non un input : les questions en darija depassent souvent
 * une ligne, et il grandit avec le texte plutot que de le faire defiler.
 */
export default function SearchBar({
  valeur,
  onChange,
  onValider,
  placeholder,
  aide,
  avecVoix = true,
  enCours = false,
  autoFocus = false,
}) {
  const champRef = useRef(null)

  const { ecoute, erreur, basculer, disponible } = useDictee({
    onTexte: (texte) => onChange(valeur ? `${valeur} ${texte}` : texte),
  })

  useEffect(() => {
    const champ = champRef.current
    if (!champ) return
    champ.style.height = 'auto'
    champ.style.height = `${champ.scrollHeight}px`
  }, [valeur])

  useEffect(() => {
    if (autoFocus) champRef.current?.focus()
  }, [autoFocus])

  function surTouche(e) {
    // Entree valide, Maj+Entree passe a la ligne : convention attendue ici.
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onValider(valeur)
    }
  }

  return (
    <div>
      <div className="champ">
        <span className="champ-loupe">
          <Loupe />
        </span>

        <textarea
          ref={champRef}
          rows={1}
          dir="auto"
          value={valeur}
          placeholder={placeholder}
          aria-label={placeholder}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={surTouche}
        />

        <div className="champ-actions">
          {avecVoix && disponible && (
            <button
              type="button"
              className={`rond ${ecoute ? 'rond-actif' : ''}`}
              onClick={basculer}
              aria-pressed={ecoute}
              aria-label={ecoute ? 'Arreter la dictee' : 'Dicter ta question'}
              title={ecoute ? 'Arreter la dictee' : 'Dicter ta question'}
            >
              <Micro />
            </button>
          )}
          <button
            type="button"
            className="rond rond-envoi"
            onClick={() => onValider(valeur)}
            disabled={enCours || !valeur.trim()}
            aria-label="Envoyer"
          >
            <Fleche />
          </button>
        </div>
      </div>

      {(erreur || aide) && (
        <p className="champ-aide" role={erreur ? 'alert' : undefined}>
          {erreur || aide}
        </p>
      )}
    </div>
  )
}
