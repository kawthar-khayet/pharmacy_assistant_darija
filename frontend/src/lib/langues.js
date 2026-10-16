// Dictionnaire complet de traductions pour DwaTalk.
// 3 langues supportees :
// - ary_ar : الدارجة المغربية بالأحرف العربية (langue par defaut, direction RTL)
// - ary_lat : Darija en alphabet latin / Arabizi (direction LTR)
// - fr : Francais (direction LTR)

export const LANGUE_PAR_DEFAUT = 'ary_ar'

export const LANGUES_DISPONIBLES = [
  { code: 'ary_ar', libelle: 'الدارجة', etiquette: 'عربية', rtl: true },
  { code: 'ary_lat', libelle: 'Darija', etiquette: 'Latine', rtl: false },
  { code: 'fr', libelle: 'Français', etiquette: 'FR', rtl: false },
]

const ARABES = new Set(['ary_ar', 'ar'])

export const estArabe = (langue) => ARABES.has(langue)

const TEXTES = {
  // --- Marque & Identite ---
  app_nom: {
    ary_ar: 'دوا توك',
    ary_lat: 'DwaTalk',
    fr: 'DwaTalk',
  },
  app_sous_titre: {
    ary_ar: 'المساعد الذكي ديالك للصيدلة والدوا',
    ary_lat: 'L-moussa3id dyalk f saydaliya w d-dwa',
    fr: 'Assistant santé et pharmacie par IA',
  },
  hero_badge: {
    ary_ar: 'مساعد ذكي للصحة بالمغرب',
    ary_lat: 'Moussa3id sa7a IA fl-Meghrib',
    fr: 'Assistant santé IA Maroc',
  },
  hero_titre_1: {
    ary_ar: 'سول على دواك،',
    ary_lat: 'Swwel 3la dwak,',
    fr: 'Tes questions médicaments,',
  },
  hero_titre_2: {
    ary_ar: 'بالدارجة.',
    ary_lat: 'b darija.',
    fr: 'en darija.',
  },
  hero_description: {
    ary_ar: 'الأثمنة، التعويض فالـ CNSS و CNOPS، صيدليات الحراسة والمعلومات الرسمية لي كتهم صحتك.',
    ary_lat: 'L-atmina, remboursement CNSS/CNOPS, saydaliyat de garde w l-ma3loumat r-rasmiya.',
    fr: 'Prix, remboursement CNSS & CNOPS, pharmacies de garde et notices officielles autorisées au Maroc.',
  },
  hero_placeholder: {
    ary_ar: 'شنو بغيتي تعرف؟ (مثلا: شحال ثمن دوليبران؟ أقرب صيدلية مفتوحة...)',
    ary_lat: 'Chno bghiti t3ref? (taman doliprane, saydaliya de garde...)',
    fr: 'Pose ta question (ex : prix Doliprane, pharmacie de garde...)',
  },
  hero_aide: {
    ary_ar: 'كتب ولا هضر بالدارجة، بالعربية ولا بالفرنسية — كنفهموك كيفما هدرتي.',
    ary_lat: 'Kteb wla hder b darija, l3arbiya wla l-francais — kanfehmouk.',
    fr: 'Écris ou parle en darija, arabe ou français — on te comprend.',
  },

  // --- Navigation ---
  nav_accueil: { ary_ar: 'الرئيسية', ary_lat: 'L-Accueil', fr: 'Accueil' },
  nav_assistant: { ary_ar: 'المساعد الذكي', ary_lat: 'L-Moussa3id', fr: 'Assistant' },
  nav_medicaments: { ary_ar: 'الأدوية', ary_lat: 'L-Adwiya', fr: 'Médicaments' },
  nav_pharmacies: { ary_ar: 'الصيدليات', ary_lat: 'Saydaliyat', fr: 'Pharmacies' },
  nav_garde: { ary_ar: 'صيدليات الحراسة', ary_lat: 'De garde', fr: 'De garde' },
  nav_historique: { ary_ar: 'المحادثات السابقة', ary_lat: 'L-Archiv', fr: 'Historique' },
  nav_parametres: { ary_ar: 'الإعدادات', ary_lat: 'I3dadat', fr: 'Paramètres' },
  nav_menu: { ary_ar: 'القائمة', ary_lat: 'Menu', fr: 'Menu' },
  officiel_titre: { ary_ar: 'بيانات مغربية رسمية', ary_lat: 'Ma3loumat rasmiya', fr: 'Données officielles' },
  officiel_desc: {
    ary_ar: 'أدوية AMMPS، أثمنة وتعويضات CNOPS و CNSS المحينة.',
    ary_lat: 'Adwiya AMMPS, atmina w remboursement CNOPS w CNSS.',
    fr: 'Médicaments AMMPS, prix et remboursements CNOPS et CNSS.',
  },
  disclaimer_court: {
    ary_ar: 'دوا توك كيعاونك ويوجهك، وما كيعوضش استشارة الطبيب ولا الصيدلي.',
    ary_lat: 'DwaTalk kay3awnek w ywejjhek, ma kay3ewwedch tbib wla pharmacien.',
    fr: 'DwaTalk oriente et informe. Il ne remplace pas un pharmacien.',
  },

  // --- Urgences Express ---
  urgences_titre: { ary_ar: 'أرقام الطوارئ فالمغرب', ary_lat: 'Arqam d-tawari2 fl-Meghrib', fr: 'Urgences médicales Maroc' },
  urgence_samu: { ary_ar: 'الإسعاف (SAMU)', ary_lat: 'SAMU (L-Is3af)', fr: 'SAMU (Ambulance)' },
  urgence_pompiers: { ary_ar: 'الوقاية المدنية', ary_lat: 'L-Wiqaya l-Madaniya', fr: 'Protection civile' },
  urgence_poison: { ary_ar: 'مركز محاربة التسمم', ary_lat: 'Centre Antipoison', fr: 'Centre Antipoison' },
  urgence_bouton: { ary_ar: 'طوارئ', ary_lat: 'Tawari2', fr: 'Urgences' },

  // --- Suggestions & Pistes ---
  piste_prix: { ary_ar: 'شحال كيدير دوليبران 1000؟', ary_lat: 'Chhal taman doliprane 1g?', fr: 'Combien coûte Doliprane 1g ?' },
  piste_role: { ary_ar: 'فاش كيصلح دواء أوغمونتان؟', ary_lat: 'Chno kaydir augmentin?', fr: 'À quoi sert Augmentin ?' },
  piste_lieu: { ary_ar: 'فين كاينة أقرب صيدلية فالمعاريف؟', ary_lat: 'Fin kayna saydaliya f Maarif?', fr: 'Où est la pharmacie la plus proche à Maarif ?' },
  piste_garde: { ary_ar: 'صيدلية الحراسة ديال الليل فكازا؟', ary_lat: 'Pharmacie de garde d lil f Casa?', fr: 'Pharmacie de garde de nuit à Casablanca ?' },
  piste_remboursement: { ary_ar: 'واش هاد الدوا كيتعوض فالـ CNSS؟', ary_lat: 'Wach had dwa fih remboursement CNSS?', fr: 'Ce médicament est-il remboursé par la CNSS ?' },

  // --- Atouts du Service ---
  atout_base_titre: { ary_ar: 'قواعد رسمية', ary_lat: 'Base officielle', fr: 'Base officielle' },
  atout_base_desc: { ary_ar: 'AMMPS · CNOPS · CNSS المغرب', ary_lat: 'AMMPS · CNOPS · CNSS', fr: 'AMMPS · CNOPS · CNSS' },
  atout_langues_titre: { ary_ar: '3 ديال اللغات', ary_lat: '3 loughat', fr: '3 langues' },
  atout_langues_desc: { ary_ar: 'الدارجة · العربية · Français', ary_lat: 'Darija · 3arbiya · Français', fr: 'Darija · Arabe · Français' },
  atout_voix_titre: { ary_ar: 'هضر بالصوت', ary_lat: 'Hder b l-voix', fr: 'À voix haute' },
  atout_voix_desc: { ary_ar: 'سول بالدارجة بصوتك ويتجاوبك', ary_lat: 'Swwel b sotek b darija', fr: 'Pose ta question en parlant' },
  atout_proximite_titre: { ary_ar: 'صيدليات قريبة', ary_lat: 'Saydaliyat 9rab', fr: 'Pharmacies proches' },
  atout_proximite_desc: { ary_ar: 'بالمدينة، الحي ونظام GPS', ary_lat: 'B lmdina, l7ay w GPS', fr: 'Par ville, quartier et GPS' },

  // --- Services & Actions ---
  services_titre: { ary_ar: 'الخدمات ديالنا', ary_lat: 'Khadamat dyalna', fr: 'Nos services' },
  services_desc: { ary_ar: 'كل ما كتحتاج باش تعرف دواك وتلقى فرماسيانك بأمان.', ary_lat: 'Kol ma kat7taj bach t3ref dwak w saydaliya dyalk.', fr: 'Tout ce qu’il faut pour bien prendre ton traitement.' },
  action_med_titre: { ary_ar: 'بحث على شي دوا', ary_lat: 'Qelleb 3la dwa', fr: 'Rechercher un médicament' },
  action_med_desc: { ary_ar: 'الثمن للعموم، الجرعات، واش كيتعوض وواش بـ Ordonnance.', ary_lat: 'Taman, dosage w taux de remboursement.', fr: 'Prix public, forme, dosage et taux de remboursement.' },
  action_bot_titre: { ary_ar: 'تكلم مع دوا توك', ary_lat: 'Hder m3a DwaTalk', fr: 'Parler à DwaTalk' },
  action_bot_desc: { ary_ar: 'سول بالدارجة، بالعربية ولا بالفرنسية وجاوبك فالحين.', ary_lat: 'Swwel b darija, 3arbiya wla francais.', fr: 'Pose ta question en darija, en arabe ou en français.' },
  action_pharma_titre: { ary_ar: 'لقى صيدلية قريبة', ary_lat: 'Lqa saydaliya', fr: 'Trouver une pharmacie' },
  action_pharma_desc: { ary_ar: 'الصيدليات لي فالحي ديالك، واللي شادين الحراسة دابا.', ary_lat: 'Saydaliyat d l7ay dyalk w li f l-garde.', fr: 'Les pharmacies de ton quartier, et celles de garde.' },
  action_ouvrir: { ary_ar: 'دخول', ary_lat: 'Dkhol', fr: 'Ouvrir' },

  // --- Etapes ---
  etapes_titre: { ary_ar: 'كيفاش كيخدم دوا توك؟', ary_lat: 'Kifach kaykheddem DwaTalk?', fr: 'Comment ça marche' },
  etape_1_titre: { ary_ar: '1. سول كيفما كتهضر', ary_lat: '1. Swwel kif kat-hder', fr: 'Pose ta question' },
  etape_1_desc: { ary_ar: 'كتب ولا هضر بالصوت بالدارجة كما كتهضر عند الفرماسيان.', ary_lat: 'Kteb wla hder b darija kifma 3nd l-farmacyan.', fr: 'Écris ou parle comme tu le ferais au comptoir.' },
  etape_2_titre: { ary_ar: '2. الذكاء الاصطناعي كيفهمك', ary_lat: '2. DwaTalk kayfhem', fr: 'DwaTalk comprend' },
  etape_2_desc: { ary_ar: 'كيعرف الدوا واخا تغلط فالحروف ولا السمية ديالو.', ary_lat: 'Kay3ref d-dwa wakha tghlet f smiya.', fr: 'Il reconnaît le médicament, même mal orthographié.' },
  etape_3_titre: { ary_ar: '3. كتاخد الجواب الموثوق', ary_lat: '3. Katakhod l-jawab', fr: 'Tu reçois la réponse' },
  etape_3_desc: { ary_ar: 'الثمن، التعويض، موانع الاستعمال وأقرب صيدلية ليك.', ary_lat: 'Taman, remboursement, notice w saydaliyat.', fr: 'Prix, remboursement, notice et pharmacies.' },

  // --- Fiches & Alertes Securite ---
  securite_titre: {
    ary_ar: 'معلومات للتوجيه فقط',
    ary_lat: 'Ma3loumat ghir bach tt3rf',
    fr: 'Informations à titre indicatif',
  },
  securite_texte: {
    ary_ar: 'لأي سؤال كيهم حالتك الصحية الشخصية، ديما استشر الطبيب ولا الصيدلي ديالك.',
    ary_lat: 'Ay so2al 3la 7altek nta, swwel pharmacien wla tbib dyalk.',
    fr: 'Pour toute question concernant ta situation personnelle, demande conseil à un pharmacien ou à un médecin.',
  },
  notice_titre: {
    ary_ar: 'موانع الاستعمال والآثار الجانبية',
    ary_lat: 'Contre-indications w les effets secondaires',
    fr: 'Contre-indications et effets secondaires',
  },
  resume_auto_titre: {
    ary_ar: 'ملخص أوتوماتيكي',
    ary_lat: 'Moulakhas otomatiki',
    fr: 'Résumé automatique',
  },
  resume_auto_note: {
    ary_ar: 'هاد الملخص تصاوب أوتوماتيكيا من النص الرسمي. عند أي شك، النص الرسمي هو المرجع.',
    ary_lat: "Had l moulakhas mkhrouj otomatikiyan mn n-nass r-rasmi. Ila kan chi chak, n-nass r-rasmi howa lli kay7kem.",
    fr: "Résumé généré automatiquement à partir du texte officiel. En cas de doute, c'est le texte officiel qui fait foi.",
  },

  // --- Saisie & Recherche ---
  saisie_lieu: {
    ary_ar: 'المدينة ولا الحي ديالك…',
    ary_lat: 'Lmdina wla l7ay dyalk…',
    fr: 'Ta ville ou ton quartier…',
  },
  aide_lieu: {
    ary_ar: 'دوا توك كيتسنى المدينة ولا الحي ديالك باش يقترح عليك صيدليات قريبة.',
    ary_lat: 'DwaTalk kaytsenna lmdina wla l7ay dyalk bach yqtare7 3lik saydaliyat.',
    fr: 'DwaTalk attend ta ville ou ton quartier pour te proposer des pharmacies.',
  },
  ecoute_en_cours: {
    ary_ar: 'كانسمعوك دابا... هضر بالدارجة ولا ورك مرة أخرى باش تحبس',
    ary_lat: 'Kansem3ouk daba... hder b darija wla brek bach t7bes',
    fr: "J'écoute… appuie à nouveau sur le micro quand tu as fini.",
  },
  transcription_en_cours: {
    ary_ar: 'كنحولو الصوت ديالك لكتابة دابا...',
    ary_lat: 'Kanketbo l-klam dyalk daba...',
    fr: 'Transcription en cours…',
  },
  micro_demarrer: {
    ary_ar: 'سول بالصوت ديالك',
    ary_lat: 'Swwel b sotek',
    fr: 'Poser ta question à voix haute',
  },
  micro_arreter: {
    ary_ar: 'حبس التسجيل',
    ary_lat: '7bes t-tasjil',
    fr: "Arrêter l'enregistrement",
  },
  envoyer: {
    ary_ar: 'صيفط السؤال',
    ary_lat: 'Sifet',
    fr: 'Envoyer',
  },
  api_demarrage: {
    ary_ar: 'السيرفر كيتشعل، تسنى شي دقيقة… سؤالك غادي يتصيفط بوحدو',
    ary_lat: 'Serveur kaytcha3el, tsenna chi d9i9a… so2al dyalk ghadi itsifet bou7dou',
    fr: 'Le serveur démarre (environ 1 minute)… ta question partira automatiquement.',
  },

  // --- Termes Medicaments ---
  medicament: { ary_ar: 'دواء', ary_lat: 'Dwa', fr: 'Médicament' },
  nom_approchant: { ary_ar: 'سمية قريبة، تأكد منها', ary_lat: 'Smiya 9riba, t2akked', fr: 'Nom approchant, à vérifier' },
  prix_indicatif: { ary_ar: 'الثمن للعموم (PPV)', ary_lat: 'Taman (PPV)', fr: 'Prix public (PPV)' },
  forme: { ary_ar: 'الشكل والجرعة', ary_lat: 'Forme w dosage', fr: 'Forme & dosage' },
  remboursement: { ary_ar: 'التعويض (CNOPS/CNSS)', ary_lat: 'Remboursement', fr: 'Remboursement' },
  remboursable: { ary_ar: 'معوض فالـ CNSS/CNOPS', ary_lat: 'Fih remboursement', fr: 'Remboursable' },
  non_rembourse: { ary_ar: 'ما فيهش تعويض', ary_lat: 'Ma fihch remboursement', fr: 'Non remboursé' },
  de_garde: { ary_ar: 'صيدلية الحراسة', ary_lat: 'De garde', fr: 'De garde' },
  horaires_inconnus: { ary_ar: 'أوقات العمل غير متوفرة', ary_lat: 'Lwa9t ma m3roufch', fr: 'Horaires non renseignés' },
  itineraire: { ary_ar: 'الطريق (Maps)', ary_lat: 'Tri9 (Maps)', fr: 'Itinéraire' },
  appeler: { ary_ar: 'اتصل', ary_lat: '3iyyet', fr: 'Appeler' },

  // --- Page Medicaments ---
  med_titre: { ary_ar: 'دليل الأدوية بالمغرب', ary_lat: 'Dalil l-adwiya fl-Meghrib', fr: 'Médicaments' },
  med_surtitre: { ary_ar: 'قاعدة بيانات رسمية', ary_lat: 'Base rasmiya', fr: 'Base de référence' },
  med_soustitre: { ary_ar: 'أثمنة، أشكال ونسب التعويض للأدوية المرخصة بالمغرب.', ary_lat: 'Atmina, formes w remboursement dyal dwa fl-Meghrib.', fr: 'Prix, forme et remboursement des médicaments autorisés au Maroc.' },
  med_placeholder: { ary_ar: 'كتب سمية الدوا (مثلا: Doliprane, Smecta, Augmentin...)', ary_lat: 'Qelleb 3la dwa (Doliprane, Smecta...)', fr: 'Rechercher un médicament…' },
  med_aide: { ary_ar: 'كتب الاسم التجاري ولا المادة الفعالة. الأخطاء الإملائية مقبولة.', ary_lat: 'Kteb smiya d dwa wla la molecule.', fr: 'Écris le nom commercial ou la molécule. Les fautes sont tolérées.' },
  med_courants: { ary_ar: 'أدوية كيسولو عليها بزاف', ary_lat: 'Adwiya katte9leb bzaf', fr: 'Recherches fréquentes' },
  med_aucun_titre: { ary_ar: 'ما لقينا حتى دواء بهاد الاسم', ary_lat: 'Ma lqina ta dwa', fr: 'Aucun médicament trouvé' },
  med_aucun_texte: {
    ary_ar: 'تأكد من الحروف، ولا جرب تقلب بالمادة الفعالة (مثلا "paracetamol" فبلاصة "Doliprane").',
    ary_lat: 'T2akked mn l-7rouf wla jereb la molecule (paracetamol f blasset Doliprane).',
    fr: 'Vérifie l’orthographe, ou essaie la molécule plutôt que le nom commercial.',
  },
  med_resultats_nb: { ary_ar: 'نتيجة بحث', ary_lat: 'natija', fr: 'résultat(s)' },
  med_retour: { ary_ar: 'رجوع لنتائج الأدوية', ary_lat: 'Rjou3 l nata2ij', fr: 'Retour aux résultats' },

  // --- Page Pharmacies ---
  pharma_titre: { ary_ar: 'دليل الصيدليات', ary_lat: 'Saydaliyat', fr: 'Pharmacies' },
  pharma_surtitre: { ary_ar: 'دليل وعناوين', ary_lat: 'Annuaire w GPS', fr: 'Annuaire' },
  pharma_soustitre: { ary_ar: 'لقى الصيدليات لي قريبة ليك بالمدينة ولا بالحي، وشوف شكون لي شاد الحراسة.', ary_lat: 'Lqa saydaliyat 9rab lik b lmdina wla l7ay.', fr: 'Trouve une pharmacie par ville ou par quartier, et vois celles de garde.' },
  pharma_placeholder: { ary_ar: 'المدينة ولا الحي ديالك (المعاريف، أكدال، جيليز، بني مكادة...)', ary_lat: 'Lmdina wla l7ay (Maarif, Agdal, Gueliz...)', fr: 'Ta ville ou ton quartier — Maarif, Agdal, Gueliz…' },
  pharma_aide: { ary_ar: 'تقدر تقلب بالحي، بالمدينة ولا بسمية الصيدلية مباشرة.', ary_lat: 'Tqder tqelleb b l7ay, lmdina wla smiya d saydaliya.', fr: 'Tu peux aussi chercher une pharmacie par son nom.' },
  pharma_autour_moi: { ary_ar: 'حدايا دابا (GPS)', ary_lat: '7daya daba (GPS)', fr: 'Autour de moi' },
  pharma_localisant: { ary_ar: 'كنحددو موقعك...', ary_lat: 'Kan7eddo l-mowqi3...', fr: 'Localisation…' },
  pharma_ou_es_tu: { ary_ar: 'فين كاين دابا؟', ary_lat: 'Fin nta daba?', fr: 'Où es-tu ?' },
  pharma_ou_es_tu_desc: { ary_ar: 'حدد مدينتك ولا الحي ديالك باش نطلعو ليك الصيدليات لي دايرين بيك.', ary_lat: 'Kteb lmdina wla l7ay dyalk bach tchouf saydaliyat 9rab lik.', fr: 'Indique ta ville ou ton quartier pour voir les pharmacies répertoriées autour de toi.' },
  pharma_aucun_titre: { ary_ar: 'ما لقينا حتى صيدلية', ary_lat: 'Ma lqina ta saydaliya', fr: 'Aucune pharmacie trouvée' },
  pharma_aucun_desc: { ary_ar: 'جرب تكتب اسم مدينة كبيرة (مثلا "الدار البيضاء") ولا تأكد من اسم الحي.', ary_lat: 'Jereb smiya d mdina kbira wla t2akked mn smiya d l7ay.', fr: 'Essaie une ville plus large ou vérifie l’orthographe du quartier.' },
  pharma_autour_de_toi: { ary_ar: 'قريبة ليك', ary_lat: '9riba lik', fr: 'autour de toi' },

  // --- Page Garde ---
  garde_titre: { ary_ar: 'صيدليات الحراسة', ary_lat: 'Saydaliyat de garde', fr: 'Pharmacies de garde' },
  garde_surtitre: { ary_ar: 'اليوم', ary_lat: 'Lyoum', fr: "Aujourd'hui" },
  garde_soustitre: { ary_ar: 'اختار مدينتك باش تشوف صيدليات الحراسة ديال اليوم: بالنهار، بالليل ولا 24/24.', ary_lat: 'Khtar mdintek bach tchouf saydaliyat de garde d lyoum.', fr: 'Choisis ta ville pour voir les pharmacies de garde du jour : de jour, de nuit ou 24h/24.' },
  garde_placeholder: { ary_ar: 'مدينتك (الدار البيضاء، الرباط، مراكش، فاس، طنجة...)', ary_lat: 'Lmdina dyalk (Casablanca, Rabat, Fes...)', fr: 'Ta ville — Casablanca, Rabat, Safi…' },
  garde_aide: { ary_ar: 'البحث الأول ديال اليوم فمدينة كبيرة يقدر ياخد شوية د الوقت فقراءة المصدر الرسمي.', ary_lat: 'L-ba7t l-ewwel yqder yakhod chwiya d lwaqt.', fr: 'La première recherche du jour peut prendre une trentaine de secondes.' },
  garde_toutes: { ary_ar: 'كلشي', ary_lat: 'Koulchi', fr: 'Toutes' },
  garde_jour: { ary_ar: 'حراسة النهار', ary_lat: 'D nhar', fr: 'De jour' },
  garde_nuit: { ary_ar: 'حراسة الليل', ary_lat: 'D lil', fr: 'De nuit' },
  garde_24h: { ary_ar: '24/24 ساعة', ary_lat: '24h/24', fr: '24h/24' },
  garde_proches_moi: { ary_ar: 'الأقرب ليا دابا', ary_lat: 'Li 9rab liya', fr: 'Les plus proches de moi' },
  garde_appeler_avant: { ary_ar: 'عيط فالتيليفون قبل ما تمشي باش تأكد.', ary_lat: '3iyyet f tilifun 9bel ma tmchi.', fr: 'Appelle avant de te déplacer.' },
  garde_indispo_titre: { ary_ar: 'جدول الحراسة غير متوفر لهاد المدينة', ary_lat: 'Tour de garde ma kaynch', fr: 'Tour de garde non disponible' },

  // --- Assistant & Chat ---
  chat_titre: { ary_ar: 'المساعد دوا توك', ary_lat: 'Moussa3id DwaTalk', fr: 'DwaTalk' },
  chat_role: { ary_ar: 'مساعد صيدلي ذكي', ary_lat: 'Moussa3id saydali', fr: 'Assistant pharmacie' },
  chat_dispo: { ary_ar: 'متصل الآن', ary_lat: 'Dispo daba', fr: 'En ligne' },
  chat_placeholder_normal: { ary_ar: 'كتب سؤالك هنا بالدارجة...', ary_lat: 'Ktebli soualek b darija…', fr: 'Pose ta question ici…' },
  chat_disclaimer: { ary_ar: 'دوا توك يقدر يغلط. تأكد ديما من الصيدلي.', ary_lat: 'DwaTalk yqder yghlet. T2akked mn l-pharmacien.', fr: "DwaTalk peut se tromper. Vérifie auprès d'un pharmacien." },
  chat_copier: { ary_ar: 'نسخ الجواب', ary_lat: 'Copier', fr: 'Copier le message' },
  chat_copie_fait: { ary_ar: 'تم النسخ بنجاح !', ary_lat: 'T-copia !', fr: 'Copié !' },

  // --- Historique ---
  histo_titre: { ary_ar: 'المحادثات السابقة', ary_lat: 'L-Archiv dyal l-hadra', fr: 'Historique' },
  histo_soustitre: { ary_ar: 'المحادثات والأسئلة ديالك لي دازو مع دوا توك.', ary_lat: 'Mouta7adatat dyalk li dazou m3a DwaTalk.', fr: 'Tes discussions précédentes avec DwaTalk.' },
  histo_nouvelle: { ary_ar: 'محادثة جديدة', ary_lat: 'Mouta7adata jdida', fr: 'Nouvelle discussion' },
  histo_vide_titre: { ary_ar: 'ما كاين حتى محادثة مسجلة', ary_lat: 'Ma kayna ta hadra', fr: 'Pas encore de discussion' },
  histo_vide_desc: { ary_ar: 'سول أول سؤال لدوا توك : غادي يتسجل هنا باش تقدر ترجع ليه وقتما بغيتي.', ary_lat: 'Swwel awwal soual l DwaTalk bach yban hna.', fr: 'Pose ta première question à DwaTalk : elle apparaîtra ici pour que tu puisses la reprendre plus tard.' },
  histo_supprimer: { ary_ar: 'مسح هاد المحادثة', ary_lat: 'Mse7 had l-hadra', fr: 'Supprimer la discussion' },
  histo_local_note: { ary_ar: 'المحادثات كيبقاو محفوظين غير فهاد الهاتف/المتصفح فقط، وما كيخرجوش من جهازك.', ary_lat: 'L-hadra katbqa ghir f had l-appareil.', fr: 'L’historique est conservé dans ce navigateur uniquement. Il ne quitte pas cet appareil.' },

  // --- Page d'accueil (presentation du service) ---
  nav_services: { ary_ar: 'الخدمات', ary_lat: 'Khadamat', fr: 'Services' },
  nav_sources: { ary_ar: 'المصادر', ary_lat: 'Masadir', fr: 'Sources' },
  acc_med_chercher: { ary_ar: 'قلّب', ary_lat: 'Qelleb', fr: 'Chercher' },
  nav_langue: { ary_ar: 'اللغة', ary_lat: 'L-lougha', fr: 'Langue' },
  cta_essayer: { ary_ar: 'جرّب دوا توك', ary_lat: 'Jerreb DwaTalk', fr: 'Essayer DwaTalk' },
  acc_surtitre: { ary_ar: 'مساعد الصيدلية فالمغرب', ary_lat: 'Moussa3id dyal saydaliya f l-Meghrib', fr: "L'assistant pharmacie au Maroc" },
  acc_titre_1: { ary_ar: 'المعلومة على دواك،', ary_lat: 'L-ma3louma 3la dwak,', fr: "L'information sur ton médicament," },
  acc_titre_2: { ary_ar: 'باللغة ديالك.', ary_lat: 'b lougha dyalk.', fr: 'dans ta langue.' },
  acc_p1: {
    ary_ar: 'بزاف ديال الناس كيخرجو من الصيدلية وباقي عندهم أسئلة: شحال ثمن هاد الدوا، واش كيتعوض، كيفاش كيتاخد، وفين نلقى صيدلية محلولة دابا.',
    ary_lat: 'Bzzaf d n-nas kaykhrjou men saydaliya w ba9i 3endhom as2ila: chhal taman had d-dwa, wach fih remboursement, kifach kaytakhed, w fin nelqa saydaliya 7alla daba.',
    fr: 'On sort souvent de la pharmacie avec des questions : combien coûte ce médicament, est-il remboursé, comment le prendre, où trouver une pharmacie ouverte maintenant.',
  },
  acc_p2: {
    ary_ar: 'دوا توك كيجمع هاد المعلومات فبلاصة وحدة وكيجاوبك بالدارجة، بالعربية ولا بالفرنسية، على حساب المعطيات الرسمية ديال المغرب.',
    ary_lat: 'DwaTalk kayjme3 had l-ma3loumat f blasa wa7da w kayjawbek b darija, b l3arbiya wla b l-francais, 3la 7sab l-ma3tayat r-rasmiya dyal l-Meghrib.',
    fr: 'DwaTalk réunit ces informations au même endroit et te répond en darija, en arabe ou en français, à partir des données officielles marocaines.',
  },
  acc_voir_services: { ary_ar: 'شوف الخدمات', ary_lat: 'Chouf l-khadamat', fr: 'Voir les services' },

  // apercus illustratifs : aucun prix ni taux reel n'y figure
  acc_ap_illustration: { ary_ar: 'مثال توضيحي', ary_lat: 'Mital l-tawdi7', fr: 'Aperçu illustratif' },
  acc_ap_q1: { ary_ar: 'واش أوغمونتان كيتعوض؟', ary_lat: 'Wach augmentin fih remboursement?', fr: 'Augmentin est-il remboursé ?' },
  acc_ap_q2: { ary_ar: 'Pharmacie de garde à Rabat ?', ary_lat: 'فين كاينة صيدلية ديال الحراسة؟', fr: 'فين كاينة صيدلية ديال الحراسة؟' },
  acc_ap_nom_med: { ary_ar: 'سمية الدوا', ary_lat: 'Smiya d-dwa', fr: 'Nom du médicament' },
  acc_ap_dosage: { ary_ar: 'الجرعة', ary_lat: 'dosage', fr: 'dosage' },
  acc_ap_prix: { ary_ar: 'الثمن', ary_lat: 'Taman', fr: 'Prix' },
  acc_ap_source: { ary_ar: 'المصدر: AMMPS', ary_lat: 'Masdar: AMMPS', fr: 'Source : AMMPS' },
  acc_ap_details: { ary_ar: 'المادة · الجرعة · الشكل · المختبر', ary_lat: 'L-madda · dosage · forme · laboratoire', fr: 'Molécule · dosage · forme · laboratoire' },
  acc_ap_statut: { ary_ar: 'كيتباع', ary_lat: 'Commercialisé', fr: 'Commercialisé' },
  acc_ap_pharma: { ary_ar: 'سمية الصيدلية', ary_lat: 'Smiya saydaliya', fr: 'Nom de la pharmacie' },
  acc_ap_pharma_det: { ary_ar: 'الحي · المسافة · Google Maps', ary_lat: 'L7ay · km · Google Maps', fr: 'Quartier · distance · Google Maps' },
  acc_ap_garde: { ary_ar: 'صيدلية الحراسة', ary_lat: 'Saydaliya de garde', fr: 'Pharmacie de garde' },
  acc_ap_nuit: { ary_ar: 'الليل', ary_lat: 'lil', fr: 'nuit' },
  acc_ap_garde_det: { ary_ar: 'العنوان · التيليفون', ary_lat: 'L-3onwan · tilifoun', fr: 'Adresse · téléphone' },

  acc_stat_med: { ary_ar: 'سمية ديال الدوا', ary_lat: 'smiya d dwa', fr: 'noms de médicaments' },
  acc_stat_pharma: { ary_ar: 'صيدلية', ary_lat: 'saydaliya', fr: 'pharmacies' },
  acc_stat_villes: { ary_ar: 'مدينة', ary_lat: 'mdina', fr: 'villes' },
  acc_stat_langues: { ary_ar: 'لغات', ary_lat: 'loughat', fr: 'langues' },
  acc_stat_note: { ary_ar: 'فقاعدة بيانات دوا توك', ary_lat: 'F la base dyal DwaTalk', fr: 'Dans la base DwaTalk' },

  acc_essai_titre_1: { ary_ar: 'جرّب،', ary_lat: 'Jerreb,', fr: 'Essaie,' },
  acc_essai_titre_2: { ary_ar: 'سول سؤال.', ary_lat: 'swwel so2al.', fr: 'pose une question.' },
  acc_essai_desc: {
    ary_ar: 'كتب كيفما كتهضر. السمية مكتوبة بالغلط؟ دوا توك كيفهمها.',
    ary_lat: 'Kteb kima kat-hder. Smiya mektouba b ghalat? DwaTalk kayfhemha.',
    fr: 'Écris comme tu parles. Un nom mal orthographié ? DwaTalk le reconnaît.',
  },

  acc_g_prix_titre: { ary_ar: 'الثمن والتعويض', ary_lat: 'Taman w remboursement', fr: 'Prix et remboursement' },
  acc_g_prix_desc: {
    ary_ar: 'الثمن للعموم، ونسبة التعويض ديال CNOPS و CNSS لكل دوا.',
    ary_lat: 'Taman l-3oumoumi, w nisbat remboursement CNOPS w CNSS l kol dwa.',
    fr: 'Le prix public et le taux de remboursement CNOPS et CNSS de chaque médicament.',
  },
  acc_g_secu_titre: { ary_ar: 'التنبيهات والاستعمال', ary_lat: 'Tanbihat w l-isti3mal', fr: 'Précautions et usage' },
  acc_g_secu_desc: {
    ary_ar: 'الحمل، الرضاعة، والأدوية لي ما كيتلاقاوش، من النشرات الرسمية.',
    ary_lat: 'L-7aml, r-rda3a, w l-adwiya li ma kaytla9awch, men notices rasmiya.',
    fr: 'Grossesse, allaitement et interactions, tirés des notices officielles.',
  },
  acc_g_voix_titre: { ary_ar: 'بصوتك', ary_lat: 'B sotek', fr: 'À la voix' },
  acc_g_voix_desc: { ary_ar: 'هضر بالدارجة بلا ما تكتب.', ary_lat: 'Hder b darija bla ma tkteb.', fr: 'Parle en darija, sans écrire.' },
  acc_g_langues_desc: { ary_ar: 'بدّل اللغة فأي وقت.', ary_lat: 'Beddel l-lougha f ay we9t.', fr: 'Change de langue à tout moment.' },

  acc_med_titre_1: { ary_ar: 'قلّب على', ary_lat: 'Qelleb 3la', fr: 'Cherche' },
  acc_med_titre_2: { ary_ar: 'أي دوا.', ary_lat: 'ay dwa.', fr: "n'importe quel médicament." },
  acc_med_desc: {
    ary_ar: 'بالسمية التجارية ولا بالمادة الفعالة. كل بطاقة فيها الجرعة، الشكل، المختبر، الثمن والتنبيهات.',
    ary_lat: 'B smiya tijariya wla b l-madda. Kol fiche fiha dosage, forme, laboratoire, taman w tanbihat.',
    fr: 'Par nom commercial ou par molécule. Chaque fiche donne dosage, forme, laboratoire, prix et précautions.',
  },

  acc_ph_titre_1: { ary_ar: 'صيدلية قريبة،', ary_lat: 'Saydaliya 9riba,', fr: 'Une pharmacie proche,' },
  acc_ph_titre_2: { ary_ar: 'ولا ديال الحراسة.', ary_lat: 'wla de garde.', fr: 'ou de garde.' },
  acc_ph_desc: {
    ary_ar: 'بالمدينة، بالحي ولا بـ GPS. وصيدليات الحراسة ديال اليوم فمدينتك.',
    ary_lat: 'B lmdina, b l7ay wla b GPS. W tour de garde dyal l-youm f mdina dyalk.',
    fr: 'Par ville, par quartier ou par GPS. Et le tour de garde du jour dans ta ville.',
  },
  acc_ph_cta_garde: { ary_ar: 'الحراسة ديال اليوم', ary_lat: 'De garde l-youm', fr: "De garde aujourd'hui" },

  acc_src_titre_1: { ary_ar: 'منين جات المعلومة،', ary_lat: 'Mnin jat l-ma3louma,', fr: "D'où vient l'information," },
  acc_src_titre_2: { ary_ar: 'وفين كتوقف.', ary_lat: 'w fin kat-wqef.', fr: "et où elle s'arrête." },
  acc_src_off_titre: { ary_ar: 'معطيات رسمية', ary_lat: 'Ma3tayat rasmiya', fr: 'Données officielles' },
  acc_src_off_desc: {
    ary_ar: 'الأدوية والأثمنة: AMMPS. التعويض: CNOPS و CNSS.',
    ary_lat: 'Adwiya w taman: AMMPS. Remboursement: CNOPS w CNSS.',
    fr: 'Médicaments et prix : AMMPS. Remboursement : CNOPS et CNSS.',
  },
  acc_src_base_titre: { ary_ar: 'قاعدة بيانات دوا توك', ary_lat: 'La base dyal DwaTalk', fr: 'La base DwaTalk' },
  acc_src_base_desc: {
    ary_ar: 'الصيدليات، الأحياء والحراسة، مجموعين من مصادر عمومية. النشرات جاية من القاعدة العمومية الفرنسية ديال الأدوية.',
    ary_lat: 'Saydaliyat, l-a7ya w tour de garde, mejmou3in men masadir 3oumoumiya. Notices jayin men la base 3oumoumiya l-fransawiya d l-adwiya.',
    fr: 'Pharmacies, quartiers et tours de garde, rassemblés à partir de sources publiques. Les notices viennent de la base publique française des médicaments.',
  },
  acc_src_ia_titre: { ary_ar: 'جواب المساعد', ary_lat: 'Jawab l-moussa3id', fr: "La réponse de l'assistant" },
  acc_src_ia_desc: {
    ary_ar: 'مكتوب بالذكاء الاصطناعي على هاد المعطيات. يمكن يكون فيه غلط.',
    ary_lat: 'Mektoub b l-IA 3la had l-ma3tayat. Imken ykoun fih ghalat.',
    fr: 'Rédigée par une IA à partir de ces données. Elle peut contenir des erreurs.',
  },
  acc_src_limite: {
    ary_ar: 'دوا توك ما كيعطيش تشخيص وما كيعوضش الطبيب ولا الصيدلي. فحالة الاستعجال: 141 ولا 15.',
    ary_lat: 'DwaTalk ma kay3tich tachkhis w ma kay3ewwedch tbib wla pharmacien. F l-isti3jal: 141 wla 15.',
    fr: "DwaTalk ne pose pas de diagnostic et ne remplace ni médecin ni pharmacien. En cas d'urgence : 141 ou 15.",
  },

  acc_fin_titre_1: { ary_ar: 'عندك سؤال على', ary_lat: '3endek so2al 3la', fr: 'Une question sur' },
  acc_fin_titre_2: { ary_ar: 'دواك؟', ary_lat: 'dwak?', fr: 'ton médicament ?' },
  acc_fin_desc: { ary_ar: 'بالمجان، بلا تسجيل.', ary_lat: 'B l-majjan, bla tasjil.', fr: 'Gratuit, sans inscription.' },
  acc_pied_langues: { ary_ar: 'اللغات', ary_lat: 'Loughat', fr: 'Langues' },

  // --- Parametres ---
  param_titre: { ary_ar: 'الإعدادات', ary_lat: 'I3dadat', fr: 'Paramètres' },
  param_soustitre: { ary_ar: 'ضبط لغة وتفضيلات دوا توك على هاد الجهاز.', ary_lat: 'Reglages dyal DwaTalk f had l-appareil.', fr: 'Réglages de DwaTalk sur cet appareil.' },
  param_langue_titre: { ary_ar: 'لغة الواجهة', ary_lat: 'Loughat l-interface', fr: "Langue de l'interface" },
  param_langue_desc: { ary_ar: 'اختار بين الدارجة بالعربية (RTL)، الدارجة بالحروف اللاتينية ولا الفرنسية.', ary_lat: 'Khtar Darija b l-3arbiya, Darija latine wla Francais.', fr: 'Choisis entre Darija (arabe), Darija (latine) ou Français.' },
  param_voix_titre: { ary_ar: 'السؤال بالصوت (Whisper)', ary_lat: 'So2al b sot (Whisper)', fr: 'Question à voix haute' },
  param_voix_desc_active: { ary_ar: 'الصوت ديالك كيتحول لكتابة مباشرة بسيرفر DwaTalk بأمان وبلا طرف ثالث.', ary_lat: 'Sotek kayt-transcriva f serveur DwaTalk b amane.', fr: "Ta voix est transcrite par Whisper sur le serveur DwaTalk, pas chez un tiers." },
  param_voix_desc_inactif: { ary_ar: 'التسجيل الصوتي غير مدعوم فهاد المتصفح.', ary_lat: 'L-micro ma kheddamch f had l-browser.', fr: "L'enregistrement audio n'est pas disponible dans ce navigateur." },
  param_supporte: { ary_ar: 'شغال', ary_lat: 'Active', fr: 'Activé' },
  param_non_supporte: { ary_ar: 'غير مدعوم', ary_lat: 'Non supporte', fr: 'Non supporté' },
  param_histo_titre: { ary_ar: 'المحادثات المحلية', ary_lat: 'L-Archiv local', fr: 'Historique local' },
  param_histo_desc: { ary_ar: 'محادثة محفوظة فهاد المتصفح.', ary_lat: 'mouta7adatat f had l-appareil.', fr: 'discussion(s) conservée(s) dans ce navigateur.' },
  param_tout_effacer: { ary_ar: 'مسح جميع المحادثات', ary_lat: 'Mse7 koulchi', fr: 'Tout effacer' },
  param_effacer_confirm: { ary_ar: 'واش باغي تمسح جميع المحادثات ديالك؟ هاد العملية نهائية.', ary_lat: 'Bghiti tmse7 ga3 l-mouta7adatat? Had l-3amaliya niha2iya.', fr: 'Effacer toutes tes discussions ? Cette action est définitive.' },
}

/** Texte `cle` dans `langue` (darija arabe si la traduction manque). */
export function t(langue, cle) {
  const variantes = TEXTES[cle]
  if (!variantes) return cle
  return variantes[langue] ?? variantes[LANGUE_PAR_DEFAUT] ?? variantes['fr'] ?? cle
}
