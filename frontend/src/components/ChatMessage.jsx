import { useState } from 'react'
import { Signe } from './Logo'
import Icon from './Icon'
import MedicineCard from './MedicineCard'
import PharmacyCard from './PharmacyCard'
import SafetyNotice from './SafetyNotice'
import SafetySections from './SafetySections'
import { LANGUE_PAR_DEFAUT, estArabe, t } from '../lib/langues'

/**
 * Un tour de conversation optimise pour le dialogue en Darija.
 * Permet la copie rapide du texte, la mise en forme riche et le respect du sens RTL/LTR.
 */
export default function ChatMessage({ tour }) {
  const [copie, setCopie] = useState(false)
  const moi = tour.role === 'moi'
  const erreur = tour.role === 'erreur'
  const meta = moi || erreur ? null : tour.meta
  const langue = meta?.langue ?? LANGUE_PAR_DEFAUT
  const dir = estArabe(langue) ? 'rtl' : undefined

  const pharmacies = meta?.pharmacie_matches ?? []
  const medicaments = meta?.medicament_matches ?? []
  const securite = meta?.securite
  const riche = pharmacies.length > 0 || medicaments.length > 0 || Boolean(securite?.rubriques)
  const texte = pharmacies.length > 0 && meta?.reply_court ? meta.reply_court : tour.text
  const urgence = Boolean(meta?.urgence)

  async function copierTexte() {
    try {
      await navigator.clipboard.writeText(texte)
      setCopie(true)
      setTimeout(() => setCopie(false), 2000)
    } catch {
      // echec presse-papier
    }
  }

  return (
    <div className={`tour ${moi ? 'tour-moi' : ''} ${erreur || urgence ? 'tour-erreur' : ''}`}>
      {!moi && (
        <span className="avatar" aria-hidden="true">
          <Signe />
        </span>
      )}

      <div className={`bulle ${riche ? 'bulle-riche' : ''}`} dir={dir}>
        {riche ? (
          <>
            <p className="bulle-lead" dir="auto" style={{ whiteSpace: 'pre-line' }}>{texte}</p>

            {pharmacies.length > 0 && (
              <div className="liste" style={{ marginTop: 12 }}>
                {pharmacies.map((p, i) => (
                  <PharmacyCard key={`${p.nom}-${i}`} pharmacie={p} langue={langue} />
                ))}
              </div>
            )}

            {medicaments.length > 0 && (
              <div className="liste" style={{ marginTop: 12 }}>
                <MedicineCard resultat={medicaments[0]} langue={langue} />
              </div>
            )}

            {securite?.rubriques && (
              <div style={{ marginTop: 12 }}>
                <SafetySections securite={securite} langue={langue} />
              </div>
            )}

            {(securite?.rubriques || medicaments.length > 0) && (
              <div style={{ marginTop: 14 }}>
                <SafetyNotice mince langue={langue} />
              </div>
            )}
          </>
        ) : (
          <div dir="auto">{texte}</div>
        )}

        {!moi && !erreur && (
          <div className="bulle-pied">
            <button
              type="button"
              className="btn-copier-bulle"
              onClick={copierTexte}
              title={copie ? t(langue, 'chat_copie_fait') : t(langue, 'chat_copier')}
              aria-label={copie ? t(langue, 'chat_copie_fait') : t(langue, 'chat_copier')}
            >
              <Icon nom={copie ? 'valide' : 'liste'} taille={13} />
              <span>{copie ? t(langue, 'chat_copie_fait') : t(langue, 'chat_copier')}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
