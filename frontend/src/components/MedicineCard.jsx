import Icon from './Icon'
import { versModele } from '../lib/medicament'
import { t } from '../lib/langues'
import { useLanguage } from '../lib/languageContexte'

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
 * Fiche moderne d'un medicament aux standards UI/UX de sante :
 * met en valeur le prix en Dirhams (DH), le taux de remboursement CNSS/CNOPS
 * et la forme galenique de facon scanable d'un coup d'oeil.
 */
export default function MedicineCard({ resultat, onOuvrir, langue }) {
  const { langue: langueContexte } = useLanguage()
  const codeLangue = langue ?? langueContexte

  const m = versModele(resultat)
  const estRemboursable = m.remboursement && !m.remboursement.nul
  const remboursement = m.remboursement
    ? m.remboursement.nul ? t(codeLangue, 'non_rembourse') : m.remboursement.texte
    : null
  const cliquable = Boolean(onOuvrir)

  const contenu = (
    <>
      <div className="fiche-tete">
        <span className="fiche-glyphe" aria-hidden="true">
          <Icon nom="pilule" taille={20} />
        </span>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="fiche-etiquette">
            <span>{t(codeLangue, 'medicament')}</span>
            {m.confiance === 'a_confirmer' && (
              <span className="marqueur marqueur-verifier">
                {t(codeLangue, 'nom_approchant')}
              </span>
            )}
            {estRemboursable && (
              <span className="marqueur marqueur-ok">
                <Icon nom="valide" taille={12} />
                {t(codeLangue, 'remboursable')}
              </span>
            )}
          </div>
          <div className="fiche-nom" dir="auto">{m.nom}</div>
          {m.dci && <div className="fiche-dci" dir="auto">{m.dci}</div>}
        </div>
      </div>

      <dl className="fiche-faits">
        <Fait libelle={t(codeLangue, 'prix_indicatif')} valeur={m.prix} classe="fait-prix" />
        <Fait libelle={t(codeLangue, 'forme')} valeur={[m.dosage, m.forme].filter(Boolean).join(' — ')} />
        <Fait libelle={t(codeLangue, 'remboursement')} valeur={remboursement} classe={estRemboursable ? 'fait-rembourse' : ''} />
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
