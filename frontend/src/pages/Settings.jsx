import Header from '../components/Header'
import SafetyNotice from '../components/SafetyNotice'
import { API_BASE } from '../lib/api'
import { dicteeDisponible } from '../lib/voix'
import { useConversations } from '../lib/ConversationsContext'

export default function Settings() {
  const { conversations, supprimer } = useConversations()

  function toutEffacer() {
    if (!window.confirm('Effacer toutes tes discussions ? Cette action est definitive.')) return
    conversations.forEach((c) => supprimer(c.id))
  }

  return (
    <div className="page page-etroite">
      <Header titre="Parametres" sousTitre="Reglages de DwaTalk sur cet appareil." />

      <div className="liste">
        <div className="reglage">
          <div>
            <h4>Dictee vocale</h4>
            <p>
              {dicteeDisponible
                ? 'Disponible dans ce navigateur. Le micro reconnait l arabe marocain.'
                : "Indisponible dans ce navigateur. Essaie Chrome, Edge ou Safari."}
            </p>
          </div>
          <span className={`marqueur ${dicteeDisponible ? 'marqueur-ok' : ''}`}>
            {dicteeDisponible ? 'Active' : 'Non supporte'}
          </span>
        </div>

        <div className="reglage">
          <div>
            <h4>Historique local</h4>
            <p>
              {conversations.length} discussion{conversations.length > 1 ? 's' : ''} conservee
              {conversations.length > 1 ? 's' : ''} dans ce navigateur.
            </p>
          </div>
          <button className="bouton-doux bouton-danger" onClick={toutEffacer}>
            Tout effacer
          </button>
        </div>

        <div className="reglage">
          <div>
            <h4>Service DwaTalk</h4>
            <p>Les reponses sont produites par l API sur {API_BASE}.</p>
          </div>
          <span className="marqueur">API</span>
        </div>
      </div>

      <div style={{ marginTop: 26 }}>
        <SafetyNotice />
      </div>
    </div>
  )
}
