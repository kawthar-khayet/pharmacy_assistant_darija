import { createContext, useContext } from 'react'

// Separe du Provider : un fichier .jsx qui exporte autre chose que des
// composants desactive le rechargement a chaud de Vite pour ce fichier.
export const Contexte = createContext(null)

export function useConversations() {
  const valeur = useContext(Contexte)
  if (!valeur) throw new Error('useConversations doit etre utilise dans ConversationsProvider')
  return valeur
}
