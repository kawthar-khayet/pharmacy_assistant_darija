/** Rappel affiche partout ou une information medicale est presentee : DwaTalk
 *  oriente, il ne remplace ni le pharmacien ni le medecin. */
export default function SafetyNotice({ mince = false }) {
  return (
    <div className={`securite ${mince ? 'securite-mince' : ''}`} role="note">
      <span className="securite-glyphe" aria-hidden="true">⚠️</span>
      <div>
        <strong>Informations a titre indicatif</strong>
        <p>
          Pour toute question concernant ta situation personnelle, demande conseil
          a un pharmacien ou a un medecin.
        </p>
      </div>
    </div>
  )
}
