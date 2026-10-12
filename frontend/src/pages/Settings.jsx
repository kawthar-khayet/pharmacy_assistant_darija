import Header from '../components/Header'
import SafetyNotice from '../components/SafetyNotice'
import LanguageSelector from '../components/LanguageSelector'
import { API_BASE } from '../lib/api'
import { voixDisponible } from '../lib/voix'
import { useConversations } from '../lib/conversationsContexte'
import { useLanguage } from '../lib/languageContexte'

export default function Settings() {
  const { conversations, supprimer } = useConversations()
  const { t, estArabe } = useLanguage()

  function toutEffacer() {
    if (!window.confirm(t('param_effacer_confirm'))) return
    conversations.forEach((c) => supprimer(c.id))
  }

  return (
    <div className="page page-etroite" dir={estArabe ? 'rtl' : 'ltr'}>
      <Header
        titre={t('param_titre')}
        sousTitre={t('param_soustitre')}
      />

      <div className="liste">
        <div className="reglage">
          <div>
            <h4>{t('param_langue_titre')}</h4>
            <p>{t('param_langue_desc')}</p>
          </div>
          <div style={{ minWidth: 200 }}>
            <LanguageSelector />
          </div>
        </div>

        <div className="reglage">
          <div>
            <h4>{t('param_voix_titre')}</h4>
            <p>
              {voixDisponible
                ? t('param_voix_desc_active')
                : t('param_voix_desc_inactif')}
            </p>
          </div>
          <span className={`marqueur ${voixDisponible ? 'marqueur-ok' : ''}`}>
            {voixDisponible ? t('param_supporte') : t('param_non_supporte')}
          </span>
        </div>

        <div className="reglage">
          <div>
            <h4>{t('param_histo_titre')}</h4>
            <p>
              {conversations.length} {t('param_histo_desc')}
            </p>
          </div>
          <button className="bouton-doux bouton-danger" onClick={toutEffacer}>
            {t('param_tout_effacer')}
          </button>
        </div>

        <div className="reglage">
          <div>
            <h4>{t('param_api_titre')}</h4>
            <p>{t('param_api_desc')} {API_BASE}.</p>
          </div>
          <span className="marqueur marqueur-bleu">API REST</span>
        </div>
      </div>

      <div style={{ marginTop: 28 }}>
        <SafetyNotice />
      </div>
    </div>
  )
}
