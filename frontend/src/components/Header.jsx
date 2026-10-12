import Icon from './Icon'
import LanguageSelector from './LanguageSelector'
import EmergencyBanner from './EmergencyBanner'
import { useLanguage } from '../lib/languageContexte'

/** En-tete de page : surtitre, titre, sous-titre, actions contextuelles et boutons d'urgence. */
export default function Header({ titre, sousTitre, surtitre, icone, aside, dirTitre = 'auto' }) {
  const { estArabe } = useLanguage()

  return (
    <header className="entete" dir={estArabe ? 'rtl' : 'ltr'}>
      <div className="entete-corps">
        {surtitre && (
          <p className="entete-surtitre">
            {icone && <Icon nom={icone} taille={14} epaisseur={2.2} />}
            {surtitre}
          </p>
        )}
        <h1 dir={dirTitre} className="entete-titre">{titre}</h1>
        {sousTitre && (
          <p className="entete-sous" dir="auto">
            {sousTitre}
          </p>
        )}
      </div>

      <div className="entete-actions">
        <EmergencyBanner />
        <div className="entete-langue-mobile">
          <LanguageSelector compact />
        </div>
        {aside}
      </div>
    </header>
  )
}

export function Disponible() {
  const { t } = useLanguage()
  return <span className="pastille-dispo">{t('chat_dispo')}</span>
}
