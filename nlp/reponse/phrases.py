"""Les phrases du bot, dans les quatre langues de reponse.

Le bot ne redige que ce qui est ici ; les donnees (noms, prix, adresses,
texte des notices) viennent des bases telles quelles. Une phrase absente
dans une langue retombe sur le francais.

Numeros d'urgence verifies (page d'urgence de l'ambassade de France au Maroc,
ma.diplomatie.gouv.fr/fr/urgence) : SAMU 141, Protection civile 15, Centre
antipoison et de pharmacovigilance du Maroc (CAPM) 0801 000 180.
"""
from nlp.reponse.langues import LANGUE_PAR_DEFAUT

TEXTES: dict[str, dict[str, str]] = {
    # --- Urgences : les numeros d'abord, rien d'autre ---------------------------
    "urgence_detresse": {
        "fr": ("C'est une urgence : appelle tout de suite le SAMU au 141, ou la Protection "
               "civile au 15. Ne reste pas seul en attendant les secours."),
        "ary_lat": ("Hadi urgence : 3iyet daba 3la SAMU f 141, wla l-Protection civile f 15. "
                    "Ma tb9ach bo7dek 7ta yjiw."),
        "ary_ar": ("هادي حالة مستعجلة: عيّط دابا على الإسعاف SAMU ف 141، ولا الوقاية المدنية ف 15. "
                   "ما تبقاش بوحدك حتى يجيو."),
        "ar": ("هذه حالة طارئة: اتصل فورًا بالإسعاف SAMU على الرقم 141، أو بالوقاية المدنية على الرقم 15. "
               "لا تبقَ وحدك في انتظار وصول المساعدة."),
    },
    "urgence_intoxication": {
        "fr": ("C'est une urgence : appelle tout de suite le Centre antipoison (CAPM) au "
               "0801 000 180, 24h/24. Si la personne respire mal, s'endort ou ne reagit plus : "
               "SAMU 141 ou Protection civile 15. Ne la fais pas vomir sans l'avis du centre, "
               "et garde la boite du medicament ou du produit."),
        "ary_lat": ("Hadi urgence : 3iyet daba 3la Centre antipoison (CAPM) f 0801 000 180, 24h/24. "
                    "Ila ma kaytneffsch mzyan, n3es wla ma kayjawbch : SAMU 141 wla Protection civile 15. "
                    "Ma tkhllihch yterref 7ta y9olha lik l-centre, w khlli l-3elba dyal dwa m3ak."),
        "ary_ar": ("هادي حالة مستعجلة: عيّط دابا على مركز محاربة التسمم (CAPM) ف 0801 000 180، 24/24. "
                   "إلا ما كيتنفسش مزيان، نعس ولا ما كيجاوبش: الإسعاف 141 ولا الوقاية المدنية 15. "
                   "ما تخليهش يتقيأ حتى يقولها ليك المركز، وخلي العلبة ديال الدوا معاك."),
        "ar": ("هذه حالة طارئة: اتصل فورًا بمركز محاربة التسمم واليقظة الدوائية (CAPM) على الرقم "
               "0801 000 180، على مدار الساعة. إذا كان الشخص يتنفس بصعوبة أو نام أو لا يستجيب: "
               "الإسعاف 141 أو الوقاية المدنية 15. لا تجعله يتقيأ دون استشارة المركز، واحتفظ بعلبة "
               "الدواء أو المنتج."),
    },

    # --- Situations sans demande -----------------------------------------------
    "medical": {
        "fr": ("Je ne peux pas donner d'avis medical sur ce que tu decris. Parle a un medecin, ou "
               "demande conseil a un pharmacien. Si c'est grave ou que ca s'aggrave : SAMU 141 ou "
               "Protection civile 15."),
        "ary_lat": ("Ma n9derch n3tik ra2y tibbi 3la had chi lli katgoul. Hder m3a tbib, wla swwel "
                    "pharmacien. Ila kan l7al khatir wla kayzid : SAMU 141 wla Protection civile 15."),
        "ary_ar": ("ما نقدرش نعطيك رأي طبي على هادشي اللي كتقول. هضر مع طبيب، ولا سوّل الصيدلي. "
                   "إلا كانت الحالة خطيرة ولا كتزيد: الإسعاف 141 ولا الوقاية المدنية 15."),
        "ar": ("لا يمكنني تقديم رأي طبي حول ما تصفه. تحدّث إلى طبيب، أو اطلب نصيحة الصيدلي. "
               "إذا كانت الحالة خطيرة أو تتفاقم: الإسعاف 141 أو الوقاية المدنية 15."),
    },
    "pas_d_info": {
        "fr": ("Je n'ai pas cette information. Je ne suis pas une pharmacie : je ne connais pas "
               "les stocks, je ne vends rien et je ne propose pas de medicament de remplacement. "
               "Demande a ton pharmacien."),
        "ary_lat": ("Ma 3ndich had l-ma3louma. Ana machi pharmacie : ma kan3refch chno kayn f "
                    "l-stock, ma kanbi3 walou w ma kan9tare7ch dwa f blast dwa. Swwel pharmacien dyalek."),
        "ary_ar": ("ما عنديش هاد المعلومة. أنا ماشي صيدلية: ما كنعرفش شنو كاين فالسطوك، ما كنبيع والو "
                   "وما كنقترحش دوا فبلاصة دوا. سوّل الصيدلي ديالك."),
        "ar": ("لا تتوفر لدي هذه المعلومة. لست صيدلية: لا أعرف المخزون، ولا أبيع شيئًا، ولا أقترح "
               "دواءً بديلًا. اسأل الصيدلي."),
    },
    "incompris": {
        "fr": "Je n'ai pas bien compris ta demande. Peux-tu reformuler ?",
        "ary_lat": "Ma fhemtch mzyan chnou bghiti. T9der t3awed b tari9a khra ?",
        "ary_ar": "ما فهمتش مزيان شنو بغيتي. تقدر تعاود بطريقة خرا؟",
        "ar": "لم أفهم طلبك جيدًا. هل يمكنك إعادة صياغته؟",
    },
    "salutation": {
        "fr": ("Bonjour ! Je peux te donner le prix, le remboursement ou la notice d'un "
               "medicament, et t'aider a trouver une pharmacie. Pose ta question."),
        "ary_lat": ("Salam ! N9der n3tik taman, remboursement wla chno katgoul la notice dyal chi dwa, "
                    "w nl9a lik pharmacie. Swwel."),
        "ary_ar": ("السلام! نقدر نعطيك الثمن، التعويض ولا شنو كتقول النشرة ديال شي دوا، ونلقى ليك "
                   "صيدلية. سوّل."),
        "ar": ("مرحبًا! يمكنني أن أعطيك سعر دواء أو نسبة تعويضه أو ما تقوله نشرته، وأن أساعدك في "
               "العثور على صيدلية. تفضّل بسؤالك."),
    },
    "hors_sujet": {
        "fr": ("Je suis un assistant pharmacie : je peux t'aider pour les medicaments (prix, "
               "remboursement, notice) et pour trouver une pharmacie. Pour le reste, je ne suis "
               "pas la bonne adresse."),
        "ary_lat": ("Ana assistant dyal pharmacie : n9der n3awnek f dwa (taman, remboursement, "
                    "notice) w nl9a lik pharmacie. Chi 7aja khra, ma n9derch n3awnek fiha."),
        "ary_ar": ("أنا مساعد ديال الصيدلية: نقدر نعاونك فالدوا (الثمن، التعويض، النشرة) ونلقى ليك "
                   "صيدلية. شي حاجة خرا، ما نقدرش نعاونك فيها."),
        "ar": ("أنا مساعد صيدلية: يمكنني مساعدتك بخصوص الأدوية (السعر، التعويض، النشرة) وفي العثور "
               "على صيدلية. أما المواضيع الأخرى فهي خارج نطاق اختصاصي."),
    },
    "llm_indisponible": {
        "fr": ("Je n'arrive pas a analyser ta question pour le moment (service surcharge). "
               "Reessaie dans une minute. En cas d'urgence : SAMU 141, Protection civile 15, "
               "Centre antipoison 0801 000 180."),
        "ary_lat": ("Ma 9dertch nfhem so2alek daba (kayn daght 3la l-service). 3awed mn ba3d chi "
                    "d9i9a. F 7alat urgence : SAMU 141, Protection civile 15, Centre antipoison "
                    "0801 000 180."),
        "ary_ar": ("ما قدرتش نفهم السؤال ديالك دابا (كاين ضغط على الخدمة). عاود من بعد شي دقيقة. "
                   "فحالة الاستعجال: الإسعاف 141، الوقاية المدنية 15، مركز محاربة التسمم 0801 000 180."),
        "ar": ("لا أستطيع تحليل سؤالك حاليًا (الخدمة مثقلة). أعد المحاولة بعد دقيقة. في حالة الطوارئ: "
               "الإسعاف 141، الوقاية المدنية 15، مركز محاربة التسمم 0801 000 180."),
    },
    "posologie": {
        "fr": "Pour la dose et la facon de prendre un medicament, pose la question a ton medecin.",
        "ary_lat": "3la ch7al w kifach takhod dwa, swwel tbib dyalek.",
        "ary_ar": "على شحال وكيفاش تاخد الدوا، سوّل الطبيب ديالك.",
        "ar": "بخصوص الجرعة وطريقة تناول الدواء، اطرح السؤال على طبيبك.",
    },

    # --- Questions pour completer la demande -----------------------------------
    "demander_medicament": {
        "fr": "De quel medicament parles-tu ?",
        "ary_lat": "3la ina dwa katsowwel ?",
        "ary_ar": "على أنهي دوا كتسوّل؟",
        "ar": "عن أي دواء تسأل؟",
    },
    "demander_lieu": {
        "fr": "Dans quelle ville et quel quartier es-tu ?",
        "ary_lat": "F ina mdina w f ina 7ay nta ?",
        "ary_ar": "فأنهي مدينة وفأنهي حي نتا؟",
        "ar": "في أي مدينة وأي حي أنت؟",
    },
    "demander_pharmacie": {
        "fr": "Quel est le nom de la pharmacie ?",
        "ary_lat": "Chnou smiyt l-pharmacie ?",
        "ary_ar": "شنو سمية الصيدلية؟",
        "ar": "ما اسم الصيدلية؟",
    },
    "demander_regime": {
        "fr": "Tu es assure a la CNOPS, a la CNSS, ou tu n'as pas d'assurance maladie ?",
        "ary_lat": "Nta m2ammen f CNOPS, f CNSS, wla ma 3ndekch tamin ?",
        "ary_ar": "نتا مأمن ف CNOPS، ف CNSS، ولا ما عندكش التأمين؟",
        "ar": "هل أنت منخرط في CNOPS أم في CNSS، أم ليس لديك تأمين صحي؟",
    },

    # --- Medicaments --------------------------------------------------------------
    "med_introuvable": {
        "fr": ("Je ne trouve pas « {nom} » parmi les medicaments autorises au Maroc. Verifie "
               "l'orthographe, ou essaie le nom de la molecule (par exemple « paracetamol »)."),
        "ary_lat": ("Ma l9itch « {nom} » f les medicaments lmrkhsin f lMaghrib. Chouf wach ktbtih "
                    "mzyan, wla jreb smiyt l-molecule (b7al « paracetamol »)."),
        "ary_ar": ("ما لقيتش « {nom} » فالأدوية المرخصة فالمغرب. شوف واش كتبتيه مزيان، "
                   "ولا جرب سمية المادة الفعالة (بحال « باراسيتامول »)."),
        "ar": ("لم أجد « {nom} » ضمن الأدوية المرخصة في المغرب. تحقّق من الإملاء، "
               "أو جرّب اسم المادة الفعالة (مثل « باراسيتامول »)."),
    },
    "med_a_confirmer": {
        "fr": "Je pense que tu parles de {nom} (verifie que c'est bien lui).",
        "ary_lat": "Kan dhenn katqsed {nom} (t2akked bli howa).",
        "ary_ar": "كنظن كتقصد {nom} (تأكد بلي هو).",
        "ar": "أظن أنك تقصد {nom} (تأكد من أنه هو).",
    },
    "med_plus_commercialise": {
        "fr": "{nom} n'est plus commercialise au Maroc d'apres mes donnees.",
        "ary_lat": "{nom} ma b9ach kayitba3 f lMaghrib 3la 7sab l-ma3loumat dyali.",
        "ary_ar": "{nom} ما بقاش كيتباع فالمغرب على حساب المعلومات ديالي.",
        "ar": "لم يعد {nom} مسوّقًا في المغرب حسب معطياتي.",
    },
    "prix_tete": {
        "fr": "Prix public de {nom} :",
        "ary_lat": "Taman dyal {nom} :",
        "ary_ar": "الثمن ديال {nom}:",
        "ar": "سعر {nom} للعموم:",
    },
    "prix_inconnu": {
        "fr": "Je n'ai pas le prix de {nom}.",
        "ary_lat": "Ma 3ndich taman dyal {nom}.",
        "ary_ar": "ما عنديش الثمن ديال {nom}.",
        "ar": "لا يتوفر لدي سعر {nom}.",
    },
    "prix_par_dosage": {
        "fr": "Prix de {nom} selon le dosage :",
        "ary_lat": "Taman dyal {nom} 3la 7sab d-dosage :",
        "ary_ar": "الثمن ديال {nom} على حساب الجرعة:",
        "ar": "سعر {nom} حسب الجرعة:",
    },
    "prix_entre": {
        "fr": "{min} a {max}",
        "ary_lat": "bin {min} w {max}",
        "ary_ar": "بين {min} و{max}",
        "ar": "بين {min} و{max}",
    },
    "dosage_absent": {
        "fr": "Je ne trouve pas {nom} en {dosage}.",
        "ary_lat": "Ma lqitch {nom} b {dosage}.",
        "ary_ar": "ما لقيتش {nom} ب {dosage}.",
        "ar": "لم أجد {nom} بجرعة {dosage}.",
    },
    "remb_tete": {
        "fr": "Remboursement {regime} de {nom} :",
        "ary_lat": "Remboursement {regime} dyal {nom} :",
        "ary_ar": "التعويض ديال {regime} على {nom}:",
        "ar": "تعويض {regime} عن {nom}:",
    },
    "remb_montant": {
        "fr": "rembourse a {taux} %, soit {montant} (base de remboursement {base})",
        "ary_lat": "kayt3awed b {taux} %, ya3ni {montant} (base de remboursement {base})",
        "ary_ar": "كيتعاود ب {taux} %، يعني {montant} (أساس التعويض {base})",
        "ar": "يُعوَّض بنسبة {taux} %، أي {montant} (أساس التعويض {base})",
    },
    "remb_taux": {
        "fr": "rembourse a {taux} %",
        "ary_lat": "kayt3awed b {taux} %",
        "ary_ar": "كيتعاود ب {taux} %",
        "ar": "يُعوَّض بنسبة {taux} %",
    },
    "remb_non": {
        "fr": "non rembourse",
        "ary_lat": "ma kayt3awedch",
        "ary_ar": "ما كيتعاودش",
        "ar": "غير قابل للتعويض",
    },
    "remb_inconnu": {
        "fr": "taux inconnu",
        "ary_lat": "ma 3ndich t-taux",
        "ary_ar": "ما عنديش النسبة",
        "ar": "النسبة غير معروفة",
    },
    "remb_commun": {
        "fr": "{nom} est rembourse a {taux} % par la {regime}. Donne-moi le dosage pour le montant exact.",
        "ary_lat": "{nom} kayt3awed b {taux} % f {regime}. 3tini d-dosage bach n7seb lik l-montant.",
        "ary_ar": "{nom} كيتعاود ب {taux} % ف {regime}. عطيني الجرعة باش نحسب ليك المبلغ.",
        "ar": "يُعوَّض {nom} بنسبة {taux} % من طرف {regime}. أعطني الجرعة لأحسب لك المبلغ.",
    },
    "remb_commun_non": {
        "fr": "{nom} n'est pas rembourse par la {regime}.",
        "ary_lat": "{nom} ma kayt3awedch f {regime}.",
        "ary_ar": "{nom} ما كيتعاودش ف {regime}.",
        "ar": "لا يُعوَّض {nom} من طرف {regime}.",
    },
    "remb_variable": {
        "fr": "Le remboursement {regime} de {nom} depend du dosage : donne-moi le dosage.",
        "ary_lat": "Remboursement {regime} dyal {nom} kaytbddel 3la 7sab d-dosage : 3tini d-dosage.",
        "ary_ar": "التعويض ديال {regime} على {nom} كيتبدل على حساب الجرعة: عطيني الجرعة.",
        "ar": "يختلف تعويض {regime} عن {nom} حسب الجرعة: أعطني الجرعة.",
    },
    "remb_absent": {
        "fr": "Je n'ai pas le taux de remboursement {regime} de {nom} : demande a ton pharmacien.",
        "ary_lat": "Ma 3ndich t-taux dyal remboursement {regime} l {nom} : swwel pharmacien dyalek.",
        "ary_ar": "ما عنديش نسبة التعويض ديال {regime} ل {nom}: سوّل الصيدلي ديالك.",
        "ar": "لا تتوفر لدي نسبة تعويض {regime} عن {nom}: اسأل الصيدلي.",
    },
    "remb_aucun": {
        "fr": "Sans assurance maladie, {nom} n'est pas rembourse : tu paies le prix public.",
        "ary_lat": "Bla tamin, {nom} ma kayt3awedch : katkhelles taman kaml.",
        "ary_ar": "بلا تأمين، {nom} ما كيتعاودش: كتخلص الثمن كامل.",
        "ar": "بدون تأمين صحي، لا يُعوَّض {nom}: تدفع السعر الكامل.",
    },
    "formes_tete": {
        "fr": "{nom} existe au Maroc en :",
        "ary_lat": "{nom} kayn f lMaghrib b :",
        "ary_ar": "{nom} كاين فالمغرب ب:",
        "ar": "يوجد {nom} في المغرب بالأشكال التالية:",
    },
    "formes_coupee": {
        "fr": "(et d'autres dosages)",
        "ary_lat": "(w dosages khrin)",
        "ary_ar": "(وجرعات خرين)",
        "ar": "(وجرعات أخرى)",
    },
    "forme_existe": {
        "fr": "Oui, {nom} existe en {forme}.",
        "ary_lat": "Ah, {nom} kayn b {forme}.",
        "ary_ar": "إيه، {nom} كاين ب {forme}.",
        "ar": "نعم، يوجد {nom} على شكل {forme}.",
    },
    "forme_absente": {
        "fr": "Je ne trouve pas {nom} en {forme} au Maroc.",
        "ary_lat": "Ma l9itch {nom} b {forme} f lMaghrib.",
        "ary_ar": "ما لقيتش {nom} ب {forme} فالمغرب.",
        "ar": "لم أجد {nom} على شكل {forme} في المغرب.",
    },

    # --- Notice (securite) ---------------------------------------------------------
    "secu_tete": {
        "fr": "{rubrique} de {nom} :",
        "ary_lat": "{rubrique} dyal {nom} :",
        "ary_ar": "{rubrique} ديال {nom}:",
        "ar": "{rubrique} لـ {nom}:",
    },
    "secu_sans_explication": {
        "fr": "Je n'ai pas encore d'explication simple : le texte officiel est en dessous, ou demande a ton pharmacien.",
        "ary_lat": "Ma 3ndich chr7 sahl db : n-nass r-rasmi lte7t, wla swwel pharmacien dyalek.",
        "ary_ar": "ما عنديش شرح ساهل دابا: النص الرسمي لتحت، ولا سوّل الصيدلي ديالك.",
        "ar": "لا يتوفر لدي شرح مبسط حاليا: النص الرسمي أدناه، أو اسأل الصيدلي.",
    },
    "secu_absente": {
        "fr": "Je n'ai pas la notice de {nom} pour cette question : demande a ton pharmacien.",
        "ary_lat": "Ma 3ndich la notice dyal {nom} 3la had so2al : swwel pharmacien dyalek.",
        "ary_ar": "ما عنديش النشرة ديال {nom} على هاد السؤال: سوّل الصيدلي ديالك.",
        "ar": "لا تتوفر لدي نشرة {nom} بخصوص هذا السؤال: اسأل الصيدلي.",
    },
    "secu_rubrique_absente": {
        "fr": "La notice que j'ai pour {nom} ne parle pas de : {rubriques}. Demande a ton pharmacien.",
        "ary_lat": "La notice lli 3ndi l {nom} ma katheder 3la : {rubriques}. Swwel pharmacien dyalek.",
        "ary_ar": "النشرة اللي عندي ل {nom} ما كتهضرش على: {rubriques}. سوّل الصيدلي ديالك.",
        "ar": "النشرة التي لدي عن {nom} لا تتحدث عن: {rubriques}. اسأل الصيدلي.",
    },
    "rubrique_indications": {
        "fr": "A quoi sert", "ary_lat": "Fach kayn9e3", "ary_ar": "فاش كينفع", "ar": "دواعي الاستعمال",
    },
    "rubrique_effets_indesirables": {
        "fr": "Effets indesirables", "ary_lat": "Les effets secondaires", "ary_ar": "الأعراض الجانبية",
        "ar": "الآثار الجانبية",
    },
    "rubrique_contre_indications": {
        "fr": "Contre-indications", "ary_lat": "Chkoun ma khassouch yakhdo", "ary_ar": "شكون ما خاصوش ياخدو",
        "ar": "موانع الاستعمال",
    },
    "rubrique_precautions": {
        "fr": "Precautions", "ary_lat": "Les precautions", "ary_ar": "الاحتياطات", "ar": "الاحتياطات",
    },
    "rubrique_interactions": {
        "fr": "Interactions avec d'autres medicaments", "ary_lat": "M3a ach ma khassouch ytkhellet",
        "ary_ar": "مع آش ما خاصوش يتخلط", "ar": "التداخلات مع أدوية أخرى",
    },
    "rubrique_grossesse_allaitement": {
        "fr": "Grossesse et allaitement", "ary_lat": "L-7aml w r-rda3a", "ary_ar": "الحمل والرضاعة",
        "ar": "الحمل والرضاعة",
    },

    # --- Pharmacies ------------------------------------------------------------------
    "ph_proches": {
        "fr": "Les pharmacies les plus proches de {lieu} ({ville}) :",
        "ary_lat": "Pharmacies l9rab l {lieu} ({ville}) :",
        "ary_ar": "الصيدليات القراب ل {lieu} ({ville}):",
        "ar": "أقرب الصيدليات إلى {lieu} ({ville}):",
    },
    "ph_ville": {
        "fr": "Pharmacies a {ville} :",
        "ary_lat": "Pharmacies f {ville} :",
        "ary_ar": "الصيدليات ف {ville}:",
        "ar": "الصيدليات في {ville}:",
    },
    "ph_approx": {
        "fr": "(Quartier situe d'apres les adresses de l'annuaire : distances approximatives.)",
        "ary_lat": "(L-7ay 3ref blasto mn les adresses dyal l-annuaire : l-masafat ta9ribiya.)",
        "ary_ar": "(الحي عرفت بلاصتو من العناوين ديال الدليل: المسافات تقريبية.)",
        "ar": "(حُدّد موقع الحي من عناوين الدليل: المسافات تقريبية.)",
    },
    "ph_preciser_quartier": {
        "fr": "J'ai {n} pharmacies a {ville} : dans quel quartier es-tu ?",
        "ary_lat": "3ndi {n} pharmacie f {ville} : f ina 7ay nta ?",
        "ary_ar": "عندي {n} صيدلية ف {ville}: فأنهي حي نتا؟",
        "ar": "لدي {n} صيدلية في {ville}: في أي حي أنت؟",
    },
    "ph_quartier_inconnu": {
        "fr": "Je ne connais pas le quartier « {quartier} » a {ville}.",
        "ary_lat": "Ma kan3refch l-7ay « {quartier} » f {ville}.",
        "ary_ar": "ما كنعرفش الحي « {quartier} » ف {ville}.",
        "ar": "لا أعرف الحي « {quartier} » في {ville}.",
    },
    "ph_preciser_ville": {
        "fr": "« {lieu} » existe dans plusieurs villes ({villes}) : laquelle ?",
        "ary_lat": "« {lieu} » kayn f bzaf dyal l-mdoun ({villes}) : ina wa7da ?",
        "ary_ar": "« {lieu} » كاين فبزاف ديال المدن ({villes}): أنهي وحدة؟",
        "ar": "« {lieu} » موجود في عدة مدن ({villes}): أيها تقصد؟",
    },
    "ph_lieu_inconnu": {
        "fr": "Je ne connais pas le lieu « {lieu} ». Donne-moi ta ville et ton quartier.",
        "ary_lat": "Ma kan3refch « {lieu} ». 3tini l-mdina w l-7ay dyalek.",
        "ary_ar": "ما كنعرفش « {lieu} ». عطيني المدينة والحي ديالك.",
        "ar": "لا أعرف المكان « {lieu} ». أعطني مدينتك وحيّك.",
    },
    "garde_tete": {
        "fr": "Pharmacies ouvertes 24h/24 ou la nuit a {ville}, d'apres mon annuaire :",
        "ary_lat": "Pharmacies m7lolin 24h/24 wla f l-lil f {ville}, 3la 7sab l-annuaire dyali :",
        "ary_ar": "صيدليات محلولين 24/24 ولا فالليل ف {ville}، على حساب الدليل ديالي:",
        "ar": "صيدليات مفتوحة 24/24 أو ليلًا في {ville}، حسب دليلي:",
    },
    "garde_aucune": {
        "fr": "Je ne connais pas de pharmacie ouverte 24h/24 ou la nuit a {ville}.",
        "ary_lat": "Ma kan3ref 7ta pharmacie m7lola 24h/24 wla f l-lil f {ville}.",
        "ary_ar": "ما كنعرف حتى صيدلية محلولة 24/24 ولا فالليل ف {ville}.",
        "ar": "لا أعرف أي صيدلية مفتوحة 24/24 أو ليلًا في {ville}.",
    },
    "garde_aveu": {
        "fr": ("Je ne connais pas le tour de garde du jour, qui change chaque jour : la liste des "
               "pharmacies de garde est affichee sur la porte des pharmacies. Appelle avant de te "
               "deplacer."),
        "ary_lat": ("Ma kan3refch pharmacie de garde dyal lyoum, kattbeddel kol nhar : la liste "
                    "kat7ett 3la bab l-pharmacies. 3iyet 9bel ma tmchi."),
        "ary_ar": ("ما كنعرفش صيدلية الحراسة ديال اليوم، كتبدل كل نهار: اللائحة كتلصق على باب "
                   "الصيدليات. عيّط قبل ما تمشي."),
        "ar": ("لا أعرف صيدلية الحراسة لهذا اليوم، فهي تتغير يوميًا: تُعلَّق اللائحة على أبواب "
               "الصيدليات. اتصل قبل التنقل."),
    },
    "info_a_confirmer": {
        "fr": "Je pense que tu parles de {nom} (verifie le nom) :",
        "ary_lat": "Kan dhenn katqsed {nom} (t2akked mn smiya) :",
        "ary_ar": "كنظن كتقصد {nom} (تأكد من السمية):",
        "ar": "أظن أنك تقصد {nom} (تأكد من الاسم):",
    },
    "info_plusieurs": {
        "fr": "J'ai trouve {n} pharmacies de ce nom a {ville} :",
        "ary_lat": "L9it {n} pharmacies b had smiya f {ville} :",
        "ary_ar": "لقيت {n} صيدليات بهاد السمية ف {ville}:",
        "ar": "وجدت {n} صيدليات بهذا الاسم في {ville}:",
    },
    "info_introuvable": {
        "fr": "Je ne trouve pas la pharmacie « {nom} ».",
        "ary_lat": "Ma l9itch l-pharmacie « {nom} ».",
        "ary_ar": "ما لقيتش الصيدلية « {nom} ».",
        "ar": "لم أجد الصيدلية « {nom} ».",
    },
    "info_introuvable_ville": {
        "fr": "Je ne trouve pas de pharmacie « {nom} » a {ville}.",
        "ary_lat": "Ma l9it 7ta pharmacie « {nom} » f {ville}.",
        "ary_ar": "ما لقيت حتى صيدلية « {nom} » ف {ville}.",
        "ar": "لم أجد صيدلية « {nom} » في {ville}.",
    },
    "info_lieu_inconnu": {
        "fr": "(Je n'ai pas reconnu le lieu « {lieu} » : j'ai cherche dans tout le Maroc.)",
        "ary_lat": "(Ma 3reftch « {lieu} » : 9elleb f lMaghrib kaml.)",
        "ary_ar": "(ما عرفتش « {lieu} »: قلبت فالمغرب كامل.)",
        "ar": "(لم أتعرف على المكان « {lieu} »: بحثت في المغرب كله.)",
    },
    "tel": {"fr": "Tel.", "ary_lat": "Tel", "ary_ar": "التيليفون", "ar": "الهاتف"},
    "ouverture_24h": {"fr": "ouverte 24h/24", "ary_lat": "m7lola 24h/24", "ary_ar": "محلولة 24/24",
                      "ar": "مفتوحة 24/24"},
    "ouverture_nuit": {"fr": "ouverte la nuit ({horaires})", "ary_lat": "m7lola f l-lil ({horaires})",
                       "ary_ar": "محلولة فالليل ({horaires})", "ar": "مفتوحة ليلًا ({horaires})"},
    "et_autres": {"fr": " et {n} autres", "ary_lat": " w {n} khrin", "ary_ar": " و {n} خرين",
                  "ar": " و {n} أخرى"},

    # --- Conseil symptomes ----------------------------------------------------------
    "conseil_enfant": {
        "fr": ("Pour un enfant, je ne conseille pas de medicament : demande a un pharmacien ou a un "
               "medecin avant de lui donner quoi que ce soit."),
        "ary_lat": ("L drari sghar, ma kan9tare7ch dwa : swwel pharmacien wla tbib 9bel ma t3tih "
                    "ay 7aja."),
        "ary_ar": "للدراري الصغار، ما كنقترحش دوا: سوّل الصيدلي ولا الطبيب قبل ما تعطيه أي حاجة.",
        "ar": "بالنسبة للأطفال، لا أقترح أي دواء: اسأل صيدليًا أو طبيبًا قبل أن تعطيه أي شيء.",
    },
    "conseil_bebe": {
        "fr": ("Pour un bebe, je ne conseille pas de medicament : demande a un medecin ou a un "
               "pharmacien avant de lui donner quoi que ce soit."),
        "ary_lat": "L l-bebe, ma kan9tare7ch dwa : swwel tbib wla pharmacien 9bel ma t3tih ay 7aja.",
        "ary_ar": "للبيبي، ما كنقترحش دوا: سوّل الطبيب ولا الصيدلي قبل ما تعطيه أي حاجة.",
        "ar": "بالنسبة للرضيع، لا أقترح أي دواء: اسأل طبيبًا أو صيدليًا قبل أن تعطيه أي شيء.",
    },
    "conseil_grossesse": {
        "fr": ("Pendant la grossesse, je ne conseille pas de medicament : demande a ton medecin ou a "
               "ton pharmacien avant de prendre quoi que ce soit."),
        "ary_lat": ("F l-7aml, ma kan9tare7ch dwa : swwel tbib wla pharmacien dyalek 9bel ma takhdi "
                    "ay 7aja."),
        "ary_ar": "فالحمل، ما كنقترحش دوا: سوّلي الطبيب ولا الصيدلي ديالك قبل ما تاخدي أي حاجة.",
        "ar": "أثناء الحمل، لا أقترح أي دواء: اسألي طبيبك أو صيدليك قبل تناول أي شيء.",
    },
    "conseil_molecule": {
        "fr": ("Pour {symptome} : demande a ton pharmacien un medicament a base de {molecules}. "
               "Pas plus de {duree} sans avis medical."),
        "ary_lat": ("L {symptome} : swwel pharmacien dyalek 3la dwa fih {molecules}. Ma tfoutch "
                    "{duree} bla ma tchouf tbib."),
        "ary_ar": ("ل{symptome}: سوّل الصيدلي ديالك على دوا فيه {molecules}. ما تفوتش {duree} بلا "
                   "ما تشوف الطبيب."),
        "ar": ("بالنسبة لـ{symptome}: اطلب من الصيدلي دواءً يحتوي على {molecules}. لا تتجاوز {duree} "
               "دون استشارة طبية."),
    },
    "conseil_orientation": {
        "fr": "Pour {symptome}, demande conseil a ton {pro} : il te dira quoi prendre.",
        "ary_lat": "L {symptome}, swwel {pro} dyalek : howa lli ghadi ygoul lik chnou takhod.",
        "ary_ar": "ل{symptome}، سوّل {pro} ديالك: هو اللي غادي يقول ليك شنو تاخد.",
        "ar": "بالنسبة لـ{symptome}، اطلب النصيحة من {pro}: سيخبرك بما يمكنك تناوله.",
    },
    "conseil_trop_long": {
        "fr": "{symptome} depuis plus de {duree} : il faut voir un medecin.",
        "ary_lat": "{symptome} kter mn {duree} : khassek tchouf tbib.",
        "ary_ar": "{symptome} كثر من {duree}: خاصك تشوف الطبيب.",
        "ar": "{symptome} منذ أكثر من {duree}: يجب أن ترى طبيبًا.",
    },
    "conseil_inconnu": {
        "fr": "Pour ce symptome, je n'ai pas de conseil : demande a ton pharmacien.",
        "ary_lat": "Had l-3ard ma 3ndi fih 7ta nasi7a : swwel pharmacien dyalek.",
        "ary_ar": "هاد العرض ما عندي فيه حتى نصيحة: سوّل الصيدلي ديالك.",
        "ar": "ليست لدي نصيحة لهذا العَرَض: اسأل الصيدلي.",
    },
    "conseil_alerte": {
        "fr": "Va voir un medecin sans attendre en cas de : {signes}.",
        "ary_lat": "Ila tzad l-7al wla ban chi 7aja ghriba, chouf tbib bla ma tsenna.",
        "ary_ar": "إلا تزادت الحالة ولا بان شي حاجة غريبة، شوف الطبيب بلا ما تسنى.",
        "ar": "إذا ساءت الحالة أو ظهر عرض غير عادي، راجع الطبيب دون انتظار.",
    },
    "conseil_fin": {
        "fr": "Si ca ne passe pas, va voir ton {pro}.",
        "ary_lat": "Ila ma dazch, chouf {pro} dyalek.",
        "ary_ar": "إلا ما دازش، شوف {pro} ديالك.",
        "ar": "إذا لم يزل، راجع {pro}.",
    },
    "pro_pharmacien": {"fr": "pharmacien", "ary_lat": "pharmacien", "ary_ar": "الصيدلي", "ar": "الصيدلي"},
    "pro_medecin": {"fr": "medecin", "ary_lat": "tbib", "ary_ar": "الطبيب", "ar": "الطبيب"},
    "pro_dentiste": {"fr": "dentiste", "ary_lat": "tbib d snan", "ary_ar": "طبيب السنان",
                     "ar": "طبيب الأسنان"},
    "jour": {"fr": "1 jour", "ary_lat": "nhar", "ary_ar": "نهار", "ar": "يوم واحد"},
    "jours": {"fr": "{n} jours", "ary_lat": "{n} ayam", "ary_ar": "{n} أيام", "ar": "{n} أيام"},
    "et": {"fr": " et ", "ary_lat": " w ", "ary_ar": " و", "ar": " و"},
    "ou": {"fr": " ou ", "ary_lat": " wla ", "ary_ar": " ولا ", "ar": " أو "},
    "dh": {"fr": "DH", "ary_lat": "DH", "ary_ar": "درهم", "ar": "درهم"},
}


def t(langue: str, cle: str, **params) -> str:
    """Phrase `cle` dans `langue` (francais si la traduction manque)."""
    variantes = TEXTES[cle]
    modele = variantes.get(langue) or variantes[LANGUE_PAR_DEFAUT]
    return modele.format(**params) if params else modele
