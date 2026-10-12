import { useEffect, useRef, useState } from 'react'
import Header from '../components/Header'
import Icon from '../components/Icon'
import SearchBar from '../components/SearchBar'
import PharmacyCard from '../components/PharmacyCard'
import LoadingState from '../components/LoadingState'
import { ApiError, chercherPharmacies, positionActuelle } from '../lib/api'
import { coordonneesVille, urlGoogleMaps, urlPlan, urlPlanPoint } from '../lib/villes'
import { useLanguage } from '../lib/languageContexte'

const VILLES_COURANTES = [
  { fr: 'Casablanca', ar: 'الدار البيضاء' },
  { fr: 'Rabat', ar: 'الرباط' },
  { fr: 'Marrakech', ar: 'مراكش' },
  { fr: 'Tanger', ar: 'طنجة' },
  { fr: 'Agadir', ar: 'أكادير' },
  { fr: 'Fes', ar: 'فاس' },
]

function Plan({ lieu, position, resultats, t, estArabe }) {
  const exactes = (resultats ?? []).filter((p) => p.precision_gps === 'exacte')
  const point = position ?? (exactes.length ? { lat: exactes[0].latitude, lon: exactes[0].longitude } : null)
  const coords = point ? [point.lat, point.lon] : coordonneesVille(lieu)
  const centreSurOfficine = Boolean(point)

  return (
    <div className="carte-plan">
      <div className="carte-plan-toile filigrane">
        {coords ? (
          <>
            <iframe
              title={centreSurOfficine ? 'Plan' : `Plan de ${lieu}`}
              src={centreSurOfficine ? urlPlanPoint(coords[0], coords[1]) : urlPlan(coords)}
              style={{ width: '100%', height: '100%', border: 0, display: 'block' }}
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
            />
            <a
              className="carte-plan-lien"
              href={urlGoogleMaps(coords[0], coords[1])}
              target="_blank"
              rel="noreferrer noopener"
            >
              <Icon nom="itineraire" taille={14} /> {t('pharma_itineraire')}
            </a>
          </>
        ) : (
          <div className="carte-plan-vide">
            <div>
              <div className="vide-glyphe">
                <Icon nom="plan" taille={24} />
              </div>
              <p style={{ marginTop: 10 }}>
                {lieu
                  ? (estArabe ? `كنقلبو على موقع « ${lieu} » فالخريطة...` : `Recherche de « ${lieu} » sur le plan…`)
                  : (estArabe ? 'كتب مدينتك ولا فعل GPS باش تطلع الخريطة.' : 'Indique une ville ou partage ta position pour afficher le plan.')}
              </p>
            </div>
          </div>
        )}
      </div>
      <p className="carte-plan-pied">
        <Icon nom="question" taille={14} />
        <span>
          {exactes.length > 0
            ? (estArabe
                ? `${exactes.length} صيدلية من أصل ${(resultats ?? []).length} عندها موقع GPS مضبوط. الباقي محدد بالحي ولا بالمدينة.`
                : `${exactes.length} pharmacie(s) sur ${(resultats ?? []).length} ont une position exacte. Les autres sont situées au quartier.`)
            : (estArabe
                ? 'الخريطة كتحدد المنطقة العامة. للموقع المضبوط استخدم زر الطريق لكل صيدلية.'
                : 'Le plan situe le secteur. Utilise le bouton d’itinéraire pour chaque officine.')}
        </span>
      </p>
    </div>
  )
}

