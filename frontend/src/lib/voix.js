import { useCallback, useEffect, useRef, useState } from 'react'

// Dictee vocale via l'API Web Speech du navigateur.
//
// Elle est native a Chrome/Edge/Safari et reconnait l'arabe marocain, donc elle
// donne une vraie saisie vocale sans rien ajouter cote serveur. Elle est en
// revanche absente de Firefox : le bouton se masque alors de lui-meme plutot
// que d'afficher une commande qui ne repondrait pas.
//
// La transcription Whisper cote API reste la voie a suivre pour ne plus dependre
// du navigateur et traiter la darija avec un modele choisi ; celle-ci sert en
// attendant, et l'interface n'aura pas a changer le jour ou on bascule.

const Reconnaissance =
  typeof window !== 'undefined' &&
  (window.SpeechRecognition || window.webkitSpeechRecognition)

export const dicteeDisponible = Boolean(Reconnaissance)

export function useDictee({ langue = 'ar-MA', onTexte } = {}) {
  const [ecoute, setEcoute] = useState(false)
  const [erreur, setErreur] = useState(null)
  const moteurRef = useRef(null)
  // garde la derniere callback sans relancer l'effet a chaque rendu
  const onTexteRef = useRef(onTexte)
  onTexteRef.current = onTexte

  useEffect(() => {
    if (!Reconnaissance) return undefined

    const moteur = new Reconnaissance()
    moteur.lang = langue
    moteur.interimResults = false
    moteur.maxAlternatives = 1

    moteur.onresult = (e) => {
      const texte = Array.from(e.results)
        .map((r) => r[0].transcript)
        .join(' ')
        .trim()
      if (texte) onTexteRef.current?.(texte)
    }
    moteur.onerror = (e) => {
      setEcoute(false)
      setErreur(
        e.error === 'not-allowed'
          ? "Acces au micro refuse. Autorise-le dans les reglages du navigateur."
          : "La dictee n'a pas abouti. Reessaie ou ecris ta question.",
      )
    }
    moteur.onend = () => setEcoute(false)

    moteurRef.current = moteur
    return () => {
      moteur.onresult = null
      moteur.onerror = null
      moteur.onend = null
      try {
        moteur.abort()
      } catch {
        // deja arrete : rien a faire
      }
    }
  }, [langue])

  const basculer = useCallback(() => {
    const moteur = moteurRef.current
    if (!moteur) return
    setErreur(null)
    if (ecoute) {
      moteur.stop()
      setEcoute(false)
      return
    }
    try {
      moteur.start()
      setEcoute(true)
    } catch {
      // start() leve si une session tourne deja : on se resynchronise
      setEcoute(false)
    }
  }, [ecoute])

  return { ecoute, erreur, basculer, disponible: dicteeDisponible }
}
