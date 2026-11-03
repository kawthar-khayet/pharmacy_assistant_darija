import { useEffect, useRef, useState } from 'react'
import Header from '../components/Header'
import Icon from '../components/Icon'
import MedicineCard from '../components/MedicineCard'
import MedicineDetails from '../components/MedicineDetails'
import LoadingState from '../components/LoadingState'
import SafetyNotice from '../components/SafetyNotice'
import { ApiError, reconnaitreBoite } from '../lib/api'
import { useLanguage } from '../lib/languageContexte'

const TYPES_IMAGE = ['image/jpeg', 'image/png', 'image/webp']

/** Photo d'une boite -> OCR (arabe + francais) -> les memes fiches que la
 *  page Medicaments (voir POST /reconnaissance). */
export default function Scan() {
  const { t, estArabe } = useLanguage()
  const [apercu, setApercu] = useState(null)
  const [fichier, setFichier] = useState(null)
  const [enCours, setEnCours] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [reponse, setReponse] = useState(null)
  const [ouvert, setOuvert] = useState(null)
  const [survol, setSurvol] = useState(false)

  const entreeRef = useRef(null)
  const abandonRef = useRef(null)

  // l'URL de previsualisation est a liberer explicitement, sinon elle reste
  // en memoire tant que l'onglet vit
  useEffect(() => () => apercu && URL.revokeObjectURL(apercu), [apercu])
  useEffect(() => () => abandonRef.current?.abort(), [])

  function accepter(f) {
    if (!f) return
    if (!TYPES_IMAGE.includes(f.type)) {
      setErreur(t('scan_format_invalide'))
      return
    }
    setApercu(URL.createObjectURL(f))
    setFichier(f)
    setReponse(null)
    setErreur(null)
    setOuvert(null)
    analyser(f)
  }

  async function analyser(f) {
    abandonRef.current?.abort()
    const controleur = new AbortController()
    abandonRef.current = controleur

    setEnCours(true)
    setErreur(null)
    try {
      setReponse(await reconnaitreBoite(f, { signal: controleur.signal }))
    } catch (err) {
      if (err.name === 'AbortError') return
      setErreur(err instanceof ApiError ? err.message : t('scan_erreur_titre'))
    } finally {
      if (!controleur.signal.aborted) setEnCours(false)
    }
  }

  function deposer(e) {
    e.preventDefault()
    setSurvol(false)
    accepter(e.dataTransfer.files?.[0])
  }

  const resultats = reponse?.resultats ?? []

  return (
    <div className="page" dir={estArabe ? 'rtl' : 'ltr'}>
      <Header
        titre={t('scan_titre')}
        surtitre={t('scan_surtitre')}
        icone="appareil"
        sousTitre={t('scan_soustitre')}
      />

      <input
        ref={entreeRef}
        type="file"
        accept={TYPES_IMAGE.join(',')}
        capture="environment"
        hidden
        onChange={(e) => {
          accepter(e.target.files?.[0])
          e.target.value = ''
        }}
      />

      {!apercu ? (
        <button
          type="button"
          className={`scan-zone ${survol ? 'scan-zone-survol' : ''}`}
          onClick={() => entreeRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault()
            setSurvol(true)
          }}
          onDragLeave={() => setSurvol(false)}
          onDrop={deposer}
        >
          <span className="vide-glyphe">
            <Icon nom="appareil" taille={26} />
          </span>
          <strong>{t('scan_choisir')}</strong>
          <span className="scan-zone-aide">{t('scan_formats')}</span>
          <span className="scan-zone-aide">{t('scan_conseil')}</span>
        </button>
      ) : (
        <div className="scan-apercu">
          <img src={apercu} alt="" />
          <div className="scan-apercu-actions">
            <button type="button" className="bouton-doux" onClick={() => entreeRef.current?.click()} disabled={enCours}>
              <Icon nom="appareil" taille={15} />
              {t('scan_changer')}
            </button>
            {erreur && fichier && (
              <button type="button" className="bouton-doux bouton-plein" onClick={() => analyser(fichier)}>
                <Icon nom="echange" taille={15} />
                {t('scan_analyser')}
              </button>
            )}
          </div>
        </div>
      )}

      {enCours && (
        <div style={{ marginTop: 28 }}>
          <p className="scan-statut" role="status">{t('scan_en_cours')}</p>
          <LoadingState variante="fiches" nombre={2} />
        </div>
      )}

      {erreur && !enCours && (
        <div className="vide" style={{ marginTop: 28 }} role="alert">
          <div className="vide-glyphe">
            <Icon nom="debranche" taille={24} />
          </div>
          <h3>{t('scan_erreur_titre')}</h3>
          <p>{erreur}</p>
        </div>
      )}

      {!enCours && reponse && !reponse.reussite && (
        <div className="vide" style={{ marginTop: 28 }}>
          <div className="vide-glyphe">
            <Icon nom="appareil" taille={24} />
          </div>
          <h3>{t('scan_sans_texte_titre')}</h3>
          <p>{t('scan_sans_texte')}</p>
        </div>
      )}

      {!enCours && reponse?.reussite && resultats.length === 0 && (
        <div className="vide" style={{ marginTop: 28 }}>
          <div className="vide-glyphe">
            <Icon nom="loupe" taille={24} />
          </div>
          <h3>{t('scan_aucun_titre')}</h3>
          <p>{t('scan_aucun')}</p>
        </div>
      )}

      {!enCours && ouvert && (
        <div style={{ marginTop: 28 }}>
          <button className="bouton-doux" onClick={() => setOuvert(null)} style={{ marginBottom: 16 }}>
            <Icon nom={estArabe ? 'fleche' : 'retour'} taille={15} />
            {t('med_retour')}
          </button>
          <MedicineDetails resultat={ouvert} />
        </div>
      )}

      {!enCours && !ouvert && resultats.length > 0 && (
        <>
          <h2 className="section-titre">{t('scan_reconnus')}</h2>
          <p className="scan-statut">{t('scan_verifier')}</p>
          <div className="grille-fiches">
            {resultats.map((r, i) => (
              <MedicineCard key={`${r.nom_candidat}-${i}`} resultat={r} onOuvrir={setOuvert} />
            ))}
          </div>
        </>
      )}

      {!enCours && reponse?.texte_detecte?.length > 0 && !ouvert && (
        <details className="scan-texte">
          <summary>{t('scan_texte_lu')}</summary>
          <div className="puces" style={{ justifyContent: 'flex-start' }}>
            {reponse.texte_detecte.map((ligne) => (
              <span key={ligne} className="puce" dir="auto">{ligne}</span>
            ))}
          </div>
        </details>
      )}

      {!reponse && !enCours && (
        <div style={{ marginTop: 34 }}>
          <SafetyNotice />
        </div>
      )}
    </div>
  )
}
