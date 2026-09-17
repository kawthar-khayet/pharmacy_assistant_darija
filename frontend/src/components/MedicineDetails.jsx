import { versModele } from '../lib/medicament'
import SafetyNotice from './SafetyNotice'

/**
 * Sections cliniques. Notre base (AMMPS + CNOPS + CNSS) est un registre
 * d'autorisation et de remboursement : elle donne le nom, la DCI, la forme, le
 * prix et la prise en charge, mais elle ne contient ni posologie ni effets
 * indesirables. Ces rubriques existent donc dans la fiche, avec un renvoi
 * explicite vers la notice ou le pharmacien -- plutot qu'un texte invente, qui
 * serait une fausse information medicale.
 */
const RUBRIQUES_CLINIQUES = [
  { glyphe: '📋', titre: 'Utilisation', quoi: "les indications de ce medicament" },
  { glyphe: '⏱️', titre: 'Posologie', quoi: 'la dose et le rythme de prise' },
  { glyphe: '🛡️', titre: 'Precautions', quoi: 'les contre-indications et interactions' },
  { glyphe: '⚡', titre: 'Effets secondaires', quoi: 'les effets indesirables connus' },
]

function Bloc({ glyphe, titre, children }) {
  return (
    <section className="detail-bloc">
      <h4>
        <span aria-hidden="true">{glyphe}</span>
        {titre}
      </h4>
      {children}
    </section>
  )
}

export default function MedicineDetails({ resultat }) {
  const m = versModele(resultat)

  // Phrase de synthese construite uniquement a partir des champs reels.
  const synthese = [
    `${m.nom} est`,
    m.dci ? `un medicament a base de ${m.dci}` : 'un medicament',
    m.classe ? `, de la classe therapeutique ${m.classe}` : '',
    m.forme ? `, presente sous forme de ${m.forme.toLowerCase()}` : '',
    m.dosage ? ` au dosage de ${m.dosage.toLowerCase()}` : '',
    '.',
  ]
    .join('')
    .replace(' ,', ',')

  return (
    <div className="fiche">
      <div className="fiche-tete">
        <span className="fiche-glyphe" aria-hidden="true">💊</span>
        <div style={{ minWidth: 0 }}>
          <div className="fiche-etiquette">Medicament</div>
          <div className="fiche-nom">{m.nom}</div>
          {m.dci && <div className="fiche-dci">{m.dci}</div>}
        </div>
      </div>

      <dl className="fiche-faits">
        {m.prix && (
          <div className="fait fait-prix">
            <dt>Prix indicatif</dt>
            <dd>{m.prix}</dd>
          </div>
        )}
        {(m.dosage || m.forme) && (
          <div className="fait">
            <dt>Forme</dt>
            <dd>{[m.dosage, m.forme].filter(Boolean).join(' — ')}</dd>
          </div>
        )}
        {m.remboursement && (
          <div className="fait">
            <dt>Remboursement</dt>
            <dd>
              {m.remboursement.texte}
              {m.remboursement.detail && (
                <span style={{ fontWeight: 500, color: 'var(--encre-pale)' }}>
                  {' '}
                  ({m.remboursement.detail})
                </span>
              )}
            </dd>
          </div>
        )}
      </dl>

      <div className="detail-sections">
        <Bloc glyphe="🔎" titre="Ce que j'ai compris">
          <p>{synthese}</p>
          <div className="pharma-meta" style={{ marginTop: 10 }}>
            {m.laboratoire && <span className="marqueur">🏭 {m.laboratoire}</span>}
            {m.classe && <span className="marqueur marqueur-terre">{m.classe}</span>}
            {m.statut && <span className="marqueur">{m.statut}</span>}
          </div>
        </Bloc>

        {m.variantes.length > 1 && (
          <Bloc glyphe="📦" titre={`Conditionnements (${m.nbVariantes})`}>
            <div className="detail-variantes">
              {m.variantes.map((v, i) => (
                <div className="variante" key={i}>
                  <span>
                    {[v.dosage, v.forme, v.presentation].filter(Boolean).join(' · ')}
                  </span>
                  {v.prix && <span className="variante-prix">{v.prix}</span>}
                </div>
              ))}
            </div>
          </Bloc>
        )}

        {RUBRIQUES_CLINIQUES.map((r) => (
          <Bloc key={r.titre} glyphe={r.glyphe} titre={r.titre}>
            <p className="detail-absent">
              Notre base recense les medicaments autorises au Maroc et leur prise en
              charge, mais pas {r.quoi}. Reporte-toi a la notice du produit ou demande
              a ton pharmacien.
            </p>
          </Bloc>
        ))}

        <div style={{ padding: '16px 18px', borderTop: '1px solid var(--trait)' }}>
          <SafetyNotice />
        </div>
      </div>
    </div>
  )
}
