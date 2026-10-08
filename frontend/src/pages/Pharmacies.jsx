import { useEffect, useRef, useState } from 'react'
import Header from '../components/Header'
import Icon from '../components/Icon'
import SearchBar from '../components/SearchBar'
import PharmacyCard from '../components/PharmacyCard'
import LoadingState from '../components/LoadingState'
import { ApiError, chercherPharmacies, positionActuelle } from '../lib/api'
import { coordonneesVille, urlPlan, urlPlanPoint } from '../lib/villes'

const VILLES_COURANTES = ['Casablanca', 'Rabat', 'Marrakech', 'Tanger', 'Agadir', 'Fes']

function Plan({ lieu, position, resultats }) {
  // Une officine dont la position est exacte peut porter un marqueur. Faute de
  // quoi on se rabat sur le centre de la ville, et le pied de carte dit que
  // c'est un reperage de secteur, pas une adresse.
  const exactes = (resultats ?? []).filter((p) => p.precision_gps === 'exacte')
  const point = position ?? (exactes.length ? { lat: exactes[0].latitude, lon: exactes[0].longitude } : null)
  const coords = point ? [point.lat, point.lon] : coordonneesVille(lieu)
  const centreSurOfficine = Boolean(point)

  return (
    <div className="carte-plan">
      <div className="carte-plan-toile filigrane">
        {coords ? (
          <iframe
            title={centreSurOfficine ? 'Plan autour de la position' : `Plan de ${lieu}`}
            src={centreSurOfficine ? urlPlanPoint(coords[0], coords[1]) : urlPlan(coords)}
            style={{ width: '100%', height: '100%', border: 0, display: 'block' }}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
        ) : (
          <div className="carte-plan-vide">
            <div>
              <div className="vide-glyphe">
                <Icon nom="plan" taille={24} />
              </div>
              <p style={{ marginTop: 10 }}>
                {lieu
                  ? `Je ne sais pas encore situer « ${lieu} » sur le plan.`
                  : 'Indique une ville ou partage ta position pour afficher le plan.'}
              </p>
            </div>
          </div>
        )}
      </div>
      <p className="carte-plan-pied">
        <Icon nom="question" taille={14} />
        <span>
          {exactes.length > 0
            ? `${exactes.length} pharmacie${exactes.length > 1 ? 's' : ''} sur ${(resultats ?? []).length} ${exactes.length > 1 ? 'ont' : 'a'} une position exacte. Les autres ne sont situees qu'au quartier ou a la ville.`
            : "Le plan situe le secteur. Les positions exactes ne sont pas connues pour ces pharmacies — utilise le bouton d'itineraire sur chaque fiche."}
        </span>
      </p>
    </div>
  )
}

export default function Pharmacies() {
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
      // L'API accepte un nom et/ou un lieu. Une saisie libre est d'abord
      // tentee comme lieu, ce qui est le cas d'usage courant ("Maarif").
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
    // L'annuaire a maintenant des coordonnees : la position du navigateur sert
    // vraiment a trier par distance, ce qui n'etait pas le cas avant.
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
    <div className="page">
      <Header
        titre="Pharmacies"
        surtitre="Annuaire"
        icone="lieu"
        sousTitre="Trouve une pharmacie par ville ou par quartier, et vois celles de garde."
      />

      <SearchBar
        valeur={requete}
        onChange={setRequete}
        onValider={chercher}
        placeholder="Ta ville ou ton quartier — Maarif, Agdal, Gueliz…"
        aide="Tu peux aussi chercher une pharmacie par son nom."
        enCours={enCours}
      />

      <div className="puces" style={{ justifyContent: 'flex-start' }}>
        <button className="puce" onClick={localiser} disabled={localisationEnCours}>
          <Icon nom="cible" taille={15} />
          {localisationEnCours ? 'Localisation…' : 'Autour de moi'}
        </button>
        {VILLES_COURANTES.map((v) => (
          <button
            key={v}
            className="puce"
            onClick={() => {
              setRequete(v)
              chercher(v)
            }}
          >
            <Icon nom="lieu" taille={15} />
            {v}
          </button>
        ))}
      </div>

      <div className="pharma-plan" style={{ marginTop: 30 }}>
        <div>
          {enCours && <LoadingState variante="liste" nombre={4} />}

          {erreur && !enCours && (
            <div className="vide">
              <div className="vide-glyphe">
                <Icon nom="debranche" taille={24} />
              </div>
              <h3>Recherche indisponible</h3>
              <p>{erreur}</p>
            </div>
          )}

          {!enCours && !erreur && resultats === null && (
            <div className="vide">
              <div className="vide-glyphe">
                <Icon nom="lieu" taille={24} />
              </div>
              <h3>Ou es-tu ?</h3>
              <p>
                Indique ta ville ou ton quartier pour voir les pharmacies
                repertoriees autour de toi.
              </p>
            </div>
          )}

          {!enCours && !erreur && resultats?.length === 0 && (
            <div className="vide">
              <div className="vide-glyphe">
                <Icon nom="question" taille={24} />
              </div>
              <h3>Aucune pharmacie trouvee</h3>
              <p>
                Essaie une ville plus large (« Casablanca » plutot qu’un nom de rue),
                ou verifie l’orthographe du quartier.
              </p>
            </div>
          )}

          {!enCours && resultats?.length > 0 && (
            <>
              <h2 className="section-titre" style={{ marginTop: 0 }}>
                {resultats.length} pharmacie{resultats.length > 1 ? 's' : ''}{' '}
                {position ? 'autour de toi' : `a ${lieu}`}
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

        <Plan lieu={lieu} position={position} resultats={resultats} />
      </div>
    </div>
  )
}
