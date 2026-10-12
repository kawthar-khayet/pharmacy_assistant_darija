import { useEffect, useRef } from 'react'
import { useDictee } from '../lib/voix'
import { useLanguage } from '../lib/languageContexte'

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
 * Champ de saisie ergonomique de DwaTalk : barre de recherche et zone de dialogue.
 * Supporte la voix en Darija (Whisper) avec retour visuel d'ondes sonores en temps reel.
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
  const { t, estArabe } = useLanguage()

  const { etat, erreur, avertissement, basculer, disponible } = useDictee({
    onTexte: (texte) => {
      onChange(valeur ? `${valeur} ${texte}` : texte)
      champRef.current?.focus()
    },
  })
  const ecoute = etat === 'ecoute'
  const transcription = etat === 'transcription'

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
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onValider(valeur)
    }
  }

  const libellePlaceholder = placeholder ?? t('hero_placeholder')
  const libelleAide = aide ?? t('hero_aide')

  return (
    <div className={`champ-conteneur ${ecoute ? 'champ-en-ecoute' : ''}`} dir={estArabe ? 'rtl' : 'ltr'}>
      <div className="champ">
        <span className="champ-loupe">
          <Loupe />
        </span>

        <textarea
          ref={champRef}
          rows={1}
          dir="auto"
          value={valeur}
          placeholder={libellePlaceholder}
          aria-label={libellePlaceholder}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={surTouche}
        />

        {ecoute && (
          <div className="onde-vocale" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
        )}

        <div className="champ-actions">
          {avecVoix && disponible && (
            <button
              type="button"
              className={`rond ${ecoute ? 'rond-actif' : ''} ${transcription ? 'rond-attente' : ''}`}
              onClick={basculer}
              disabled={transcription}
              aria-pressed={ecoute}
              aria-label={
                transcription
                  ? t('transcription_en_cours')
                  : ecoute
                    ? t('micro_arreter')
                    : t('micro_demarrer')
              }
              title={
                transcription
                  ? t('transcription_en_cours')
                  : ecoute
                    ? t('micro_arreter')
                    : t('micro_demarrer')
              }
            >
              {transcription ? <span className="mini-roue" aria-hidden="true" /> : <Micro />}
            </button>
          )}
          <button
            type="button"
            className="rond rond-envoi"
            onClick={() => onValider(valeur)}
            disabled={enCours || !valeur.trim()}
            aria-label={t('envoyer')}
          >
            <Fleche />
          </button>
        </div>
      </div>

      {(erreur || avertissement || libelleAide || ecoute || transcription) && (
        <p className="champ-aide" role={erreur || avertissement ? 'alert' : 'status'} dir="auto">
          {erreur ||
            (ecoute
              ? t('ecoute_en_cours')
              : transcription
                ? t('transcription_en_cours')
                : avertissement || libelleAide)}
        </p>
      )}
    </div>
  )
}
