import { useEffect, useState } from 'react'
import { versModele } from '../lib/medicament'
import { chercherSecurite } from '../lib/api'
import Icon from './Icon'
import SafetyNotice from './SafetyNotice'
import { useLanguage } from '../lib/languageContexte'

const RUBRIQUES_SECURITE = [
  { cle: 'indications', icone: 'loupe', titreAr: 'فاش كيصلح هاد الدواء', titreFr: 'À quoi sert ce médicament' },
  { cle: 'contre_indications', icone: 'bouclier', titreAr: 'موانع الاستعمال', titreFr: 'Contre-indications' },
  { cle: 'precautions', icone: 'alerte', titreAr: 'الاحتياطات والتحذيرات', titreFr: 'Précautions' },
  { cle: 'interactions', icone: 'liste', titreAr: 'التفاعلات مع أدوية أخرى', titreFr: 'Interactions' },
  { cle: 'grossesse_allaitement', icone: 'pouls', titreAr: 'الحمل والرضاعة', titreFr: 'Grossesse et allaitement' },
  { cle: 'effets_indesirables', icone: 'eclair', titreAr: 'الأعراض والآثار الجانبية', titreFr: 'Effets indésirables' },
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
  const { langue, estArabe, t } = useLanguage()
  const m = versModele(resultat)
  const [securite, setSecurite] = useState(null)
  const [chargement, setChargement] = useState(false)
  const dciBrute = m.dciBrute

  useEffect(() => {
    if (!dciBrute) return undefined

    const controleur = new AbortController()
    // Indique le chargement pour la nouvelle molecule
    const timer = setTimeout(() => setChargement(true), 0)

    const langueNotice = estArabe ? 'ary_ar' : 'ary_lat'

    chercherSecurite(dciBrute, { langue: langueNotice, signal: controleur.signal })
      .then((data) => {
        setSecurite(data)
      })
      .catch(() => setSecurite(null))
      .finally(() => {
        if (!controleur.signal.aborted) setChargement(false)
      })

    return () => {
      clearTimeout(timer)
      controleur.abort()
    }
  }, [dciBrute, estArabe])

  const synthese = [
    m.nom,
    m.dci ? ` (${m.dci})` : '',
    m.classe ? ` · ${m.classe}` : '',
    m.forme ? ` · ${m.forme}` : '',
    m.dosage ? ` · ${m.dosage}` : '',
  ].filter(Boolean).join('')

  return (
    <div className="fiche detail-fiche" dir={estArabe ? 'rtl' : 'ltr'}>
      <div className="fiche-tete">
        <span className="fiche-glyphe" aria-hidden="true">
          <Icon nom="pilule" taille={22} />
        </span>
        <div style={{ minWidth: 0 }}>
          <div className="fiche-etiquette">{t('medicament')}</div>
          <div className="fiche-nom" dir="auto">{m.nom}</div>
          {m.dci && <div className="fiche-dci" dir="auto">{m.dci}</div>}
        </div>
      </div>

      <dl className="fiche-faits">
        {m.prix && (
          <div className="fait fait-prix">
            <dt>{t('prix_indicatif')}</dt>
            <dd>{m.prix}</dd>
          </div>
        )}
        {(m.dosage || m.forme) && (
          <div className="fait">
            <dt>{t('forme')}</dt>
            <dd>{[m.dosage, m.forme].filter(Boolean).join(' — ')}</dd>
          </div>
        )}
        {m.remboursement && (
          <div className="fait fait-rembourse">
            <dt>{t('remboursement')}</dt>
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
        <Bloc icone="loupe" titre={estArabe ? 'ملخص الدواء' : 'Ce que l’on sait'}>
          <p dir="auto">{synthese}</p>
          <div className="pharma-meta" style={{ marginTop: 10 }}>
            {m.laboratoire && (
              <span className="marqueur">
                <Icon nom="usine" taille={12} /> {m.laboratoire}
              </span>
            )}
            {m.classe && <span className="marqueur marqueur-bleu">{m.classe}</span>}
            {m.statut && <span className="marqueur">{m.statut}</span>}
            {securite?.code_atc ? (
              <span className="marqueur marqueur-bleu" title="Code ATC officiel">
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
          <Bloc icone="boite" titre={estArabe ? `العلب والتقديم (${m.nbVariantes})` : `Conditionnements (${m.nbVariantes})`}>
            <div className="detail-variantes">
              {m.variantes.map((v, i) => (
                <div className="variante" key={i}>
                  <span dir="auto">
                    {[v.dosage, v.forme, v.presentation].filter(Boolean).join(' · ')}
                  </span>
                  {v.prix && <span className="variante-prix">{v.prix}</span>}
                </div>
              ))}
            </div>
          </Bloc>
        )}

        {chargement && (
          <Bloc icone="bouclier" titre={t('notice_titre')}>
            <p className="detail-absent">{estArabe ? 'كنقراو النشرة الرسمية للدواء...' : 'Lecture de la notice officielle…'}</p>
          </Bloc>
        )}

        {securite && (
          <>
            {securite.resume && (
              <Bloc icone="etincelle" titre={t('resume_auto_titre')}>
                <p dir="auto">{securite.resume}</p>
                <p className="detail-absent" dir="auto">
                  {t('resume_auto_note')}
                </p>
              </Bloc>
            )}

            {RUBRIQUES_SECURITE.filter((r) => securite.rubriques[r.cle]).map((r) => (
              <Bloc key={r.cle} icone={r.icone} titre={estArabe ? r.titreAr : r.titreFr}>
                <p className="detail-texte" dir="auto">{securite.rubriques[r.cle]}</p>
              </Bloc>
            ))}

            <Bloc icone="base" titre={estArabe ? 'مصدر المعلومات' : 'D’où vient ce texte'}>
              <p className="detail-absent" dir="auto">
                {estArabe
                  ? `النشرة الرسمية الخاصة بـ ${securite.specialite_source} المنشورة بقاعدة البيانات العمومية. هذا النص يخص المادة الفعالة (${securite.dci}).`
                  : `Notice officielle de ${securite.specialite_source}, publiée par l'ANSM. Ce texte décrit la molécule (${securite.dci}).`}{' '}
                {securite.source_url && (
                  <a href={securite.source_url} target="_blank" rel="noreferrer noopener">
                    {estArabe ? 'عرض النشرة الكاملة' : 'Voir la notice'}
                  </a>
                )}
              </p>
            </Bloc>
          </>
        )}

        {!chargement && !securite && (
          <Bloc icone="bouclier" titre={t('notice_titre')}>
            <p className="detail-absent" dir="auto">
              {estArabe
                ? 'النشرة الرسمية غير متوفرة حاليا لهاد المادة. يرجى الرجوع لنشرة العلبة أو استشارة الصيدلي.'
                : 'Notice officielle indisponible pour cette molécule. Reporte-toi à la boîte ou demande à ton pharmacien.'}
            </p>
          </Bloc>
        )}

        <Bloc icone="horloge" titre={estArabe ? 'طريقة الاستعمال والجرعة' : 'Posologie'}>
          <p className="detail-absent" dir="auto">
            {estArabe
              ? 'دوا توك ما كيعطيش المقادير والجرعات ديال الدوا. سول الطبيب ديالك ولا الصيدلي باش تاخد الجرعة المناسبة لسنك وحالتك.'
              : 'DwaTalk ne donne jamais de posologie. Demande toujours à ton médecin ou à ton pharmacien pour adapter la dose à ta situation.'}
          </p>
        </Bloc>

        <div style={{ padding: '16px 18px', borderTop: '1px solid var(--trait)' }}>
          <SafetyNotice langue={langue} />
        </div>
      </div>
    </div>
  )
}
