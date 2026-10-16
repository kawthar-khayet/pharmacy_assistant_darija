import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Icon from '../components/Icon'
import SearchBar from '../components/SearchBar'
import MedicineCard from '../components/MedicineCard'
import MedicineDetails from '../components/MedicineDetails'
import LoadingState from '../components/LoadingState'
import SafetyNotice from '../components/SafetyNotice'
import { ApiError, chercherMedicaments } from '../lib/api'
import { useLanguage } from '../lib/languageContexte'

const COURANTS = ['Doliprane', 'Panadol', 'Efferalgan', 'Spasfon', 'Smecta', 'Amoxicilline']

export default function Medicines() {
  const { t, estArabe } = useLanguage()
  const [requete, setRequete] = useState('')
  const [resultats, setResultats] = useState(null)
  const [enCours, setEnCours] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [ouvert, setOuvert] = useState(null)

  const abandonRef = useRef(null)
  useEffect(() => () => abandonRef.current?.abort(), [])

  async function chercher(texte) {
    const q = texte.trim()
    if (!q) return

    abandonRef.current?.abort()
    const controleur = new AbortController()
    abandonRef.current = controleur

    setEnCours(true)
    setErreur(null)
    setOuvert(null)
    try {
      const data = await chercherMedicaments(q, { limit: 12, signal: controleur.signal })
      setResultats(data.resultats)
    } catch (err) {
      if (err.name === 'AbortError') return
      setErreur(err instanceof ApiError ? err.message : 'Recherche impossible pour le moment.')
      setResultats([])
    } finally {
      if (!controleur.signal.aborted) setEnCours(false)
    }
  }

  function lancer(nom) {
    setRequete(nom)
    chercher(nom)
  }

  // Recherche saisie sur la page d'accueil : on la lance a l'arrivee, une fois.
  const location = useLocation()
  const naviguer = useNavigate()
  const requeteEntrante = location.state?.requete
  const dejaLancee = useRef(null)
  useEffect(() => {
    if (!requeteEntrante || dejaLancee.current === requeteEntrante) return
    dejaLancee.current = requeteEntrante
    naviguer('.', { replace: true, state: null })
    lancer(requeteEntrante)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requeteEntrante])

  return (
    <div className="page" dir={estArabe ? 'rtl' : 'ltr'}>
      <Header
        titre={t('med_titre')}
        surtitre={t('med_surtitre')}
        icone="base"
        sousTitre={t('med_soustitre')}
      />

      <SearchBar
        valeur={requete}
        onChange={setRequete}
        onValider={chercher}
        placeholder={t('med_placeholder')}
        aide={t('med_aide')}
        enCours={enCours}
      />

      {!resultats && !enCours && (
        <>
          <h2 className="section-titre">{t('med_courants')}</h2>
          <div className="puces" style={{ justifyContent: 'flex-start' }}>
            {COURANTS.map((nom) => (
              <button key={nom} className="puce" onClick={() => lancer(nom)}>
                <Icon nom="pilule" taille={15} />
                {nom}
              </button>
            ))}
          </div>
          <div style={{ marginTop: 34 }}>
            <SafetyNotice />
          </div>
        </>
      )}

      {enCours && (
        <div style={{ marginTop: 28 }}>
          <LoadingState variante="fiches" nombre={6} />
        </div>
      )}

      {erreur && (
        <div className="vide" style={{ marginTop: 28 }}>
          <div className="vide-glyphe">
            <Icon nom="debranche" taille={24} />
          </div>
          <h3>{estArabe ? 'خدمة البحث غير متوفرة حاليا' : 'Recherche indisponible'}</h3>
          <p>{erreur}</p>
        </div>
      )}

      {!enCours && !erreur && resultats?.length === 0 && (
        <div className="vide" style={{ marginTop: 28 }}>
          <div className="vide-glyphe">
            <Icon nom="loupe" taille={24} />
          </div>
          <h3>{t('med_aucun_titre')}</h3>
          <p>{t('med_aucun_texte')}</p>
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

      {!enCours && !ouvert && resultats?.length > 0 && (
        <>
          <h2 className="section-titre">
            {resultats.length} {t('med_resultats_nb')}
          </h2>
          <div className="grille-fiches">
            {resultats.map((r, i) => (
              <MedicineCard key={`${r.nom_candidat}-${i}`} resultat={r} onOuvrir={setOuvert} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