export default function Pharmacies() {
  const { t, estArabe } = useLanguage()
  const [requete, setRequete] = useState('')
  const [lieu, setLieu] = useState('')
  const [resultats, setResultats] = useState(null)
  const [note, setNote] = useState(null)
  const [enCours, setEnCours] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [position, setPosition] = useState(null)
  const [localisationEnCours, setLocalisationEnCours] = useState(false)

  const abandonRef = useRef(null)
  useEffect(() => () => abandonRef.current?.abort(), [])

  async function chercher(texte) {
    const q = String(texte ?? '').trim()
    if (!q) return

    abandonRef.current?.abort()
    const controleur = new AbortController()
    abandonRef.current = controleur

    setEnCours(true)
    setErreur(null)
    setLieu(q)
    setPosition(null)
    try {
      const data = await chercherPharmacies({ ville: q, limit: 12, signal: controleur.signal })
      if (data.resultats.length === 0) {
        const parNom = await chercherPharmacies({ q, limit: 12, signal: controleur.signal })
        setResultats(parNom.resultats)
        setNote(parNom.note)
      } else {
        setResultats(data.resultats)
        setNote(data.note)
      }
    } catch (err) {
      if (err.name === 'AbortError') return
      setErreur(err instanceof ApiError ? err.message : 'Recherche impossible pour le moment.')
      setResultats([])
    } finally {
      if (!controleur.signal.aborted) setEnCours(false)
    }
  }

  async function localiser() {
    setLocalisationEnCours(true)
    setErreur(null)
    try {
      const point = await positionActuelle()
      setPosition(point)
      setEnCours(true)
      const data = await chercherPharmacies({ position: point, limit: 12 })
      setResultats(data.resultats)
      setNote(data.note)
    } catch (err) {
      setErreur(err.message ?? 'Position indisponible.')
    } finally {
      setLocalisationEnCours(false)
      setEnCours(false)
    }
  }

  return (
    <div className="page" dir={estArabe ? 'rtl' : 'ltr'}>
      <Header
        titre={t('pharma_titre')}
        surtitre={t('pharma_surtitre')}
        icone="lieu"
        sousTitre={t('pharma_soustitre')}
      />

      <SearchBar
        valeur={requete}
        onChange={setRequete}
        onValider={chercher}
        placeholder={t('pharma_placeholder')}
        aide={t('pharma_aide')}
        enCours={enCours}
      />

      <div className="puces" style={{ justifyContent: 'flex-start' }}>
        <button className="puce" onClick={localiser} disabled={localisationEnCours}>
          <Icon nom="cible" taille={15} />
          {localisationEnCours ? t('pharma_localisant') : t('pharma_autour_moi')}
        </button>
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

      <div className="pharma-plan" style={{ marginTop: 30 }}>
        <div>
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

          {!enCours && !erreur && resultats === null && (
            <div className="vide">
              <div className="vide-glyphe">
                <Icon nom="lieu" taille={24} />
              </div>
              <h3>{t('pharma_ou_es_tu')}</h3>
              <p>{t('pharma_ou_es_tu_desc')}</p>
            </div>
          )}

          {!enCours && !erreur && resultats?.length === 0 && (
            <div className="vide">
              <div className="vide-glyphe">
                <Icon nom="question" taille={24} />
              </div>
              <h3>{t('pharma_aucun_titre')}</h3>
              <p>{t('pharma_aucun_desc')}</p>
            </div>
          )}

          {!enCours && resultats?.length > 0 && (
            <>
              <h2 className="section-titre" style={{ marginTop: 0 }}>
                {resultats.length} {t('pharma_titre')}{' '}
                {position ? t('pharma_autour_de_toi') : (estArabe ? `فـ ${lieu}` : `à ${lieu}`)}
              </h2>
              {note && (
                <p
                  style={{
                    margin: '-8px 0 14px',
                    fontSize: '.84rem',
                    color: 'var(--encre-douce)',
                  }}
                >
                  {note}
                </p>
              )}
              <div className="liste">
                {resultats.map((p, i) => (
                  <PharmacyCard key={`${p.nom}-${i}`} pharmacie={p} />
                ))}
              </div>
            </>
          )}
        </div>

        <Plan lieu={lieu} position={position} resultats={resultats} t={t} estArabe={estArabe} />
      </div>
    </div>
  )
}
