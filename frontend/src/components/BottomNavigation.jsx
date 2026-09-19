import { NavLink } from 'react-router-dom'
import { NAVIGATION } from './Sidebar'

/** Sur telephone, la barre laterale laisse place a une navigation basse : les
 *  cibles restent dans le pouce et l'ecran garde toute sa largeur pour lire. */
export default function BottomNavigation() {
  return (
    <nav className="barre-basse" aria-label="Navigation">
      {NAVIGATION.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.exact}
          className={({ isActive }) => `onglet ${isActive ? 'onglet-actif' : ''}`}
        >
          <span className="onglet-glyphe" aria-hidden="true">{item.glyphe}</span>
          {item.libelle}
        </NavLink>
      ))}
    </nav>
  )
}
