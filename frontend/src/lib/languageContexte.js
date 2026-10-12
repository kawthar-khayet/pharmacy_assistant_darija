import { createContext, useContext } from 'react'

export const Contexte = createContext(null)

export function useLanguage() {
  const valeur = useContext(Contexte)
  if (!valeur) throw new Error('useLanguage doit etre utilise dans LanguageProvider')
  return valeur
}
