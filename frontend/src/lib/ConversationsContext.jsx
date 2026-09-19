import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { ecrireToutes, lireToutes, nouvelleConversation } from './conversations'

const Contexte = createContext(null)

export function ConversationsProvider({ children }) {
  // On lit le stockage une seule fois, a l'initialisation : le relire a chaque
  // rendu ecraserait la discussion en cours.
  const [conversations, setConversations] = useState(() => {
    const existantes = lireToutes()
    return existantes.length ? existantes : [nouvelleConversation()]
  })
  const [couranteId, setCouranteId] = useState(() => conversations[0].id)

  useEffect(() => {
    ecrireToutes(conversations)
  }, [conversations])

  const valeur = useMemo(() => {
    const courante =
      conversations.find((c) => c.id === couranteId) ?? conversations[0]

    return {
      conversations,
      courante,
      couranteId: courante.id,
      choisir: setCouranteId,

      // Vise une conversation par son id plutot que "la courante" : quand on
      // vient de creer une discussion, `courante` pointe encore sur la
      // precedente (le setState n'est pas encore applique), et une mise a jour
      // implicite irait ecrire dans la mauvaise.
      majConversation(id, patch) {
        setConversations((liste) =>
          liste.map((c) => (c.id === id ? { ...c, ...patch, majLe: Date.now() } : c)),
        )
      },

      majCourante(patch) {
        setConversations((liste) =>
          liste.map((c) =>
            c.id === courante.id ? { ...c, ...patch, majLe: Date.now() } : c,
          ),
        )
      },

      demarrer(tours) {
        const fraiche = nouvelleConversation()
        if (tours) Object.assign(fraiche, tours)
        setConversations((liste) => [fraiche, ...liste])
        setCouranteId(fraiche.id)
        return fraiche
      },

      supprimer(id) {
        const reste = conversations.filter((c) => c.id !== id)
        // On ne laisse jamais l'ecran sans discussion : supprimer la derniere
        // en ouvre une vierge plutot que d'afficher le vide.
        const suivantes = reste.length ? reste : [nouvelleConversation()]
        // Calcule hors de l'updater : React rejoue systematiquement les
        // updaters en StrictMode, et y declencher un autre setState creerait
        // une discussion fantome a chaque suppression.
        setConversations(suivantes)
        if (id === couranteId) setCouranteId(suivantes[0].id)
      },

      // les plus recentes en tete, sans toucher a l'ordre de stockage
      triees: [...conversations].sort((a, b) => b.majLe - a.majLe),
    }
  }, [conversations, couranteId])

  return <Contexte.Provider value={valeur}>{children}</Contexte.Provider>
}

export function useConversations() {
  const valeur = useContext(Contexte)
  if (!valeur) throw new Error('useConversations doit etre utilise dans ConversationsProvider')
  return valeur
}
