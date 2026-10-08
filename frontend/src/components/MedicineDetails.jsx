import { useEffect, useState } from 'react'
import { versModele } from '../lib/medicament'
import { chercherSecurite } from '../lib/api'
import Icon from './Icon'
import SafetyNotice from './SafetyNotice'

/**
 * Rubriques de securite, telles qu'elles arrivent de l'API (notice officielle
 * francaise, verbatim). Le texte n'est ni resume ni traduit ici : une
 * contre-indication reformulee est une contre-indication faussee.
 */
const RUBRIQUES_SECURITE = [
  { cle: 'indications', icone: 'loupe', titre: 'A quoi sert ce medicament' },
  { cle: 'contre_indications', icone: 'bouclier', titre: 'Contre-indications' },
  { cle: 'precautions', icone: 'alerte', titre: 'Precautions' },
  { cle: 'interactions', icone: 'liste', titre: 'Interactions' },
  { cle: 'grossesse_allaitement', icone: 'pouls', titre: 'Grossesse et allaitement' },
  { cle: 'effets_indesirables', icone: 'eclair', titre: 'Effets indesirables' },
]

/**
 * Ce que notre base ne contient toujours pas. La posologie en fait partie : la
 * notice francaise en donne une, mais pour un dosage et un conditionnement qui
 * ne sont pas forcement ceux de la boite achetee au Maroc.
 */
const RUBRIQUES_ABSENTES = [
  { icone: 'horloge', titre: 'Posologie', quoi: 'la dose et le rythme de prise' },
]

function Bloc({ icone, titre, children }) {
  return (
    <section className="detail-bloc">
      <h4>
        <Icon nom={icone} taille={16} epaisseur={2.1} />
        {titre}
      </h4>
      {children}
    </section>
  )
}

export default function MedicineDetails({ resultat }) {
  const m = versModele(resultat)
  const [securite, setSecurite] = useState(null)
  const [chargement, setChargement] = useState(false)

  useEffect(() => {
    const controleur = new AbortController()
    setSecurite(null)
    if (!m.dciBrute) return undefined
    setChargement(true)
    // Resume demande en darija latine : l'interface est en francais, mais le
    // patient qui la consulte parle darija -- c'est justement pour lui que ce
    // resume existe, le texte officiel juste dessous etant en francais.
    chercherSecurite(m.dciBrute, { langue: 'ary_lat', signal: controleur.signal })
      .then(setSecurite)
      // Une fiche de securite absente ou une API muette ne doit pas casser la
      // fiche medicament : le reste des informations est deja la.
      .catch(() => setSecurite(null))
      .finally(() => {
        if (!controleur.signal.aborted) setChargement(false)
      })
    return () => controleur.abort()
  }, [m.dciBrute])

  // Phrase de synthese construite uniquement a partir des champs reels.
  const synthese = [
    `${m.nom} est `,
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
        <span className="fiche-glyphe">
          <Icon nom="pilule" taille={20} />
        </span>
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
        <Bloc icone="loupe" titre="Ce que j'ai compris">
          <p>{synthese}</p>
          <div className="pharma-meta" style={{ marginTop: 10 }}>
            {m.laboratoire && <span className="marqueur">
                <Icon nom="usine" taille={12} /> {m.laboratoire}
              </span>}
            {m.classe && <span className="marqueur marqueur-bleu">{m.classe}</span>}
            {m.statut && <span className="marqueur">{m.statut}</span>}
            {/* Code de la notice d'abord : c'est celui qui fait foi. A defaut,
                les classes ATC rattachees a la molecule par RxNav. */}
            {securite?.code_atc ? (
              <span className="marqueur marqueur-bleu" title="Code ATC officiel (notice)">
                ATC {securite.code_atc}
              </span>
            ) : (
              m.classesAtc.map((c) => (
                <span className="marqueur" key={c.code} title={c.libelle}>
                  ATC {c.code}
                </span>
              ))
            )}
          </div>
        </Bloc>

        {m.variantes.length > 1 && (
          <Bloc icone="boite" titre={`Conditionnements (${m.nbVariantes})`}>
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

        {chargement && (
          <Bloc icone="bouclier" titre="Informations de securite">
            <p className="detail-absent">Lecture de la notice officielle…</p>
          </Bloc>
        )}

        {securite && (
          <>
            {securite.resume && (
              <Bloc icone="etincelle" titre="Resume automatique">
                <p>{securite.resume}</p>
                <p className="detail-absent">
                  Resume genere automatiquement a partir des textes officiels ci-dessous.
                  En cas de doute, c'est le texte officiel qui fait foi.
                </p>
              </Bloc>
            )}

            {RUBRIQUES_SECURITE.filter((r) => securite.rubriques[r.cle]).map((r) => (
              <Bloc key={r.cle} icone={r.icone} titre={r.titre}>
                <p className="detail-texte">{securite.rubriques[r.cle]}</p>
              </Bloc>
            ))}

            <Bloc icone="base" titre="D'ou vient ce texte">
              <p className="detail-absent">
                Notice officielle de <strong>{securite.specialite_source}</strong>, publiee
                par l'ANSM (base de donnees publique des medicaments), relevee le{' '}
                {securite.date_recuperation}. Ce texte decrit la <strong>molecule</strong>{' '}
                ({securite.dci}), pas la boite vendue au Maroc : le dosage, le
                conditionnement et le laboratoire peuvent differer.{' '}
                <a href={securite.source_url} target="_blank" rel="noreferrer noopener">
                  Voir la notice
                </a>
              </p>
            </Bloc>
          </>
        )}

        {!chargement && !securite && (
          <Bloc icone="bouclier" titre="Informations de securite">
            <p className="detail-absent">
              Je n'ai pas de notice officielle pour cette molecule. Reporte-toi a la
              notice de la boite ou demande a ton pharmacien.
            </p>
          </Bloc>
        )}

        {RUBRIQUES_ABSENTES.map((r) => (
          <Bloc key={r.titre} icone={r.icone} titre={r.titre}>
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
