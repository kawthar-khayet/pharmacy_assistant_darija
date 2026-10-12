import { useLanguage } from '../lib/languageContexte'

export default function LanguageSelector({ compact = false }) {
  const { langue, setLangue, langues } = useLanguage()

  return (
    <div
      className={`selecteur-langue ${compact ? 'selecteur-compact' : ''}`}
      role="radiogroup"
      aria-label="Choisir la langue / اختار اللغة"
    >
      {langues.map((item) => {
        const actif = item.code === langue
        return (
          <button
            key={item.code}
            type="button"
            role="radio"
            aria-checked={actif}
            className={`btn-langue ${actif ? 'btn-langue-actif' : ''}`}
            onClick={() => setLangue(item.code)}
            title={item.libelle}
          >
            {compact ? item.etiquette : item.libelle}
          </button>
        )
      })}
    </div>
  )
}
