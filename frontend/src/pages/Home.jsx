import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import SearchBar from '../components/SearchBar'
import SuggestionCard from '../components/SuggestionCard'
import SafetyNotice from '../components/SafetyNotice'

const PISTES = [
  { glyphe: '💊', texte: 'Chno kaydir Doliprane?' },
  { glyphe: '⚠️', texte: 'Chno homa les effets secondaires?' },
  { glyphe: '🕐', texte: 'Fach nakhod had dwa?' },
  { glyphe: '📍', texte: 'Fin kayna pharmacie qriba?' },
]

const ACTIONS = [
  {
    glyphe: '💊',
    titre: 'Rechercher un medicament',
    texte: 'Trouver le prix, la forme et le remboursement d’un medicament',
    vers: '/medicaments',
  },
  {
    glyphe: '🤖',
    titre: 'Parler a DwaTalk',
    texte: 'Poser une question en darija, en arabe ou en francais',
    vers: '/assistant',
  },
  {
    glyphe: '📍',
    titre: 'Trouver une pharmacie',
    texte: 'Decouvrir les pharmacies autour de toi, et celles de garde',
    vers: '/pharmacies',
  },
]

export default function Home() {
  const [question, setQuestion] = useState('')
  const naviguer = useNavigate()

  // La question saisie ici ouvre l'Assistant et y est envoyee : l'accueil sert
  // de point d'entree, pas d'une seconde conversation parallele.
  function demander(texte) {
    const q = texte.trim()
    if (!q) return
    naviguer('/assistant', { state: { question: q } })
  }

  return (
    <div className="page">
      <section className="accueil-hero filigrane">
        <h1 className="hero-salut ar" dir="rtl" lang="ar">
          سلام <span aria-hidden="true">👋</span>
        </h1>
        <p className="hero-question ar" dir="rtl" lang="ar">
          كيفاش نقدر نعاونك اليوم؟
        </p>
        <p className="hero-sous ar" dir="rtl" lang="ar">
          سول على الأدوية، الأعراض، أو الصيدليات القريبة منك.
        </p>
      </section>

      <div style={{ maxWidth: 680, margin: '0 auto' }}>
        <SearchBar
          valeur={question}
          onChange={setQuestion}
          onValider={demander}
          placeholder="شنو بغيتي تعرف على شي دوا؟"
          aide="Ecris comme tu parles — darija, arabe ou francais."
          autoFocus
        />

        <div className="puces">
          {PISTES.map((p) => (
            <SuggestionCard key={p.texte} glyphe={p.glyphe} texte={p.texte} onClick={demander} />
          ))}
        </div>
      </div>

      <h2 className="section-titre ar" dir="rtl" lang="ar">
        شنو بغيتي دير؟
      </h2>

      <div className="grille-actions">
        {ACTIONS.map((a) => (
          <button key={a.vers} className="carte-action" onClick={() => naviguer(a.vers)}>
            <span className="carte-action-icone" aria-hidden="true">{a.glyphe}</span>
            <h3>{a.titre}</h3>
            <p>{a.texte}</p>
            <span className="carte-action-fleche">
              Ouvrir <span aria-hidden="true">→</span>
            </span>
          </button>
        ))}
      </div>

      <div style={{ marginTop: 34 }}>
        <SafetyNotice />
      </div>
    </div>
  )
}
