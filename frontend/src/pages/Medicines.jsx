import { useEffect, useRef, useState } from 'react'
import Header from '../components/Header'
import SearchBar from '../components/SearchBar'
import MedicineCard from '../components/MedicineCard'
import MedicineDetails from '../components/MedicineDetails'
import LoadingState from '../components/LoadingState'
import SafetyNotice from '../components/SafetyNotice'
import { ApiError, chercherMedicaments } from '../lib/api'

// Medicaments courants au Maroc, verifies presents dans la base de reference.
const COURANTS = ['Doliprane', 'Panadol', 'Efferalgan', 'Spasfon', 'Smecta', 'Amoxicilline']

export default function Medicines() {
  const [requete, setRequete] = useState('')
  const [resultats, setResultats] = useState(null)
  const [enCours, setEnCours] = useState(false)
  const [erreur, setErreur] = useState(null)
  const [ouvert, setOuvert] = useState(null)

  // Annule la recherche precedente quand une nouvelle part : sans ca, une
  // reponse lente peut arriver apres une plus recente et ecraser l'affichage.
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

  return (
    <div className="page">
      <Header
        titre="Medicaments"
        sousTitre="Prix, forme et remboursement des medicaments autorises au Maroc."
      />

      <SearchBar
        valeur={requete}
        onChange={setRequete}
        onValider={chercher}
        placeholder="Rechercher un medicament…"
        aide="Ecris le nom commercial ou la molecule. Les fautes de frappe sont tolerees."
        enCours={enCours}
      />

      {!resultats && !enCours && (
        <>
          <h2 className="section-titre">Recherches frequentes</h2>
          <div className="puces" style={{ justifyContent: 'flex-start' }}>
            {COURANTS.map((nom) => (
              <button key={nom} className="puce" onClick={() => lancer(nom)}>
                <span aria-hidden="true">💊</span>
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
          <div className="vide-glyphe" aria-hidden="true">🔌</div>
          <h3>Recherche indisponible</h3>
          <p>{erreur}</p>
        </div>
      )}

      {!enCours && !erreur && resultats?.length === 0 && (
        <div className="vide" style={{ marginTop: 28 }}>
          <div className="vide-glyphe" aria-hidden="true">🔍</div>
          <h3>Aucun medicament trouve</h3>
          <p>
            Verifie l’orthographe, ou essaie la molecule plutot que le nom commercial
            (par exemple « paracetamol » au lieu de « Doliprane »).
          </p>
        </div>
      )}

      {!enCours && ouvert && (
        <div style={{ marginTop: 28 }}>
          <button className="bouton-doux" onClick={() => setOuvert(null)} style={{ marginBottom: 16 }}>
            ← Retour aux resultats
          </button>
          <MedicineDetails resultat={ouvert} />
        </div>
      )}

      {!enCours && !ouvert && resultats?.length > 0 && (
        <>
          <h2 className="section-titre">
            {resultats.length} resultat{resultats.length > 1 ? 's' : ''}
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
