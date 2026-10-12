"""Les seules phrases fixes du bot, dans les quatre langues de reponse : celles
qu'il doit pouvoir dire SANS LLM (urgence, service en panne). Tout le reste
est redige par le LLM a partir des fiches (nlp/rag/repondre.md).

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

    # --- Aucun fournisseur LLM ne repond ----------------------------------------
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
}


def t(langue: str, cle: str, **params) -> str:
    """Phrase `cle` dans `langue` (francais si la traduction manque)."""
    variantes = TEXTES[cle]
    modele = variantes.get(langue) or variantes[LANGUE_PAR_DEFAUT]
    return modele.format(**params) if params else modele
