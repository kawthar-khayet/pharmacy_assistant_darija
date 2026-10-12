import { NavLink } from 'react-router-dom'
import Icon from './Icon'
import { NAVIGATION } from '../lib/navigation'
import { useLanguage } from '../lib/languageContexte'

/** Sur telephone, la barre laterale laisse place a une navigation basse ergonomique :
 *  les cibles restent dans le pouce et l'ecran garde toute sa largeur pour lire. */
export default function BottomNavigation() {
  const { t } = useLanguage()

  return (
    <nav className="barre-basse" aria-label="Navigation">
      {NAVIGATION.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.exact}
          className={({ isActive }) => `onglet ${isActive ? 'onglet-actif' : ''}`}
        >
          <span className="onglet-glyphe">
            <Icon nom={item.icone} taille={20} />
          </span>
          <span className="onglet-texte">{t(item.cle)}</span>
        </NavLink>
      ))}
    </nav>
  )
}
