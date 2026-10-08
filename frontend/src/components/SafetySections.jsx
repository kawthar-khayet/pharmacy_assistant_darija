import Icon from './Icon'
import { LANGUE_PAR_DEFAUT, estArabe, t } from '../lib/langues'

/**
 * Rubriques de securite d'une molecule, telles que l'API les renvoie : texte
 * de la notice officielle francaise, mot pour mot.
 *
 * Deux partis pris.
 *
 * Le texte reste en francais meme quand la conversation est en darija. Le
 * traduire demanderait de le faire reecrire par un modele, et une
 * contre-indication reformulee est une contre-indication faussee -- ici le
 * risque n'est pas une phrase maladroite mais une erreur de sante.
 *
 * Il est replie par defaut. Ces rubriques font plusieurs milliers de
 * caracteres : deroulees d'office, elles noieraient la reponse a la question
 * posee, qui est le plus souvent un prix ou une adresse.
 */
const RUBRIQUES = [
  { cle: 'indications', icone: 'loupe', titre: 'A quoi sert ce medicament' },
  { cle: 'contre_indications', icone: 'bouclier', titre: 'Contre-indications' },
  { cle: 'precautions', icone: 'alerte', titre: 'Precautions' },
  { cle: 'interactions', icone: 'liste', titre: 'Interactions' },
  { cle: 'grossesse_allaitement', icone: 'pouls', titre: 'Grossesse et allaitement' },
  { cle: 'effets_indesirables', icone: 'eclair', titre: 'Effets indesirables' },
]

export default function SafetySections({ securite, langue = LANGUE_PAR_DEFAUT }) {
  if (!securite?.rubriques) return null
  const presentes = RUBRIQUES.filter((r) => securite.rubriques[r.cle])
  if (presentes.length === 0) return null

  return (
    <details className="securite-repli" dir="ltr">
      <summary>
        <Icon nom="bouclier" taille={14} />
        {t(langue, 'notice_titre')}
        <span className="securite-repli-compte">{presentes.length}</span>
      </summary>

      {securite.resume && (
        <section className="securite-resume" dir={estArabe(securite.resume_langue) ? 'rtl' : undefined}>
          <h5>
            <Icon nom="etincelle" taille={13} />
            {t(langue, 'resume_auto_titre')}
          </h5>
          <p>{securite.resume}</p>
          {/* Dit sans detour que ces phrases sont generees : le lecteur doit
              savoir laquelle des deux versions fait foi. */}
          <p className="securite-resume-note">{t(langue, 'resume_auto_note')}</p>
        </section>
      )}

      {presentes.map((r) => (
        <section key={r.cle} className="securite-rubrique">
          <h5>
            <Icon nom={r.icone} taille={13} />
            {r.titre}
          </h5>
          <p className="detail-texte">{securite.rubriques[r.cle]}</p>
        </section>
      ))}

      <p className="securite-repli-source">
        Notice officielle de {securite.specialite_source} (ANSM), pour la molecule{' '}
        {securite.dci} — pas pour la boite vendue au Maroc.{' '}
        <a href={securite.source_url} target="_blank" rel="noreferrer noopener">
          Voir la notice
        </a>
      </p>
    </details>
  )
}
