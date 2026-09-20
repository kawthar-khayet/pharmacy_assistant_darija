import { casseTitre, prixLisible } from '../lib/medicament'

/**
 * Equivalents d'un medicament : meme composition, meme dosage, meme voie
 * d'administration, du moins cher au plus cher (voir `equivalents()` dans
 * nlu/entity_linking.py pour les garde-fous appliques cote serveur).
 */
export default function AlternativesList({ alternatives }) {
  const { reference: ref, equivalents } = alternatives

  return (
    <div className="fiche">
      <div className="fiche-tete">
        <span className="fiche-glyphe" aria-hidden="true">💊</span>
        <div style={{ minWidth: 0 }}>
          <div className="fiche-etiquette">Équivalents de</div>
          <div className="fiche-nom">
            {casseTitre(ref.nom)} {ref.dosage}
          </div>
          <div className="fiche-dci">
            {casseTitre(ref.dci)}
            {ref.forme ? ` · ${casseTitre(ref.forme)}` : ''}
            {ref.ppv != null ? ` · ${prixLisible(ref.ppv)}` : ''}
          </div>
        </div>
      </div>

      <div style={{ padding: '4px 18px 16px' }}>
        <div className="detail-variantes">
          {equivalents.map((e) => {
            const economie = ref.ppv != null && e.ppv < ref.ppv ? ref.ppv - e.ppv : null
            return (
              <div className="variante" key={e.nom}>
                <span>
                  <strong>{casseTitre(e.nom)}</strong>
                  {e.forme ? ` · ${casseTitre(e.forme)}` : ''}
                  {e.meme_forme && (
                    <span className="marqueur marqueur-ok" style={{ marginLeft: 8 }}>
                      même forme
                    </span>
                  )}
                </span>
                <span className="variante-prix">
                  {prixLisible(e.ppv)}
                  {economie != null && (
                    <span style={{ display: 'block', fontSize: '.72rem', fontWeight: 600, color: 'var(--dispo)' }}>
                      −{economie.toFixed(1)} DH
                    </span>
                  )}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
