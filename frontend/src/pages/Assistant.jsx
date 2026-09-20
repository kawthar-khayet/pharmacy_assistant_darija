import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import ChatMessage from '../components/ChatMessage'
import SearchBar from '../components/SearchBar'
import SuggestionCard from '../components/SuggestionCard'
import { IndicateurFrappe } from '../components/LoadingState'
import { Khatim } from '../components/Logo'
import { Disponible } from '../components/Header'
import { ApiError, envoyerMessage } from '../lib/api'
import { titrer } from '../lib/conversations'
import { useConversations } from '../lib/conversationsContexte'

const PISTES = [
  { glyphe: '💊', texte: 'Wach kayn doliprane 1g?' },
  { glyphe: '💰', texte: 'Chhal taman panadol?' },
  { glyphe: '🔁', texte: 'Kayn chi dwa bhal doliprane rkhis?' },
  { glyphe: '📍', texte: 'Fin kayna sidalia f Maarif?' },
  { glyphe: '🕐', texte: 'شحال تمن دوليبران؟' },
]

export default function Assistant() {
  const { courante, majConversation, demarrer } = useConversations()
  const [saisie, setSaisie] = useState('')
  const [enCours, setEnCours] = useState(false)

  const filRef = useRef(null)
  const location = useLocation()
  const naviguer = useNavigate()
  const { tours, attendLieu } = courante

  // colle le fil en bas a chaque nouveau tour
  useEffect(() => {
    const fil = filRef.current
    if (fil) fil.scrollTop = fil.scrollHeight
  }, [tours, enCours])

  useEffect(() => {
    setSaisie('')
  }, [courante.id])

  // Question posee depuis l'accueil : on ouvre une discussion neuve et on
  // l'envoie une seule fois. Le garde par ref est indispensable -- React
  // rejoue les effets en StrictMode, ce qui creerait sinon deux discussions
  // et deux appels au modele pour une seule question.
  const questionEntrante = location.state?.question
  const dejaEnvoyee = useRef(null)
  useEffect(() => {
    if (!questionEntrante || dejaEnvoyee.current === questionEntrante) return
    dejaEnvoyee.current = questionEntrante
    naviguer('.', { replace: true, state: null })
    const fraiche = demarrer()
    envoyer(questionEntrante, fraiche)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionEntrante])

  async function envoyer(texte, cible) {
    const message = texte.trim()
    if (!message || enCours) return

    const conv = cible ?? courante
    const avecMoi = [...conv.tours, { role: 'moi', text: message }]
    majConversation(conv.id, { tours: avecMoi, titre: titrer(avecMoi) })
    setSaisie('')
    setEnCours(true)

    try {
      const data = await envoyerMessage(message, conv.sessionId)
      majConversation(conv.id, {
        tours: [...avecMoi, { role: 'bot', text: data.reply, meta: data }],
        titre: titrer(avecMoi),
        sessionId: data.session_id,
        attendLieu: Boolean(data.awaiting_localisation),
      })
    } catch (err) {
      majConversation(conv.id, {
        tours: [
          ...avecMoi,
          {
            role: 'erreur',
            text: err instanceof ApiError ? err.message : "Une erreur inattendue s'est produite.",
          },
        ],
        titre: titrer(avecMoi),
      })
    } finally {
      setEnCours(false)
    }
  }

  const debut = tours.length === 1

  return (
    <div className="chat">
      <header className="chat-tete">
        <div className="chat-identite">
          <span className="avatar" aria-hidden="true">
            <Khatim />
          </span>
          <div>
            <h2>DwaTalk</h2>
            <p>Assistant pharmacie</p>
          </div>
        </div>
        <Disponible />
      </header>

      <div className="chat-fil" ref={filRef}>
        <div className="chat-fil-inner">
          {tours.map((tour, i) => (
            <ChatMessage key={i} tour={tour} />
          ))}

          {enCours && (
            <div className="tour">
              <span className="avatar" aria-hidden="true">
                <Khatim />
              </span>
              <div className="bulle">
                <IndicateurFrappe />
              </div>
            </div>
          )}

          {debut && !enCours && (
            <div className="puces" style={{ justifyContent: 'flex-start', paddingLeft: 41 }}>
              {PISTES.map((p) => (
                <SuggestionCard
                  key={p.texte}
                  glyphe={p.glyphe}
                  texte={p.texte}
                  onClick={(t) => envoyer(t)}
                  disabled={enCours}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="chat-socle">
        <div className="chat-socle-inner">
          <SearchBar
            valeur={saisie}
            onChange={setSaisie}
            onValider={(t) => envoyer(t)}
            enCours={enCours}
            placeholder={attendLieu ? 'Ta ville ou ton quartier…' : 'Ktebli soualek…'}
            aide={
              attendLieu
                ? 'DwaTalk attend ta ville ou ton quartier pour te proposer des pharmacies.'
                : "DwaTalk peut se tromper. Verifie aupres d'un pharmacien."
            }
          />
        </div>
      </div>
    </div>
  )
}
