import { NavLink } from 'react-router-dom'
import Icon from './Icon'
import Logo from './Logo'
import { NAVIGATION } from '../lib/navigation'

export default function Sidebar() {
  return (
    <aside className="flanc">
      <div className="flanc-marque">
        <Logo />
      </div>

      <p className="flanc-legende">Menu</p>
      <nav className="flanc-groupe" aria-label="Navigation principale">
        {NAVIGATION.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            className={({ isActive }) => `lien ${isActive ? 'lien-actif' : ''}`}
          >
            <span className="lien-glyphe">
              <Icon nom={item.icone} />
            </span>
            {item.libelle}
          </NavLink>
        ))}
      </nav>

      <div className="flanc-bas">
        <div className="flanc-carte">
          <div className="flanc-carte-titre">
            <Icon nom="bouclier" taille={16} />
            Donnees officielles
          </div>
          <p>Medicaments AMMPS, prix et remboursements CNOPS et CNSS.</p>
        </div>

        <NavLink
          to="/parametres"
          className={({ isActive }) => `lien ${isActive ? 'lien-actif' : ''}`}
        >
          <span className="lien-glyphe">
            <Icon nom="reglages" />
          </span>
          Parametres
        </NavLink>
        <p className="flanc-note">
          DwaTalk oriente et informe. Il ne remplace pas un pharmacien.
        </p>
      </div>
    </aside>
  )
}
