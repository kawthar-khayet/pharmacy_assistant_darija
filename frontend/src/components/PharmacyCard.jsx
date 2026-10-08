import Icon from './Icon'
import { casseTitre } from '../lib/medicament'
import { urlItineraire, urlItineraireVers } from '../lib/villes'
import { LANGUE_PAR_DEFAUT, t } from '../lib/langues'

/**
 * Fiche pharmacie.
 *
 * La distance n'est affichee que si la position vient de l'officine
 * elle-meme (`precision_gps === 'exacte'`). Les autres positions situent la
 * voie, le quartier ou le centre-ville : annoncer « a 300 m » a partir d'un
 * centre-ville serait une mesure inventee. Pour celles-la on nomme ce qu'on
 * sait -- le secteur -- sans chiffre.
 *
 * Les horaires restent absents de la source : pas de « ouvert maintenant ».
 * Le champ `garde` existe en revanche vraiment, et c'est l'information la plus
 * utile de nuit.
 */
const LIBELLE_PRECISION = {
  rue: 'position approchee (la voie)',
  quartier: 'position approchee (le quartier)',
  ville: 'position approchee (la ville)',
}

export default function PharmacyCard({ pharmacie, langue = LANGUE_PAR_DEFAUT }) {
  const nom = pharmacie.nom ?? 'Pharmacie'
  const tel = pharmacie.telephone
  const garde = pharmacie.garde
  const exacte = pharmacie.precision_gps === 'exacte'
  const distance = exacte && typeof pharmacie.distance_km === 'number' ? pharmacie.distance_km : null
  const approximative = pharmacie.precision_gps && !exacte

  return (
    <article className="pharma">
      <span className="pharma-glyphe">
        <Icon nom="plus" epaisseur={2.6} />
      </span>

      <div className="pharma-corps">
        <h3 className="pharma-nom">{nom}</h3>
        {pharmacie.adresse && (
          <p className="pharma-adresse">
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
              {distance < 1 ? `${Math.round(distance * 1000)} m` : `${distance.toFixed(1)} km`}
            </span>
          )}
          {approximative && (
            <span className="marqueur" title={LIBELLE_PRECISION[pharmacie.precision_gps]}>
              <Icon nom="question" taille={12} /> {LIBELLE_PRECISION[pharmacie.precision_gps]}
            </span>
          )}
          {garde ? (
            <span className="marqueur marqueur-ok">
              <Icon nom="lune" taille={12} /> {t(langue, 'de_garde')} · {casseTitre(garde)}
            </span>
          ) : (
            <span className="marqueur">{t(langue, 'horaires_inconnus')}</span>
          )}
          {pharmacie.ville && <span className="marqueur">
              <Icon nom="lieu" taille={12} /> {pharmacie.ville}
            </span>}

          {tel && (
            <a className="bouton-tel" href={`tel:${String(tel).replace(/\s/g, '')}`}>
              <Icon nom="telephone" taille={13} />
              {tel}
            </a>
          )}

          {(pharmacie.adresse || exacte) && (
            <a
              className="marqueur"
              href={
                exacte
                  ? urlItineraireVers(pharmacie.latitude, pharmacie.longitude)
                  : urlItineraire(pharmacie.adresse, pharmacie.ville)
              }
              target="_blank"
              rel="noreferrer noopener"
            >
              <Icon nom="itineraire" taille={12} /> {t(langue, 'itineraire')}
            </a>
          )}
        </div>
      </div>
    </article>
  )
}
