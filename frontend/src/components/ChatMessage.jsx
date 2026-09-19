import { Khatim } from './Logo'
import MedicineCard from './MedicineCard'
import PharmacyCard from './PharmacyCard'
import SafetyNotice from './SafetyNotice'

/**
 * Phrase d'introduction quand la reponse est presentee en fiches.
 *
 * L'API renvoie un `reply` deja redige, qui repete en texte ce que les fiches
 * montrent mieux. Plutot que d'afficher les deux, on remplace ce pave par une
 * courte amorce et on laisse les fiches porter l'information.
 */
function amorce(meta) {
  const aMed = (meta.medicament_matches ?? []).length > 0
  const aPharma = (meta.pharmacie_matches ?? []).length > 0

  // Les reserves que l'API exprime dans son texte doivent survivre au passage
  // en fiches : remplacer le paragraphe sans les reprendre ferait passer une
  // reponse prudente pour une reponse affirmative.
  if (aMed && meta.intent === 'autre') {
    return "Je ne suis pas sur d'avoir bien compris ta question, mais voici ce que je sais de ce medicament :"
  }
  if (aMed && meta.intent === 'posologie_information') {
    return "Je n'ai pas la posologie dans ma base. Voici ce que je sais de ce medicament :"
  }

  if (aMed && aPharma) return 'Voici le medicament et des pharmacies a contacter :'
  if (aMed) return "Voici ce que j'ai trouve sur ce medicament :"
  if (aPharma) return 'Voici les pharmacies que j’ai trouvees :'
  return null
}

/** Derniere ligne entre parentheses du `reply` : c'est la note d'ambiguite de
 *  lieu ("'Maarif' existe aussi a ..."), une information utile a conserver. */
function noteLieu(reply) {
  const m = /\(([^()]*existe aussi a[^()]*)\)\s*$/i.exec(reply ?? '')
  return m ? m[1] : null
}

export default function ChatMessage({ tour }) {
  const moi = tour.role === 'moi'
  const erreur = tour.role === 'erreur'
  const meta = tour.meta

  const medicaments = meta?.medicament_matches ?? []
  const pharmacies = meta?.pharmacie_matches ?? []
  const structure = !moi && !erreur && (medicaments.length > 0 || pharmacies.length > 0)
  const tete = structure ? amorce(meta) : null
  const note = structure ? noteLieu(meta.reply) : null

  return (
    <div className={`tour ${moi ? 'tour-moi' : ''} ${erreur ? 'tour-erreur' : ''}`}>
      {!moi && (
        <span className="avatar" aria-hidden="true">
          <Khatim />
        </span>
      )}

      <div className={`bulle ${structure ? 'bulle-riche' : ''}`}>
        {structure ? (
          <>
            <p className="bulle-lead">{tete}</p>

            {medicaments.length > 0 && (
              <div className="liste" style={{ marginTop: 12 }}>
                <MedicineCard resultat={medicaments[0]} />
              </div>
            )}

            {pharmacies.length > 0 && (
              <div className="liste" style={{ marginTop: 12 }}>
                {pharmacies.map((p, i) => (
                  <PharmacyCard key={`${p.nom}-${i}`} pharmacie={p} />
                ))}
              </div>
            )}

            {note && (
              <p style={{ marginTop: 10, fontSize: '.83rem', color: 'var(--encre-pale)' }}>
                {note}
              </p>
            )}

            {medicaments.length > 0 && (
              <div style={{ marginTop: 14 }}>
                <SafetyNotice mince />
              </div>
            )}
          </>
        ) : (
          <div dir="auto">{tour.text}</div>
        )}
      </div>
    </div>
  )
}
