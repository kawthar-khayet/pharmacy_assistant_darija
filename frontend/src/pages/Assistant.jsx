import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import ChatMessage from '../components/ChatMessage'
import SearchBar from '../components/SearchBar'
import SuggestionCard from '../components/SuggestionCard'
import { IndicateurFrappe } from '../components/LoadingState'
import { Signe } from '../components/Logo'
import { Disponible } from '../components/Header'
import EmergencyBanner from '../components/EmergencyBanner'
import LanguageSelector from '../components/LanguageSelector'
import { ApiError, envoyerMessage } from '../lib/api'
import { titrer } from '../lib/conversations'
import { LANGUE_PAR_DEFAUT, t } from '../lib/langues'
import { useConversations } from '../lib/conversationsContexte'
import { useLanguage } from '../lib/languageContexte'

export default function Assistant() {
  const { courante, majConversation, demarrer } = useConversations()
  const { t: trad, estArabe, langue } = useLanguage()
  const [saisie, setSaisie] = useState('')
  const [enCours, setEnCours] = useState(false)

  const filRef = useRef(null)
  const location = useLocation()
  const naviguer = useNavigate()
  const { tours, attendLieu } = courante

  const langueQuestion = [...tours].reverse().find((x) => x.meta)?.meta.langue ?? langue ?? LANGUE_PAR_DEFAUT

  const pistes = [
    { icone: 'monnaie', texte: trad('piste_prix') },
    { icone: 'pilule', texte: trad('piste_role') },
    { icone: 'lieu', texte: trad('piste_lieu') },
    { icone: 'lune', texte: trad('piste_garde') },
    { icone: 'bouclier', texte: trad('piste_remboursement') },
  ]

  useEffect(() => {
    const fil = filRef.current
    if (fil) fil.scrollTop = fil.scrollHeight
  }, [tours, enCours])

  useEffect(() => {
    setSaisie('')
  }, [courante.id])

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
            text: err instanceof ApiError ? err.message : 'Une erreur inattendue est survenue.',
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
    <div className="chat" dir={estArabe ? 'rtl' : 'ltr'}>
      <header className="chat-tete">
        <div className="chat-identite">
          <span className="avatar" aria-hidden="true">
            <Signe />
          </span>
          <div>
            <h2>{trad('chat_titre')}</h2>
            <p>{trad('chat_role')}</p>
          </div>
        </div>
        <div className="chat-tete-actions">
          <EmergencyBanner />
          <div className="chat-langue-mobile">
            <LanguageSelector compact />
          </div>
          <Disponible />
        </div>
      </header>

      <div className="chat-fil" ref={filRef}>
        <div className="chat-fil-inner">
          {tours.map((tour, i) => (
            <ChatMessage key={i} tour={tour} />
          ))}

          {enCours && (
            <div className="tour">
              <span className="avatar" aria-hidden="true">
                <Signe />
              </span>
              <div className="bulle">
                <IndicateurFrappe />
              </div>
            </div>
          )}

          {debut && !enCours && (
            <div className="puces" style={{ justifyContent: 'flex-start', paddingRight: estArabe ? 41 : 0, paddingLeft: estArabe ? 0 : 41 }}>
              {pistes.map((p) => (
                <SuggestionCard
                  key={p.texte}
                  icone={p.icone}
                  texte={p.texte}
                  onClick={(texte) => envoyer(texte)}
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
            onValider={(texte) => envoyer(texte)}
            enCours={enCours}
            placeholder={attendLieu ? t(langueQuestion, 'saisie_lieu') : trad('chat_placeholder_normal')}
            aide={
              attendLieu
                ? t(langueQuestion, 'aide_lieu')
                : trad('chat_disclaimer')
            }
          />
        </div>
      </div>
    </div>
  )
}
