import { useEffect, useRef, useState } from 'react'
import Header from '../components/Header'
import Icon from '../components/Icon'
import SearchBar from '../components/SearchBar'
import PharmacyCard from '../components/PharmacyCard'
import LoadingState from '../components/LoadingState'
import { ApiError, chercherPharmaciesDeGarde, positionActuelle } from '../lib/api'
import { useLanguage } from '../lib/languageContexte'

const VILLES_COURANTES = [
  { fr: 'Casablanca', ar: 'الدار البيضاء' },
  { fr: 'Rabat', ar: 'الرباط' },
  { fr: 'Marrakech', ar: 'مراكش' },
  { fr: 'Tanger', ar: 'طنجة' },
  { fr: 'Agadir', ar: 'أكادير' },
  { fr: 'Fes', ar: 'فاس' },
]

function dateLisible(iso, estArabe) {
  const jour = new Date(`${iso}T12:00:00`)
  if (Number.isNaN(jour.getTime())) return iso
  return jour.toLocaleDateString(estArabe ? 'ar-MA' : 'fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export default function Garde() {
  const { t, estArabe } = useLanguage()
  const [requete, setRequete] = useState('')
  const [reponse, setReponse] = useState(null)
  const [type, setType] = useState('tout')
  const [enCours, setEnCours] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [position, setPosition] = useState(null)

  const abandonRef = useRef(null)
  useEffect(() => () => abandonRef.current?.abort(), [])

  const types = [
    { cle: 'tout', libelle: t('garde_toutes') },
    { cle: 'jour', libelle: t('garde_jour') },
    { cle: 'nuit', libelle: t('garde_nuit') },
    { cle: '24h', libelle: t('garde_24h') },
  ]

  async function chercher(texte, point = position) {
    const ville = String(texte ?? '').trim()
    if (!ville) return

    abandonRef.current?.abort()
    const controleur = new AbortController()
    abandonRef.current = controleur

    setEnCours(true)
    setErreur(null)
    setType('tout')
    try {
      setReponse(await chercherPharmaciesDeGarde(ville, { position: point, signal: controleur.signal }))
    } catch (err) {
      if (err.name === 'AbortError') return
      setErreur(err instanceof ApiError ? err.message : 'Recherche impossible pour le moment.')
      setReponse(null)
    } finally {
      if (!controleur.signal.aborted) setEnCours(false)
    }
  }

  async function trierParDistance() {
    try {
      const point = await positionActuelle()
      setPosition(point)
      if (reponse?.ville) chercher(reponse.ville, point)
    } catch (err) {
      setErreur(err.message ?? 'Position indisponible.')
    }
  }

  const toutes = reponse?.resultats ?? []
  const visibles = type === 'tout' ? toutes : toutes.filter((p) => p.pharmacie_de_garde?.type === type)

  return (
    <div className="page" dir={estArabe ? 'rtl' : 'ltr'}>
      <Header
        titre={t('garde_titre')}
        surtitre={t('garde_surtitre')}
        icone="lune"
        sousTitre={t('garde_soustitre')}
      />

      <SearchBar
        valeur={requete}
        onChange={setRequete}
        onValider={(v) => chercher(v)}
        placeholder={t('garde_placeholder')}
        aide={t('garde_aide')}
        enCours={enCours}
      />

      <div className="puces" style={{ justifyContent: 'flex-start' }}>
        {VILLES_COURANTES.map((v) => {
          const nomVille = estArabe ? v.ar : v.fr
          return (
            <button
              key={v.fr}
              className="puce"
              onClick={() => {
                setRequete(nomVille)
                chercher(nomVille)
              }}
            >
              <Icon nom="lieu" taille={15} />
              {nomVille}
            </button>
          )
        })}
      </div>

      <div style={{ marginTop: 30 }}>
        {enCours && <LoadingState variante="liste" nombre={4} />}

        {erreur && !enCours && (
          <div className="vide">
            <div className="vide-glyphe">
              <Icon nom="debranche" taille={24} />
            </div>
            <h3>{estArabe ? 'البحث غير متوفر حاليا' : 'Recherche indisponible'}</h3>
            <p>{erreur}</p>
          </div>
        )}

        {!enCours && !erreur && reponse === null && (
          <div className="vide">
            <div className="vide-glyphe">
              <Icon nom="lune" taille={24} />
            </div>
            <h3>{estArabe ? 'أي مدينة؟' : 'Quelle ville ?'}</h3>
            <p>{estArabe ? 'كتب اسم مدينتك باش تشوف صيدليات الحراسة لي شغالين اليوم.' : 'Indique ta ville pour voir les pharmacies de garde aujourd’hui.'}</p>
          </div>
        )}

        {!enCours && !erreur && reponse && !reponse.connu && (
          <div className="vide">
            <div className="vide-glyphe">
              <Icon nom="question" taille={24} />
            </div>
            <h3>{t('garde_indispo_titre')}</h3>
            <p>
              {reponse.note} {estArabe ? 'جرب تقلب بمدينة أكبر، ولا اتصل بأقرب صيدلية راها كتعلق صيدلية الحراسة فالباب.' : 'Essaie le nom d’une ville plus grande, ou appelle une pharmacie proche.'}
            </p>
          </div>
        )}

        {!enCours && !erreur && reponse?.connu && (
          <>
            <h2 className="section-titre" style={{ marginTop: 0 }}>
              {toutes.length} {t('de_garde')} {estArabe ? `فـ ${reponse.ville}` : `à ${reponse.ville}`}
            </h2>
            <p style={{ margin: '-8px 0 14px', fontSize: '.84rem', color: 'var(--encre-douce)' }}>
              {dateLisible(reponse.date, estArabe)} · {t('garde_appeler_avant')}
            </p>

            <div className="puces" style={{ justifyContent: 'flex-start', marginBottom: 16 }}>
              {types.map((item) => (
                <button
                  key={item.cle}
                  className="puce"
                  aria-pressed={type === item.cle}
                  style={type === item.cle ? { borderColor: 'var(--sante)', color: 'var(--sante-fonce)', background: 'var(--sante-voile)' } : undefined}
                  onClick={() => setType(item.cle)}
                >
                  {item.libelle}
                </button>
              ))}
              <button className="puce" onClick={trierParDistance}>
                <Icon nom="cible" taille={15} />
                {position ? (estArabe ? 'مرتبة حسب الأقرب' : 'Triées par distance') : t('garde_proches_moi')}
              </button>
            </div>

            {visibles.length === 0 ? (
              <p style={{ color: 'var(--encre-douce)' }}>
                {estArabe ? 'ما كايناش صيدلية بهاد النوع د الحراسة اليوم.' : 'Aucune pharmacie de ce type aujourd’hui.'}
              </p>
            ) : (
              <div className="liste">
                {visibles.map((p, i) => (
                  <PharmacyCard key={`${p.nom}-${i}`} pharmacie={p} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
