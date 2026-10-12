import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Icon from '../components/Icon'
import { dateLisible } from '../lib/conversations'
import { useConversations } from '../lib/conversationsContexte'
import { useLanguage } from '../lib/languageContexte'

export default function History() {
  const { triees, choisir, supprimer, demarrer } = useConversations()
  const { t, langue, estArabe } = useLanguage()
  const naviguer = useNavigate()

  const entamees = triees.filter((c) => c.tours.some((t) => t.role === 'moi'))

  function ouvrir(id) {
    choisir(id)
    naviguer('/assistant')
  }

  return (
    <div className="page page-etroite" dir={estArabe ? 'rtl' : 'ltr'}>
      <Header
        titre={t('histo_titre')}
        sousTitre={t('histo_soustitre')}
        aside={
          <button
            className="bouton-doux bouton-plein"
            onClick={() => {
              demarrer()
              naviguer('/assistant')
            }}
          >
            <Icon nom="plus" taille={15} epaisseur={2.2} />
            {t('histo_nouvelle')}
          </button>
        }
      />

      {entamees.length === 0 ? (
        <div className="vide">
          <div className="vide-glyphe">
            <Icon nom="historique" taille={24} />
          </div>
          <h3>{t('histo_vide_titre')}</h3>
          <p>{t('histo_vide_desc')}</p>
        </div>
      ) : (
        <div className="liste">
          {entamees.map((c) => (
            <div key={c.id} className="histo-item">
              <span className="histo-glyphe">
                <Icon nom="message" />
              </span>

              <button
                className="histo-corps"
                onClick={() => ouvrir(c.id)}
                style={{
                  border: 0,
                  background: 'none',
                  textAlign: estArabe ? 'right' : 'left',
                  padding: 0,
                  cursor: 'pointer',
                }}
              >
                <div className="histo-titre" dir="auto">{c.titre}</div>
                <div className="histo-date">{dateLisible(c.majLe, langue)}</div>
              </button>

              <button
                className="histo-suppr"
                onClick={() => supprimer(c.id)}
                aria-label={`${t('histo_supprimer')} ${c.titre}`}
                title={t('histo_supprimer')}
              >
                <Icon nom="croix" taille={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      <p className="flanc-note" style={{ marginTop: 24, textAlign: 'center' }}>
        {t('histo_local_note')}
      </p>
    </div>
  )
}
