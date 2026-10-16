import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import Icon from './Icon'
import Logo from './Logo'
import { NAVIGATION, allerA } from '../lib/navigation'
import { useLanguage } from '../lib/languageContexte'

/** Menu de langue : un seul bouton qui affiche la langue courante, les trois
 *  choix s'ouvrent dessous. Prend moins de place que trois boutons cote a cote. */
function MenuLangue() {
  const { langue, setLangue, langues, t } = useLanguage()
  const [ouvert, setOuvert] = useState(false)
  const racine = useRef(null)
  const courante = langues.find((l) => l.code === langue)

  useEffect(() => {
    if (!ouvert) return
    function surClic(e) {
      if (!racine.current?.contains(e.target)) setOuvert(false)
    }
    function surTouche(e) {
      if (e.key === 'Escape') setOuvert(false)
    }
    document.addEventListener('mousedown', surClic)
    document.addEventListener('keydown', surTouche)
    return () => {
      document.removeEventListener('mousedown', surClic)
      document.removeEventListener('keydown', surTouche)
    }
  }, [ouvert])

  return (
    <div className="menu-langue" ref={racine}>
      <button
        type="button"
        className="menu-langue-bouton"
        onClick={() => setOuvert((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={ouvert}
        aria-label={t('nav_langue')}
      >
        <span>{courante?.libelle}</span>
        <Icon nom="chevron" taille={14} epaisseur={2.2} />
      </button>

      {ouvert && (
        <ul className="menu-langue-liste" role="listbox" aria-label={t('nav_langue')}>
          {langues.map((item) => (
            <li key={item.code} role="option" aria-selected={item.code === langue}>
              <button
                type="button"
                className={item.code === langue ? 'menu-langue-actif' : ''}
                onClick={() => {
                  setLangue(item.code)
                  setOuvert(false)
                }}
              >
                {item.libelle}
                {item.code === langue && <Icon nom="valide" taille={14} epaisseur={2.4} />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** Barre du haut : les rubriques sont les memes sur toutes les pages, accueil
 *  compris ; le logo ramene a l'accueil. */
export default function TopBar() {
  const { t, estArabe } = useLanguage()
  const { pathname } = useLocation()
  const surAccueil = pathname === '/'
  const rubriques = NAVIGATION.filter((item) => item.to !== '/' && item.to !== '/historique')

  return (
    <header className="barre-haut" dir={estArabe ? 'rtl' : 'ltr'}>
      <div className="barre-haut-in">
        <Link to="/" className="barre-haut-marque" aria-label="DwaTalk" onClick={() => allerA('haut')}>
          <Logo />
        </Link>

        <nav className="barre-haut-liens" aria-label="Navigation principale">
          {rubriques.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              className={({ isActive }) => `lien-haut ${isActive ? 'lien-haut-actif' : ''}`}
            >
              {t(item.cle)}
            </NavLink>
          ))}
        </nav>

        <div className="barre-haut-actions">
          <NavLink
            to="/historique"
            className={({ isActive }) => `icone-haut ${isActive ? 'icone-haut-actif' : ''}`}
            aria-label={t('nav_historique')}
            title={t('nav_historique')}
          >
            <Icon nom="historique" />
          </NavLink>
          <NavLink
            to="/parametres"
            className={({ isActive }) => `icone-haut ${isActive ? 'icone-haut-actif' : ''}`}
            aria-label={t('nav_parametres')}
            title={t('nav_parametres')}
          >
            <Icon nom="reglages" />
          </NavLink>
          <MenuLangue />
          {surAccueil && (
            <Link to="/assistant" className="btn-plein btn-compact">
              {t('cta_essayer')}
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}
