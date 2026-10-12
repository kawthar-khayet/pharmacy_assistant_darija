import { useEffect, useRef, useState } from 'react'
import Header from '../components/Header'
import Icon from '../components/Icon'
import SearchBar from '../components/SearchBar'
import PharmacyCard from '../components/PharmacyCard'
import LoadingState from '../components/LoadingState'
import { ApiError, chercherPharmaciesDeGarde, positionActuelle } from '../lib/api'

const VILLES_COURANTES = ['Casablanca', 'Rabat', 'Marrakech', 'Tanger', 'Agadir', 'Fes']
const TYPES = [
  { cle: 'tout', libelle: 'Toutes' },
  { cle: 'jour', libelle: 'De jour' },
  { cle: 'nuit', libelle: 'De nuit' },
  { cle: '24h', libelle: '24h/24' },
]

/** "2026-10-12" -> "lundi 12 octobre 2026". */
function dateLisible(iso) {
  const jour = new Date(`${iso}T12:00:00`)
  if (Number.isNaN(jour.getTime())) return iso
  return jour.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
}

/**
 * Pharmacies de garde du jour dans une ville, sans passer par le chat.
 *
 * Le tour de garde vient de Telecontact, lu par l'API a la demande : la
 * premiere recherche de la journee pour une grande ville attend la lecture du
 * site (jusqu'a une trentaine de secondes), les suivantes sont immediates.
 */
export default function Garde() {
  const [requete, setRequete] = useState('')
  const [reponse, setReponse] = useState(null)
  const [type, setType] = useState('tout')
  const [enCours, setEnCours] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [position, setPosition] = useState(null)

  const abandonRef = useRef(null)
  useEffect(() => () => abandonRef.current?.abort(), [])

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
    // La position ne remplace pas la ville (le tour de garde est publie par
    // ville) : elle sert seulement a mettre les plus proches en premier.
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
    <div className="page">
      <Header
        titre="Pharmacies de garde"
        surtitre="Aujourd'hui"
        icone="lune"
        sousTitre="Choisis ta ville pour voir les pharmacies de garde du jour : de jour, de nuit ou 24h/24."
      />

      <SearchBar
        valeur={requete}
        onChange={setRequete}
        onValider={(v) => chercher(v)}
        placeholder="Ta ville — Casablanca, Rabat, Safi…"
        aide="La premiere recherche de la journee pour une grande ville peut prendre une trentaine de secondes."
        enCours={enCours}
      />

      <div className="puces" style={{ justifyContent: 'flex-start' }}>
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

      <div style={{ marginTop: 30 }}>
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

        {!enCours && !erreur && reponse === null && (
          <div className="vide">
            <div className="vide-glyphe">
              <Icon nom="lune" taille={24} />
            </div>
            <h3>Quelle ville ?</h3>
            <p>Indique ta ville pour voir les pharmacies de garde aujourd’hui.</p>
          </div>
        )}

        {!enCours && !erreur && reponse && !reponse.connu && (
          <div className="vide">
            <div className="vide-glyphe">
              <Icon nom="question" taille={24} />
            </div>
            <h3>Tour de garde non disponible</h3>
            <p>
              {reponse.note} Essaie le nom d’une ville plus grande, ou appelle une pharmacie
              proche : elle affiche la pharmacie de garde sur sa porte.
            </p>
          </div>
        )}

        {!enCours && !erreur && reponse?.connu && (
          <>
            <h2 className="section-titre" style={{ marginTop: 0 }}>
              {toutes.length} pharmacie{toutes.length > 1 ? 's' : ''} de garde a {reponse.ville}
            </h2>
            <p style={{ margin: '-8px 0 14px', fontSize: '.84rem', color: 'var(--encre-douce)' }}>
              {dateLisible(reponse.date)} · source : {reponse.source}. Appelle avant de te deplacer.
            </p>

            <div className="puces" style={{ justifyContent: 'flex-start', marginBottom: 16 }}>
              {TYPES.map((t) => (
                <button
                  key={t.cle}
                  className="puce"
                  aria-pressed={type === t.cle}
                  style={type === t.cle ? { borderColor: 'var(--bleu)', color: 'var(--bleu)' } : undefined}
                  onClick={() => setType(t.cle)}
                >
                  {t.libelle}
                </button>
              ))}
              <button className="puce" onClick={trierParDistance}>
                <Icon nom="cible" taille={15} />
                {position ? 'Triees par distance' : 'Les plus proches de moi'}
              </button>
            </div>

            {visibles.length === 0 ? (
              <p style={{ color: 'var(--encre-douce)' }}>Aucune pharmacie de ce type aujourd’hui.</p>
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
