import { NavLink } from 'react-router-dom'
import Logo from './Logo'

export const NAVIGATION = [
  { to: '/', glyphe: '🏠', libelle: 'Accueil', exact: true },
  { to: '/assistant', glyphe: '💬', libelle: 'Assistant' },
  { to: '/medicaments', glyphe: '💊', libelle: 'Medicaments' },
  { to: '/pharmacies', glyphe: '📍', libelle: 'Pharmacies' },
  { to: '/historique', glyphe: '🕘', libelle: 'Historique' },
]

export default function Sidebar() {
  return (
    <aside className="flanc">
      <div className="flanc-marque">
        <Logo />
      </div>

      <nav className="flanc-groupe" aria-label="Navigation principale">
        {NAVIGATION.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            className={({ isActive }) => `lien ${isActive ? 'lien-actif' : ''}`}
          >
            <span className="lien-glyphe" aria-hidden="true">{item.glyphe}</span>
            {item.libelle}
          </NavLink>
        ))}
      </nav>

      <div className="flanc-bas">
        <NavLink
          to="/parametres"
          className={({ isActive }) => `lien ${isActive ? 'lien-actif' : ''}`}
        >
          <span className="lien-glyphe" aria-hidden="true">⚙️</span>
          Parametres
        </NavLink>
        <p className="flanc-note">
          DwaTalk oriente et informe. Il ne remplace pas un pharmacien.
        </p>
      </div>
    </aside>
  )
}
