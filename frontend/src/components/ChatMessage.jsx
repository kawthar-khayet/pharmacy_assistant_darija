import { Signe } from './Logo'
import MedicineCard from './MedicineCard'
import PharmacyCard from './PharmacyCard'
import SafetyNotice from './SafetyNotice'
import SafetySections from './SafetySections'
import { LANGUE_PAR_DEFAUT, estArabe } from '../lib/langues'

/**
 * Un tour de conversation.
 *
 * Le texte de l'API (`reply`) est la reponse : il ne dit que ce qui a ete
 * demande, dans la langue du patient. S'y ajoutent :
 *  - les fiches des pharmacies trouvees, a la place de leur liste en texte
 *    (`reply_court` est la reponse sans cette liste) ;
 *  - le texte complet des rubriques de notice demandees, replie.
 * Les conversations enregistrees avec l'ancienne API peuvent encore porter une
 * fiche medicament (`medicament_matches`) : elle reste affichee.
 */
export default function ChatMessage({ tour }) {
  const moi = tour.role === 'moi'
  const erreur = tour.role === 'erreur'
  const meta = moi || erreur ? null : tour.meta
  const langue = meta?.langue ?? LANGUE_PAR_DEFAUT
  // l'arabe se lit de droite a gauche : fiches et libelles suivent
  const dir = estArabe(langue) ? 'rtl' : undefined

  const pharmacies = meta?.pharmacie_matches ?? []
  const medicaments = meta?.medicament_matches ?? []
  const securite = meta?.securite
  const riche = pharmacies.length > 0 || medicaments.length > 0 || Boolean(securite?.rubriques)
  const texte = pharmacies.length > 0 && meta?.reply_court ? meta.reply_court : tour.text
  const urgence = Boolean(meta?.urgence)

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
      </div>
    </div>
  )
}
