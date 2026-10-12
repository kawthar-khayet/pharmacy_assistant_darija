import Icon from './Icon'
import { t } from '../lib/langues'
import { useLanguage } from '../lib/languageContexte'

/** Rappel affiche partout ou une information medicale est presentee : DwaTalk
 *  oriente, il ne remplace ni le pharmacien ni le medecin. */
export default function SafetyNotice({ mince = false, langue }) {
  const { langue: langueContexte } = useLanguage()
  const codeLangue = langue ?? langueContexte

  return (
    <div className={`securite ${mince ? 'securite-mince' : ''}`} role="note">
      <span className="securite-glyphe" aria-hidden="true">
        <Icon nom="alerte" taille={mince ? 14 : 16} />
      </span>
      <div>
        <strong>{t(codeLangue, 'securite_titre')}</strong>
        <p dir="auto">{t(codeLangue, 'securite_texte')}</p>
      </div>
    </div>
  )
}
