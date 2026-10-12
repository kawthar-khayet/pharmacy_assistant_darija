import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Icon from '../components/Icon'
import Logo from '../components/Logo'
import SearchBar from '../components/SearchBar'
import SuggestionCard from '../components/SuggestionCard'
import { useLanguage } from '../lib/languageContexte'
import { allerA } from '../lib/navigation'

// Volumes comptes dans data/clean/ le 2026-10-12 (noms distincts de
// medicaments_reference.csv, lignes et villes de pharmacies_fusion.csv).
// A recompter quand la base change.
const VOLUMES = [
  { valeur: 6719, cle: 'acc_stat_med' },
  { valeur: 8088, cle: 'acc_stat_pharma' },
  { valeur: 302, cle: 'acc_stat_villes' },
  { valeur: 3, cle: 'acc_stat_langues' },
]

const nombre = new Intl.NumberFormat('fr-FR')

/** Valeur volontairement absente : les apercus sont des illustrations, ils ne
 *  doivent afficher ni prix ni taux qu'on pourrait prendre pour reels. */
function Trait({ largeur = 44 }) {
  return <span className="acc-trait" style={{ width: largeur }} aria-hidden="true" />
}

function Titre({ debut, accent, niveau = 'h2', className = '' }) {
  const Balise = niveau
  return (
    <Balise className={`acc-titre ${className}`}>
      {debut} <em>{accent}</em>
    </Balise>
  )
}

