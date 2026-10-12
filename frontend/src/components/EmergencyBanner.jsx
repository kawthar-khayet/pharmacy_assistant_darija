import { useState } from 'react'
import Icon from './Icon'
import { useLanguage } from '../lib/languageContexte'

const NUMEROS_URGENCE = [
  { nomCle: 'urgence_samu', numero: '141', description: 'SAMU · Ambulance Maroc' },
  { nomCle: 'urgence_pompiers', numero: '15', description: 'Protection Civile' },
  { nomCle: 'urgence_poison', numero: '0801000180', affichage: '0801 000 180', description: 'Centre Antipoison Maroc' },
]

export default function EmergencyBanner() {
  const { t } = useLanguage()
  const [ouvert, setOuvert] = useState(false)

  return (
    <div className="bandeau-urgence-wrap">
      <button
        type="button"
        className="bouton-urgence-declencheur"
        onClick={() => setOuvert((v) => !v)}
        aria-expanded={ouvert}
        aria-label={t('urgences_titre')}
      >
        <span className="urgence-pulse" aria-hidden="true" />
        <Icon nom="pouls" taille={15} />
        <span>{t('urgence_bouton')} 141 / 15</span>
      </button>

      {ouvert && (
        <div className="fenetre-urgence">
          <div className="fenetre-urgence-tete">
            <div className="fenetre-urgence-titre">
              <Icon nom="alerte" taille={18} />
              <h4>{t('urgences_titre')}</h4>
            </div>
            <button
              type="button"
              className="btn-fermer-urgence"
              onClick={() => setOuvert(false)}
              aria-label="Fermer"
            >
              <Icon nom="croix" taille={16} />
            </button>
          </div>

          <p className="fenetre-urgence-desc">
            {t('securite_texte')}
          </p>

          <div className="liste-urgences">
            {NUMEROS_URGENCE.map((u) => (
              <a
                key={u.numero}
                href={`tel:${u.numero}`}
                className="carte-urgence-item"
              >
                <div className="urgence-info">
                  <span className="urgence-nom">{t(u.nomCle)}</span>
                  <span className="urgence-desc">{u.description}</span>
                </div>
                <span className="urgence-num-badge">
                  <Icon nom="telephone" taille={14} />
                  {u.affichage ?? u.numero}
                </span>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
