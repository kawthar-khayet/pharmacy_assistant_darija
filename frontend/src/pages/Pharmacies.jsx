import { useEffect, useRef, useState } from 'react'
import Header from '../components/Header'
import SearchBar from '../components/SearchBar'
import PharmacyCard from '../components/PharmacyCard'
import LoadingState from '../components/LoadingState'
import { ApiError, chercherPharmacies } from '../lib/api'
import { coordonneesVille, urlPlan } from '../lib/villes'

const VILLES_COURANTES = ['Casablanca', 'Rabat', 'Marrakech', 'Tanger', 'Agadir', 'Fes']

function Plan({ lieu }) {
  const coords = coordonneesVille(lieu)

  return (
    <div className="carte-plan">
      <div className="carte-plan-toile filigrane">
        {coords ? (
          <iframe
            title={`Plan de ${lieu}`}
            src={urlPlan(coords)}
            style={{ width: '100%', height: '100%', border: 0, display: 'block' }}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
          />
        ) : (
          <div
            style={{
              height: '100%',
              display: 'grid',
              placeItems: 'center',
              padding: 28,
              textAlign: 'center',
              color: 'var(--encre-douce)',
              fontSize: '.88rem',
            }}
          >
            <div>
              <div style={{ fontSize: '1.7rem' }} aria-hidden="true">🗺️</div>
              <p style={{ marginTop: 10 }}>
                {lieu
                  ? `Je ne sais pas encore situer « ${lieu} » sur le plan.`
                  : 'Indique une ville pour afficher le plan.'}
              </p>
            </div>
          </div>
        )}
      </div>
      <p className="carte-plan-pied">
        Le plan situe la ville. Les positions exactes des pharmacies ne sont pas
        fournies par notre source — utilise le bouton d’itineraire sur chaque fiche.
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

  function localiser() {
    // On ne demande pas la position GPS : sans coordonnees cote annuaire, elle
    // ne servirait a rien. On invite plutot a nommer le quartier, ce que
    // l'annuaire sait vraiment exploiter.
    setRequete('')
    document.querySelector('.champ textarea')?.focus()
  }

  return (
    <div className="page">
      <Header
        titre="Pharmacies"
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
        <button className="puce" onClick={localiser}>
          <span aria-hidden="true">🎯</span>
          Preciser mon quartier
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
            <span aria-hidden="true">📍</span>
            {v}
          </button>
        ))}
      </div>

      <div className="pharma-plan" style={{ marginTop: 30 }}>
        <div>
          {enCours && <LoadingState variante="liste" nombre={4} />}

          {erreur && !enCours && (
            <div className="vide">
              <div className="vide-glyphe" aria-hidden="true">🔌</div>
              <h3>Recherche indisponible</h3>
              <p>{erreur}</p>
            </div>
          )}

          {!enCours && !erreur && resultats === null && (
            <div className="vide">
              <div className="vide-glyphe" aria-hidden="true">📍</div>
              <h3>Ou es-tu ?</h3>
              <p>
                Indique ta ville ou ton quartier pour voir les pharmacies
                repertoriees autour de toi.
              </p>
            </div>
          )}

          {!enCours && !erreur && resultats?.length === 0 && (
            <div className="vide">
              <div className="vide-glyphe" aria-hidden="true">🤔</div>
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
                {resultats.length} pharmacie{resultats.length > 1 ? 's' : ''} a {lieu}
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

        <Plan lieu={lieu} />
      </div>
    </div>
  )
}
