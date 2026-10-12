import Icon from './Icon'
import { casseTitre } from '../lib/medicament'
import { urlItineraire, urlItineraireVers } from '../lib/villes'
import { t } from '../lib/langues'
import { useLanguage } from '../lib/languageContexte'

const TYPE_DE_GARDE = {
  jour: 'garde_jour',
  nuit: 'garde_nuit',
  '24h': 'garde_24h',
}

const LIBELLE_PRECISION = {
  rue: 'موقع تقريبي (الشارع)',
  quartier: 'موقع تقريبي (الحي)',
  ville: 'موقع تقريبي (المدينة)',
}

export default function PharmacyCard({ pharmacie, langue }) {
  const { langue: langueContexte } = useLanguage()
  const codeLangue = langue ?? langueContexte

  const nom = pharmacie.nom ?? 'Pharmacie'
  const tel = pharmacie.telephone
  const typeGardeCle = TYPE_DE_GARDE[pharmacie.pharmacie_de_garde?.type]
  const gardeLibelle = typeGardeCle ? t(codeLangue, typeGardeCle) : pharmacie.garde
  const exacte = pharmacie.precision_gps === 'exacte'
  const distance = exacte && typeof pharmacie.distance_km === 'number' ? pharmacie.distance_km : null
  const approximative = pharmacie.precision_gps && !exacte

  return (
    <article className="pharma">
      <span className="pharma-glyphe" aria-hidden="true">
        <Icon nom="lieu" taille={18} epaisseur={2.4} />
      </span>

      <div className="pharma-corps">
        <div className="pharma-entete-ligne">
          <h3 className="pharma-nom" dir="auto">{nom}</h3>
          {gardeLibelle && (
            <span className="badge-garde-actif">
              <span className="point-lumineux" aria-hidden="true" />
              <Icon nom="lune" taille={12} />
              {t(codeLangue, 'de_garde')} · {casseTitre(gardeLibelle)}
            </span>
          )}
        </div>

        {pharmacie.adresse && (
          <p className="pharma-adresse" dir="auto">
            {pharmacie.adresse}
            {pharmacie.ville && !pharmacie.adresse.includes(pharmacie.ville)
              ? ` — ${pharmacie.ville}`
              : ''}
          </p>
        )}

        <div className="pharma-meta">
          {distance !== null && (
            <span className="marqueur marqueur-bleu">
              <Icon nom="cible" taille={12} />{' '}
              {distance < 1 ? `${Math.round(distance * 1000)} م` : `${distance.toFixed(1)} كلم`}
            </span>
          )}
          {approximative && (
            <span className="marqueur" title={LIBELLE_PRECISION[pharmacie.precision_gps]}>
              <Icon nom="question" taille={12} /> {LIBELLE_PRECISION[pharmacie.precision_gps]}
            </span>
          )}
          {!gardeLibelle && (
            <span className="marqueur">{t(codeLangue, 'horaires_inconnus')}</span>
          )}
          {pharmacie.ville && (
            <span className="marqueur">
              <Icon nom="lieu" taille={12} /> {pharmacie.ville}
            </span>
          )}
        </div>

        <div className="pharma-actions-rapides">
          {tel && (
            <a className="bouton-action-pharma bouton-tel" href={`tel:${String(tel).replace(/\s/g, '')}`}>
              <Icon nom="telephone" taille={14} />
              <span>{t(codeLangue, 'appeler')} ({tel})</span>
            </a>
          )}

          {(pharmacie.adresse || exacte) && (
            <a
              className="bouton-action-pharma bouton-itineraire"
              href={
                exacte
                  ? urlItineraireVers(pharmacie.latitude, pharmacie.longitude)
                  : urlItineraire(pharmacie.adresse, pharmacie.ville)
              }
              target="_blank"
              rel="noreferrer noopener"
            >
              <Icon nom="itineraire" taille={14} />
              <span>{t(codeLangue, 'itineraire')}</span>
            </a>
          )}
        </div>
      </div>
    </article>
  )
}
