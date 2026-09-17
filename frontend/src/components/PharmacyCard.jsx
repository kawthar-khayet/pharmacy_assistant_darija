import { casseTitre } from '../lib/medicament'
import { urlItineraire } from '../lib/villes'

/**
 * Fiche pharmacie. La source (saydalia.ma) ne fournit ni coordonnees GPS
 * fiables ni horaires complets : on n'affiche donc ni distance ni "ouvert
 * maintenant" calcules, qui seraient inventes. Le champ `garde` existe en
 * revanche vraiment, et c'est l'information la plus utile de nuit.
 */
export default function PharmacyCard({ pharmacie }) {
  const nom = pharmacie.nom ?? 'Pharmacie'
  const tel = pharmacie.telephone
  const garde = pharmacie.garde

  return (
    <article className="pharma">
      <span className="pharma-glyphe" aria-hidden="true">🏥</span>

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
          {garde ? (
            <span className="marqueur marqueur-ok">🌙 De garde · {casseTitre(garde)}</span>
          ) : (
            <span className="marqueur">Horaires non renseignes</span>
          )}
          {pharmacie.ville && <span className="marqueur">📍 {pharmacie.ville}</span>}

          {tel && (
            <a className="bouton-tel" href={`tel:${String(tel).replace(/\s/g, '')}`}>
              <span aria-hidden="true">📞</span>
              {tel}
            </a>
          )}

          {pharmacie.adresse && (
            <a
              className="marqueur"
              href={urlItineraire(pharmacie.adresse, pharmacie.ville)}
              target="_blank"
              rel="noreferrer noopener"
            >
              🧭 Itineraire
            </a>
          )}
        </div>
      </div>
    </article>
  )
}
