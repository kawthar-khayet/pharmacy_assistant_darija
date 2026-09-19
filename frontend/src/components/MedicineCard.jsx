import { versModele } from '../lib/medicament'

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
export default function MedicineCard({ resultat, onOuvrir }) {
  const m = versModele(resultat)
  const cliquable = Boolean(onOuvrir)

  const contenu = (
    <>
      <div className="fiche-tete">
        <span className="fiche-glyphe" aria-hidden="true">💊</span>
        <div style={{ minWidth: 0 }}>
          <div className="fiche-etiquette">Medicament</div>
          <div className="fiche-nom">{m.nom}</div>
          {m.dci && <div className="fiche-dci">{m.dci}</div>}
        </div>
      </div>

      <dl className="fiche-faits">
        <Fait libelle="Prix indicatif" valeur={m.prix} classe="fait-prix" />
        <Fait libelle="Forme" valeur={[m.dosage, m.forme].filter(Boolean).join(' — ')} />
        <Fait
          libelle="Remboursement"
          valeur={m.remboursement ? m.remboursement.texte : null}
        />
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
