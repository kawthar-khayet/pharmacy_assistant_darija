import { useEffect, useMemo, useState } from 'react'
import { LANGUE_PAR_DEFAUT, LANGUES_DISPONIBLES, estArabe, t } from './langues'
import { Contexte } from './languageContexte'

const CLE_STOCKAGE = 'dwatalk:langue'

export function LanguageProvider({ children }) {
  const [langue, setLangueState] = useState(() => {
    try {
      const sauvee = localStorage.getItem(CLE_STOCKAGE)
      if (sauvee && LANGUES_DISPONIBLES.some((l) => l.code === sauvee)) {
        return sauvee
      }
    } catch {
      // stockage inaccessible
    }
    return LANGUE_PAR_DEFAUT
  })

  useEffect(() => {
    try {
      localStorage.setItem(CLE_STOCKAGE, langue)
    } catch {
      // quota ou bloque
    }

    const rtl = estArabe(langue)
    document.documentElement.setAttribute('dir', rtl ? 'rtl' : 'ltr')
    document.documentElement.setAttribute('lang', rtl ? 'ar' : langue === 'fr' ? 'fr' : 'ary')
  }, [langue])

  const valeur = useMemo(() => {
    const rtl = estArabe(langue)
    return {
      langue,
      setLangue: setLangueState,
      estArabe: rtl,
      dir: rtl ? 'rtl' : 'ltr',
      t: (cle) => t(langue, cle),
      langues: LANGUES_DISPONIBLES,
    }
  }, [langue])

  return <Contexte.Provider value={valeur}>{children}</Contexte.Provider>
}
