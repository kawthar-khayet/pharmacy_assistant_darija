import Icon from './Icon'
import { versModele } from '../lib/medicament'
import { LANGUE_PAR_DEFAUT, t } from '../lib/langues'

function Fait({ libelle, valeur, classe = '' }) {
  if (!valeur) return null
  return (
    <div className={`fait ${classe}`}>
      <dt>{libelle}</dt>
      <dd>{valeur}</dd>
    </div>
  )
}

/**
 * Fiche compacte d'un medicament : le meme composant sert dans la reponse de
 * l'assistant et dans les resultats de la page Medicaments, pour qu'un produit
 * se presente partout de la meme facon.
 *
 * Les donnees viennent en un seul bloc de texte cote API ; les eclater en faits
 * separes rend la reponse balayable d'un coup d'oeil au lieu d'un paragraphe.
 */
export default function MedicineCard({ resultat, onOuvrir, langue = LANGUE_PAR_DEFAUT }) {
  const m = versModele(resultat)
  const remboursement = m.remboursement
    ? m.remboursement.nul ? t(langue, 'non_rembourse') : m.remboursement.texte
    : null
  const cliquable = Boolean(onOuvrir)

  const contenu = (
    <>
      <div className="fiche-tete">
        <span className="fiche-glyphe">
          <Icon nom="pilule" taille={20} />
        </span>
        <div style={{ minWidth: 0 }}>
          <div className="fiche-etiquette">
            {t(langue, 'medicament')}
            {m.confiance === 'a_confirmer' && (
              <span className="marqueur marqueur-verifier" style={{ marginLeft: 8 }}>
                {t(langue, 'nom_approchant')}
              </span>
            )}
          </div>
          <div className="fiche-nom">{m.nom}</div>
          {m.dci && <div className="fiche-dci">{m.dci}</div>}
        </div>
      </div>

      <dl className="fiche-faits">
        <Fait libelle={t(langue, 'prix_indicatif')} valeur={m.prix} classe="fait-prix" />
        <Fait libelle={t(langue, 'forme')} valeur={[m.dosage, m.forme].filter(Boolean).join(' — ')} />
        <Fait libelle={t(langue, 'remboursement')} valeur={remboursement} />
      </dl>
    </>
  )

  if (!cliquable) return <article className="fiche">{contenu}</article>

  return (
    <article
      className="fiche fiche-cliquable"
      role="button"
      tabIndex={0}
      onClick={() => onOuvrir(resultat)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOuvrir(resultat)
        }
      }}
      aria-label={`Voir la fiche de ${m.nom}`}
    >
      {contenu}
    </article>
  )
}
