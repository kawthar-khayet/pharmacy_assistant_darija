import { NavLink } from 'react-router-dom'
import Icon from './Icon'
import Logo from './Logo'
import LanguageSelector from './LanguageSelector'
import { NAVIGATION } from '../lib/navigation'
import { useLanguage } from '../lib/languageContexte'

export default function Sidebar() {
  const { t, estArabe } = useLanguage()

  return (
    <aside className="flanc" dir={estArabe ? 'rtl' : 'ltr'}>
      <div className="flanc-marque">
        <Logo />
        <p className="flanc-sous-marque">{t('app_sous_titre')}</p>
      </div>

      <div className="flanc-langue-box">
        <LanguageSelector />
      </div>

      <p className="flanc-legende">{t('nav_menu')}</p>
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
            <span className="lien-texte">{t(item.cle)}</span>
          </NavLink>
        ))}
      </nav>

      <div className="flanc-bas">
        <div className="flanc-carte">
          <div className="flanc-carte-titre">
            <Icon nom="bouclier" taille={16} />
            {t('officiel_titre')}
          </div>
          <p>{t('officiel_desc')}</p>
        </div>

        <NavLink
          to="/parametres"
          className={({ isActive }) => `lien ${isActive ? 'lien-actif' : ''}`}
        >
          <span className="lien-glyphe">
            <Icon nom="reglages" />
          </span>
          <span className="lien-texte">{t('nav_parametres')}</span>
        </NavLink>
        <p className="flanc-note">
          {t('disclaimer_court')}
        </p>
      </div>
    </aside>
  )
}