export default function Home() {
  const [question, setQuestion] = useState('')
  const naviguer = useNavigate()
  const { t, estArabe } = useLanguage()

  const pistes = [
    { icone: 'pilule', texte: t('piste_role') },
    { icone: 'lune', texte: t('piste_garde') },
    { icone: 'bouclier', texte: t('piste_remboursement') },
  ]

  function demander(texte) {
    const q = texte.trim()
    if (!q) return
    naviguer('/assistant', { state: { question: q } })
  }

  return (
    <div className="accueil" dir={estArabe ? 'rtl' : 'ltr'}>
      {/* ------------------------------------------------ presentation */}
      <section className="acc-hero" id="haut">
        <div className="acc-in acc-hero-grille">
          <div>
            <p className="acc-surtitre">{t('acc_surtitre')}</p>
            <Titre niveau="h1" className="acc-titre-xl" debut={t('acc_titre_1')} accent={t('acc_titre_2')} />
            <p className="acc-chapeau">{t('acc_p1')}</p>
            <p className="acc-chapeau">{t('acc_p2')}</p>
            <div className="acc-boutons">
              <Link to="/assistant" className="btn-plein">
                {t('cta_essayer')}
                <Icon nom="fleche" taille={16} epaisseur={2.2} className="acc-fleche" />
              </Link>
              <button type="button" className="btn-contour" onClick={() => allerA('services')}>
                {t('acc_voir_services')}
              </button>
            </div>
          </div>

          <figure className="acc-apercu-chat" aria-label={t('acc_ap_illustration')}>
            <div className="acc-apercu-tete">
              <span className="acc-pastille" />
              <strong>DwaTalk</strong>
              <span className="acc-apercu-note">{t('acc_ap_illustration')}</span>
            </div>
            <p className="acc-bulle acc-bulle-moi" dir="auto">{t('acc_ap_q1')}</p>
            <div className="acc-bulle acc-bulle-bot">
              <strong>{t('acc_ap_nom_med')} · {t('acc_ap_dosage')}</strong>
              <div className="acc-ligne"><span>{t('acc_ap_prix')}</span><Trait /></div>
              <div className="acc-ligne"><span>CNOPS · CNSS</span><Trait largeur={30} /></div>
            </div>
            <p className="acc-bulle acc-bulle-moi acc-bulle-decalee" dir="auto">{t('acc_ap_q2')}</p>
            <span className="acc-etiquette">
              <Icon nom="bouclier" taille={14} />
              {t('acc_ap_source')}
            </span>
          </figure>
        </div>
      </section>

      {/* ----------------------------------------------------- volumes */}
      <section className="acc-volumes" aria-label={t('acc_stat_note')}>
        <div className="acc-in acc-volumes-in">
          {VOLUMES.map((v) => (
            <p key={v.cle} className="acc-volume">
              <strong>{nombre.format(v.valeur)}</strong> {t(v.cle)}
            </p>
          ))}
          <p className="acc-volumes-note">{t('acc_stat_note')}</p>
        </div>
      </section>

      {/* ------------------------------------------------------- essai */}
      <section className="acc-section acc-essai">
        <div className="acc-in acc-etroit">
          <Titre debut={t('acc_essai_titre_1')} accent={t('acc_essai_titre_2')} />
          <p className="acc-texte">{t('acc_essai_desc')}</p>
          <div className="acc-essai-champ">
            <SearchBar
              valeur={question}
              onChange={setQuestion}
              onValider={demander}
              placeholder={t('piste_prix')}
              aide={t('hero_aide')}
            />
          </div>
          <div className="puces">
            {pistes.map((p) => (
              <SuggestionCard key={p.texte} icone={p.icone} texte={p.texte} onClick={demander} />
            ))}
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------- services */}
      <section className="acc-section acc-services" id="services">
        <div className="acc-in acc-mosaique">
          <article className="acc-case acc-case-grande">
            <Icon nom="monnaie" taille={24} className="acc-icone" />
            <h3>{t('acc_g_prix_titre')}</h3>
            <p>{t('acc_g_prix_desc')}</p>
            <div className="acc-fiche-mini" aria-hidden="true">
              <div className="acc-ligne"><span>{t('prix_indicatif')}</span><Trait /></div>
              <div className="acc-ligne"><span>CNOPS</span><Trait largeur={30} /></div>
              <div className="acc-ligne"><span>CNSS</span><Trait largeur={30} /></div>
            </div>
          </article>

          <article className="acc-case acc-case-large">
            <Icon nom="bouclier" taille={24} className="acc-icone" />
            <div>
              <h3>{t('acc_g_secu_titre')}</h3>
              <p>{t('acc_g_secu_desc')}</p>
            </div>
          </article>

          <article className="acc-case">
            <Icon nom="micro" taille={24} className="acc-icone" />
            <h3>{t('acc_g_voix_titre')}</h3>
            <p>{t('acc_g_voix_desc')}</p>
          </article>

          <article className="acc-case acc-case-nuit">
            <h3 dir="auto">الدارجة · Darija · Français</h3>
            <p>{t('acc_g_langues_desc')}</p>
          </article>
        </div>
      </section>

      {/* ------------------------------------------------- medicaments */}
      <section className="acc-section acc-fond">
        <div className="acc-in acc-duo">
          <div>
            <Icon nom="loupe" taille={24} className="acc-icone" />
            <Titre debut={t('acc_med_titre_1')} accent={t('acc_med_titre_2')} />
            <p className="acc-texte">{t('acc_med_desc')}</p>
            <Link to="/medicaments" className="btn-plein">
              {t('action_med_titre')}
              <Icon nom="fleche" taille={16} epaisseur={2.2} className="acc-fleche" />
            </Link>
          </div>

          <figure className="acc-fiche" aria-label={t('acc_ap_illustration')}>
            <div className="acc-fiche-recherche">
              <Icon nom="loupe" taille={16} />
              <span>{t('acc_ap_nom_med')}</span>
            </div>
            <div className="acc-fiche-tete">
              <strong>{t('acc_ap_nom_med')}</strong>
              <span className="acc-badge">{t('acc_ap_statut')}</span>
            </div>
            <p className="acc-fiche-details">{t('acc_ap_details')}</p>
            <div className="acc-fiche-faits">
              <div><span>{t('acc_ap_prix')}</span><Trait /></div>
              <div><span>CNOPS</span><Trait largeur={30} /></div>
              <div><span>CNSS</span><Trait largeur={30} /></div>
            </div>
          </figure>
        </div>
      </section>

      {/* -------------------------------------------------- pharmacies */}
      <section className="acc-section acc-nuit">
        <div className="acc-in">
          <div className="acc-nuit-tete">
            <div>
              <Titre debut={t('acc_ph_titre_1')} accent={t('acc_ph_titre_2')} />
              <p className="acc-texte">{t('acc_ph_desc')}</p>
            </div>
            <div className="acc-boutons">
              <Link to="/pharmacies" className="btn-plein">{t('action_pharma_titre')}</Link>
              <Link to="/garde" className="btn-contour btn-contour-clair">{t('acc_ph_cta_garde')}</Link>
            </div>
          </div>

          <div className="acc-nuit-grille" aria-hidden="true">
            <svg className="acc-carte" viewBox="0 0 520 220" preserveAspectRatio="xMidYMid slice">
              <path d="M0 70 L520 44 M0 162 L520 140 M130 0 L156 220 M350 0 L328 220 M0 118 L130 112 M350 96 L520 92" />
              <circle cx="150" cy="66" r="9" />
              <circle cx="334" cy="150" r="9" />
              <circle cx="438" cy="52" r="9" className="acc-carte-garde" />
            </svg>
            <div className="acc-resultats">
              <div className="acc-resultat">
                <strong>{t('acc_ap_pharma')}</strong>
                <span>{t('acc_ap_pharma_det')}</span>
              </div>
              <div className="acc-resultat">
                <strong>
                  {t('acc_ap_garde')} <em>· {t('acc_ap_nuit')}</em>
                </strong>
                <span>{t('acc_ap_garde_det')}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------- sources */}
      <section className="acc-section" id="sources">
        <div className="acc-in">
          <Titre className="acc-centre" debut={t('acc_src_titre_1')} accent={t('acc_src_titre_2')} />
          <div className="acc-trio">
            <div>
              <Icon nom="bouclier" taille={24} className="acc-icone" />
              <h3>{t('acc_src_off_titre')}</h3>
              <p>{t('acc_src_off_desc')}</p>
            </div>
            <div>
              <Icon nom="base" taille={24} className="acc-icone" />
              <h3>{t('acc_src_base_titre')}</h3>
              <p>{t('acc_src_base_desc')}</p>
            </div>
            <div>
              <Icon nom="message" taille={24} className="acc-icone" />
              <h3>{t('acc_src_ia_titre')}</h3>
              <p>{t('acc_src_ia_desc')}</p>
            </div>
          </div>
          <p className="acc-limite" role="note">
            <Icon nom="alerte" taille={18} />
            <span>{t('acc_src_limite')}</span>
          </p>
        </div>
      </section>

      {/* ------------------------------------------------ appel final */}
      <section className="acc-in acc-final">
        <Titre className="acc-titre-xl" debut={t('acc_fin_titre_1')} accent={t('acc_fin_titre_2')} />
        <p className="acc-texte">{t('acc_fin_desc')}</p>
        <Link to="/assistant" className="btn-plein">
          {t('cta_essayer')}
          <Icon nom="fleche" taille={16} epaisseur={2.2} className="acc-fleche" />
        </Link>
      </section>

      <footer className="acc-pied">
        <div className="acc-in acc-pied-grille">
          <div>
            <Logo />
            <p>{t('acc_titre_1')} {t('acc_titre_2')}</p>
          </div>
          <nav aria-label={t('nav_services')}>
            <h4>{t('nav_services')}</h4>
            <Link to="/assistant">{t('nav_assistant')}</Link>
            <Link to="/medicaments">{t('nav_medicaments')}</Link>
            <Link to="/pharmacies">{t('nav_pharmacies')}</Link>
            <Link to="/garde">{t('nav_garde')}</Link>
            <Link to="/historique">{t('nav_historique')}</Link>
          </nav>
          <div>
            <h4>{t('nav_sources')}</h4>
            <span>AMMPS</span>
            <span>CNOPS</span>
            <span>CNSS</span>
          </div>
          <div>
            <h4>{t('acc_pied_langues')}</h4>
            <span>الدارجة</span>
            <span>Darija</span>
            <span>Français</span>
            <Link to="/parametres">{t('nav_parametres')}</Link>
          </div>
        </div>
        <p className="acc-in acc-pied-note">{t('disclaimer_court')}</p>
      </footer>
    </div>
  )
}
