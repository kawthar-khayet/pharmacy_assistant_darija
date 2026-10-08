import Icon from './Icon'
import { LANGUE_PAR_DEFAUT, t } from '../lib/langues'

/** Rappel affiche partout ou une information medicale est presentee : DwaTalk
 *  oriente, il ne remplace ni le pharmacien ni le medecin. */
export default function SafetyNotice({ mince = false, langue = LANGUE_PAR_DEFAUT }) {
  return (
    <div className={`securite ${mince ? 'securite-mince' : ''}`} role="note">
      <span className="securite-glyphe">
        <Icon nom="alerte" taille={mince ? 14 : 16} />
      </span>
      <div>
        <strong>{t(langue, 'securite_titre')}</strong>
        <p>{t(langue, 'securite_texte')}</p>
      </div>
    </div>
  )
}
