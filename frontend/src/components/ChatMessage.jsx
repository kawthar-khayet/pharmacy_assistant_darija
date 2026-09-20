import { Khatim } from './Logo'
import AlternativesList from './AlternativesList'
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
  // Nom seulement approchant : c'est une hypothese, la fiche ne doit pas
  // passer pour une reponse ferme.
  if (aMed && meta.medicament_matches[0].confidence === 'a_confirmer') {
    return 'Tu parles peut-etre de ce medicament ? Verifie que le nom correspond bien :'
  }
  if (aMed && meta.intent === 'hors_sujet') {
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
  const m = /\(([^()]*existe aussi a[^()]*)\)/i.exec(reply ?? '')
  return m ? m[1] : null
}

/** Avertissement sur les gardes ajoute par l'API : l'annuaire est un
 *  instantane, il ne faut pas le perdre en remplacant le texte par des fiches. */
function noteGarde(reply) {
  const m = /(Les pharmacies de garde changent[^\n]*)/.exec(reply ?? '')
  return m ? m[1] : null
}

export default function ChatMessage({ tour }) {
  const moi = tour.role === 'moi'
  const erreur = tour.role === 'erreur'
  const meta = tour.meta

  const medicaments = meta?.medicament_matches ?? []
  const pharmacies = meta?.pharmacie_matches ?? []
  const alternatives = meta?.alternatives
  const avecEquivalents = !moi && !erreur && alternatives?.equivalents?.length > 0

  // Demande d'equivalent sans resultat : le texte de l'API explique pourquoi
  // (composition inconnue, aucun equivalent commercialise). Une fiche du seul
  // medicament d'origine repondrait a cote de la question.
  const equivalentSansResultat =
    meta?.intent === 'alternative_moins_chere' && !avecEquivalents

  const structure =
    !moi && !erreur && !equivalentSansResultat && (medicaments.length > 0 || pharmacies.length > 0)
  const tete = structure ? amorce(meta) : null
  const lieu = structure ? noteLieu(meta.reply) : null
  const garde = structure ? noteGarde(meta.reply) : null

  return (
    <div className={`tour ${moi ? 'tour-moi' : ''} ${erreur ? 'tour-erreur' : ''}`}>
      {!moi && (
        <span className="avatar" aria-hidden="true">
          <Khatim />
        </span>
      )}

      <div className={`bulle ${structure || avecEquivalents ? 'bulle-riche' : ''}`}>
        {avecEquivalents ? (
          <>
            <p className="bulle-lead">
              Voici des équivalents, même molécule et même dosage, du moins cher au plus cher :
            </p>
            <div style={{ marginTop: 12 }}>
              <AlternativesList alternatives={alternatives} />
            </div>
            <div className="securite securite-mince" role="note" style={{ marginTop: 14 }}>
              <span className="securite-glyphe" aria-hidden="true">⚠️</span>
              <div>
                <strong>Demande l'avis de ton pharmacien</strong>
                <p>
                  Le changement de médicament se fait sur son conseil : la forme exacte et
                  les excipients peuvent différer.
                </p>
              </div>
            </div>
          </>
        ) : structure ? (
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

            {lieu && (
              <p style={{ marginTop: 10, fontSize: '.83rem', color: 'var(--encre-pale)' }}>{lieu}</p>
            )}
            {garde && (
              <p style={{ marginTop: 8, fontSize: '.83rem', color: 'var(--alerte)' }}>🌙 {garde}</p>
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
