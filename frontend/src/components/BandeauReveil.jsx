import { useEffect, useState } from 'react'
import { surDemarrage } from '../lib/api'
import { useLanguage } from '../lib/languageContexte'

/** Bandeau visible pendant le reveil de l'API (Azure l'eteint sans visite). */
export default function BandeauReveil() {
  const { t } = useLanguage()
  const [visible, setVisible] = useState(false)

  useEffect(() => surDemarrage(setVisible), [])

  if (!visible) return null
  return (
    <div className="bandeau-reveil" role="status">
      <span className="bandeau-reveil-rond" aria-hidden="true" />
      {t('api_demarrage')}
    </div>
  )
}
