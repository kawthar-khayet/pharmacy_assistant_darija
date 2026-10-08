// Textes des fiches de l'assistant, dans la langue de la question.
//
// L'API renvoie `langue` avec chaque reponse (voir nlp/reponse/langues.py) : fr,
// ary_lat (darija en lettres latines), ary_ar (darija en lettres arabes) ou
// ar (arabe standard). Les fiches reprennent cette langue pour que le patient
// ne lise pas une reponse en darija encadree de libelles en francais.

export const LANGUE_PAR_DEFAUT = 'fr'
const ARABES = new Set(['ary_ar', 'ar'])

export const estArabe = (langue) => ARABES.has(langue)

const TEXTES = {
  securite_titre: {
    fr: 'Informations a titre indicatif',
    ary_lat: 'Ma3loumat ghir bach tt3rf',
    ary_ar: 'معلومات غير باش تعرف',
    ar: 'معلومات على سبيل الإرشاد',
  },
  // Titre du repli qui contient les rubriques de la notice officielle. Le
  // contenu reste en francais (voir SafetySections) : seul le titre est traduit.
  notice_titre: {
    fr: 'Contre-indications et effets secondaires',
    ary_lat: 'Contre-indications w les effets secondaires',
    ary_ar: 'موانع الاستعمال والآثار الجانبية',
    ar: 'موانع الاستعمال والآثار الجانبية',
  },
  resume_auto_titre: {
    fr: 'Resume automatique',
    ary_lat: 'Moulakhas otomatiki',
    ary_ar: 'ملخص أوتوماتيكي',
    ar: 'ملخص آلي',
  },
  resume_auto_note: {
    fr: "Resume genere automatiquement a partir du texte officiel ci-dessous. En cas de doute, c'est le texte officiel qui fait foi.",
    ary_lat:
      "Had l moulakhas mkhrouj otomatikiyan mn n-nass r-rasmi lli t7t. Ila kan chi chak, n-nass r-rasmi howa lli kay7kem.",
    ary_ar: 'هاد الملخص مخروج أوتوماتيكيا من النص الرسمي اللي تحت. إلا كان شي شك، النص الرسمي هو اللي كيحكم.',
    ar: 'هذا ملخص آلي مستخرج من النص الرسمي أدناه. عند الشك، النص الرسمي هو المرجع.',
  },
  securite_texte: {
    fr: 'Pour toute question concernant ta situation personnelle, demande conseil a un pharmacien ou a un medecin.',
    ary_lat: 'Ay so2al 3la 7altek nta, swwel pharmacien wla tbib.',
    ary_ar: 'أي سؤال على الحالة ديالك، سوّل الصيدلي ولا الطبيب.',
    ar: 'لأي سؤال يخص حالتك الشخصية، استشر صيدليًا أو طبيبًا.',
  },
  saisie_lieu: {
    fr: 'Ta ville ou ton quartier…',
    ary_lat: 'Lmdina wla l7ay dyalk…',
    ary_ar: 'المدينة ولا الحي ديالك…',
    ar: 'مدينتك أو حيّك…',
  },
  aide_lieu: {
    fr: 'DwaTalk attend ta ville ou ton quartier pour te proposer des pharmacies.',
    ary_lat: 'DwaTalk kaytsenna lmdina wla l7ay dyalk bach yqtare7 3lik pharmacies.',
    ary_ar: 'DwaTalk كيتسنى المدينة ولا الحي ديالك باش يقترح عليك صيدليات.',
    ar: 'ينتظر DwaTalk مدينتك أو حيّك ليقترح عليك صيدليات.',
  },
  medicament: { fr: 'Medicament', ary_lat: 'Dwa', ary_ar: 'دوا', ar: 'دواء' },
  nom_approchant: {
    fr: 'Nom approchant, a verifier',
    ary_lat: 'Smiya 9riba, t2akked',
    ary_ar: 'سمية قريبة، تأكد منها',
    ar: 'اسم مقارب، يُرجى التحقق',
  },
  prix_indicatif: { fr: 'Prix indicatif', ary_lat: 'Taman', ary_ar: 'الثمن', ar: 'السعر التقريبي' },
  forme: { fr: 'Forme', ary_lat: 'Forme', ary_ar: 'الشكل', ar: 'الشكل' },
  remboursement: { fr: 'Remboursement', ary_lat: 'Remboursement', ary_ar: 'التعويض', ar: 'التعويض' },
  non_rembourse: {
    fr: 'Non rembourse',
    ary_lat: 'Ma fihch remboursement',
    ary_ar: 'ما فيهش التعويض',
    ar: 'غير قابل للتعويض',
  },
  de_garde: { fr: 'De garde', ary_lat: 'De garde', ary_ar: 'حراسة', ar: 'مناوبة' },
  horaires_inconnus: {
    fr: 'Horaires non renseignes',
    ary_lat: 'Lwa9t ma m3roufch',
    ary_ar: 'الوقت ما معروفش',
    ar: 'أوقات العمل غير متوفرة',
  },
  itineraire: { fr: 'Itineraire', ary_lat: 'Tri9', ary_ar: 'الطريق', ar: 'الاتجاهات' },
}

/** Texte `cle` dans `langue` (francais si la traduction manque). */
export function t(langue, cle) {
  const variantes = TEXTES[cle]
  return variantes[langue] ?? variantes[LANGUE_PAR_DEFAUT]
}
