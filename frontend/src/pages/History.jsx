import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import { dateLisible } from '../lib/conversations'
import { useConversations } from '../lib/ConversationsContext'

export default function History() {
  const { triees, choisir, supprimer, demarrer } = useConversations()
  const naviguer = useNavigate()

  // Une discussion ouverte mais jamais utilisee n'a rien a faire dans un
  // historique : on ne liste que celles ou quelqu'un a reellement ecrit.
  const entamees = triees.filter((c) => c.tours.some((t) => t.role === 'moi'))

  function ouvrir(id) {
    choisir(id)
    naviguer('/assistant')
  }

  return (
    <div className="page page-etroite">
      <Header
        titre="Historique"
        sousTitre="Tes discussions precedentes avec DwaTalk."
        aside={
          <button
            className="bouton-doux"
            onClick={() => {
              demarrer()
              naviguer('/assistant')
            }}
          >
            + Nouvelle discussion
          </button>
        }
      />

      {entamees.length === 0 ? (
        <div className="vide">
          <div className="vide-glyphe" aria-hidden="true">🕘</div>
          <h3>Pas encore de discussion</h3>
          <p>
            Pose ta premiere question a DwaTalk : elle apparaitra ici pour que tu
            puisses la reprendre plus tard.
          </p>
        </div>
      ) : (
        <div className="liste">
          {entamees.map((c) => (
            <div key={c.id} className="histo-item">
              <span className="histo-glyphe" aria-hidden="true">💬</span>

              <button
                className="histo-corps"
                onClick={() => ouvrir(c.id)}
                style={{ border: 0, background: 'none', textAlign: 'left', padding: 0 }}
              >
                <div className="histo-titre" dir="auto">{c.titre}</div>
                <div className="histo-date">{dateLisible(c.majLe)}</div>
              </button>

              <button
                className="histo-suppr"
                onClick={() => supprimer(c.id)}
                aria-label={`Supprimer la discussion ${c.titre}`}
                title="Supprimer"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      <p className="flanc-note" style={{ marginTop: 20, textAlign: 'center' }}>
        L’historique est conserve dans ce navigateur uniquement. Il ne quitte pas
        cet appareil et disparait si tu vides le cache.
      </p>
    </div>
  )
}
