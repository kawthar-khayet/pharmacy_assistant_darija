import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, transcrire } from './api'

// Saisie vocale : le navigateur enregistre, l'API DwaTalk transcrit (Whisper,
// en local cote serveur -- voir api/parole.py).
//
// On enregistre plutot que d'utiliser la dictee integree du navigateur : celle-ci
// n'existe pas sous Firefox, envoie la voix aux serveurs de l'editeur du
// navigateur, et ne laisse aucun composant vocal dans le projet lui-meme.
//
// Le texte transcrit est rendu au champ de saisie sans etre envoye : Whisper
// ne connait la darija qu'approximativement, l'utilisateur doit pouvoir relire
// et corriger avant de poser sa question.

// Garde-fou : un enregistrement oublie ne doit pas tourner indefiniment.
// Aligne sur la limite de l'API (60 s), avec de la marge.
const DUREE_MAX_MS = 45_000

export const voixDisponible =
  typeof window !== 'undefined' &&
  Boolean(navigator.mediaDevices?.getUserMedia) &&
  typeof window.MediaRecorder !== 'undefined'

/** etat : 'repos' | 'ecoute' | 'transcription' */
export function useDictee({ onTexte } = {}) {
  const [etat, setEtat] = useState('repos')
  const [erreur, setErreur] = useState(null)

  const enregistreurRef = useRef(null)
  const fluxRef = useRef(null)
  const morceauxRef = useRef([])
  const minuterieRef = useRef(null)
  // garde la derniere callback sans relancer d'effet a chaque rendu ; mise a
  // jour dans un effet et non pendant le rendu, que React peut rejouer
  const onTexteRef = useRef(onTexte)
  useEffect(() => {
    onTexteRef.current = onTexte
  })

  const libererMicro = useCallback(() => {
    clearTimeout(minuterieRef.current)
    // couper les pistes eteint le voyant "micro actif" du navigateur : sans ca
    // il resterait allume apres l'enregistrement, ce qui inquiete a juste titre
    fluxRef.current?.getTracks().forEach((piste) => piste.stop())
    fluxRef.current = null
  }, [])

  // a la fermeture de la page ou au changement d'ecran
  useEffect(
    () => () => {
      if (enregistreurRef.current?.state === 'recording') enregistreurRef.current.stop()
      libererMicro()
    },
    [libererMicro],
  )

  const demarrer = useCallback(async () => {
    setErreur(null)
    let flux
    try {
      flux = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e) {
      setErreur(
        e?.name === 'NotAllowedError'
          ? "Acces au micro refuse. Autorise-le dans les reglages du navigateur."
          : "Aucun micro utilisable n'a ete trouve.",
      )
      return
    }

    fluxRef.current = flux
    morceauxRef.current = []
    const enregistreur = new MediaRecorder(flux)
    enregistreurRef.current = enregistreur

    enregistreur.ondataavailable = (e) => {
      if (e.data.size > 0) morceauxRef.current.push(e.data)
    }

    enregistreur.onstop = async () => {
      libererMicro()
      const audio = new Blob(morceauxRef.current, { type: enregistreur.mimeType || 'audio/webm' })
      morceauxRef.current = []
      if (audio.size === 0) {
        setEtat('repos')
        return
      }

      setEtat('transcription')
      try {
        const { texte } = await transcrire(audio)
        onTexteRef.current?.(texte)
      } catch (err) {
        setErreur(err instanceof ApiError ? err.message : "La transcription n'a pas abouti.")
      } finally {
        setEtat('repos')
      }
    }

    enregistreur.start()
    setEtat('ecoute')
    minuterieRef.current = setTimeout(() => {
      if (enregistreur.state === 'recording') enregistreur.stop()
    }, DUREE_MAX_MS)
  }, [libererMicro])

  const basculer = useCallback(() => {
    if (etat === 'transcription') return
    if (etat === 'ecoute') {
      enregistreurRef.current?.stop()
      return
    }
    demarrer()
  }, [etat, demarrer])

  return { etat, erreur, basculer, disponible: voixDisponible }
}
