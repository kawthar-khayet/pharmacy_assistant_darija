import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from '../components/Icon'
import SearchBar from '../components/SearchBar'
import SuggestionCard from '../components/SuggestionCard'
import SafetyNotice from '../components/SafetyNotice'

const PISTES = [
  { icone: 'pilule', texte: 'Chno kaydir Doliprane?' },
  { icone: 'monnaie', texte: 'Chhal taman Panadol?' },
  { icone: 'lieu', texte: 'Fin kayna pharmacie qriba?' },
]

// Ce que le service sait reellement faire -- pas de chiffres ici : on n'en
// affiche aucun qui ne soit pas calcule depuis la base.
const ATOUTS = [
  { icone: 'base', titre: 'Base officielle', texte: 'AMMPS · CNOPS · CNSS', vive: true },
  { icone: 'langues', titre: '3 langues', texte: 'Darija · عربية · Français' },
  { icone: 'micro', titre: 'A voix haute', texte: 'Pose ta question en parlant' },
  { icone: 'lune', titre: 'Pharmacies proches', texte: 'Par ville et quartier' },
]

const ACTIONS = [
  {
    icone: 'pilule',
    titre: 'Rechercher un medicament',
    texte: 'Prix public, forme, dosage et taux de remboursement.',
    vers: '/medicaments',
  },
  {
    icone: 'message',
    titre: 'Parler a DwaTalk',
    texte: 'Pose ta question en darija, en arabe ou en francais.',
    vers: '/assistant',
  },
  {
    icone: 'lieu',
    titre: 'Trouver une pharmacie',
    texte: 'Les pharmacies de ton quartier, et celles de garde.',
    vers: '/pharmacies',
  },
]

const ETAPES = [
  { titre: 'Pose ta question', texte: 'Ecris ou parle comme tu le ferais au comptoir.' },
  { titre: 'DwaTalk comprend', texte: 'Il reconnait le medicament, meme mal orthographie.' },
  { titre: 'Tu recois la reponse', texte: 'Prix, remboursement, notice et pharmacies.' },
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
      <section className="hero">
        <div>
          <span className="hero-badge">
            <Icon nom="pouls" taille={14} epaisseur={2.2} />
            Assistant sante IA
          </span>
          <h1 className="hero-titre">
            Tes questions medicaments, <span>en darija.</span>
          </h1>
          <p className="hero-ar ar" dir="rtl" lang="ar">
            سول على الأدوية، الثمن، ولا الصيدليات القريبة منك.
          </p>

          <div className="hero-champ">
            <SearchBar
              valeur={question}
              onChange={setQuestion}
              onValider={demander}
              placeholder="شنو بغيتي تعرف على شي دوا؟"
              aide="Ecris comme tu parles — darija, arabe ou francais."
              autoFocus
            />
          </div>

          <div className="puces puces-sombre">
            {PISTES.map((p) => (
              <SuggestionCard key={p.texte} icone={p.icone} texte={p.texte} onClick={demander} />
            ))}
          </div>
        </div>

        <div className="hero-cote">
          {ATOUTS.map((a) => (
            <div key={a.titre} className={`tuile ${a.vive ? 'tuile-vive' : ''}`}>
              <span className="tuile-icone">
                <Icon nom={a.icone} />
              </span>
              <p className="tuile-titre">{a.titre}</p>
              <p className="tuile-texte" dir="auto">{a.texte}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="section-tete">
        <h2 className="section-titre">Nos services</h2>
        <p>Tout ce qu’il faut pour bien prendre ton traitement.</p>
      </div>

      <div className="grille-actions">
        {ACTIONS.map((a) => (
          <button key={a.vers} className="carte-action" onClick={() => naviguer(a.vers)}>
            <span className="carte-action-icone">
              <Icon nom={a.icone} taille={22} />
            </span>
            <h3>{a.titre}</h3>
            <p>{a.texte}</p>
            <span className="carte-action-fleche">
              Ouvrir <Icon nom="fleche" taille={15} epaisseur={2.2} />
            </span>
          </button>
        ))}
      </div>

      <h2 className="section-titre">Comment ca marche</h2>
      <div className="etapes">
        {ETAPES.map((e) => (
          <div key={e.titre} className="etape">
            <h3>{e.titre}</h3>
            <p>{e.texte}</p>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 32 }}>
        <SafetyNotice />
      </div>
    </div>
  )
}
