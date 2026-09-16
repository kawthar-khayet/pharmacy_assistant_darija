"""Build the NLU seed dataset (intent + NER) for the pharmacy assistant.

Each raw example lists the text, language, intent, and the entity VALUES
(substrings) rather than manual char offsets -- offsets are computed
automatically via str.find(), so authors never have to count characters
by hand and offsets can never silently drift from the text.

Output: nlu/seed_dataset.jsonl, one JSON object per line:
  {"id", "text", "lang", "intent", "entities": [{"type","value","start","end"}]}
"""
import json
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parent / "seed_dataset.jsonl"

# (text, lang, intent, [(entity_type, value), ...])
RAW_EXAMPLES = [
    # --- disponibilite_medicament ---
    ("wach kayn doliprane?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "doliprane")]),
    ("wach 3andkom doliprane 1g?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "doliprane"), ("DOSAGE", "1g")]),
    ("واش عندكم دوليبران 1 گرام؟", "ary_ar", "disponibilite_medicament",
     [("MEDICAMENT", "دوليبران"), ("DOSAGE", "1 گرام")]),
    ("je cherche doliprane 500mg", "fr", "disponibilite_medicament",
     [("MEDICAMENT", "doliprane"), ("DOSAGE", "500mg")]),
    ("avez-vous du paracetamol en stock ?", "fr", "disponibilite_medicament",
     [("MEDICAMENT", "paracetamol")]),
    ("هل يتوفر لديكم دوليبران؟", "ar", "disponibilite_medicament",
     [("MEDICAMENT", "دوليبران")]),
    ("wach kayn doliprane 1g? bghit juj boites", "mixte", "disponibilite_medicament",
     [("MEDICAMENT", "doliprane"), ("DOSAGE", "1g"), ("QUANTITE", "juj"), ("FORME", "boites")]),
    ("wach 3andkom sirop dyal la toux?", "mixte", "disponibilite_medicament",
     [("FORME", "sirop")]),
    ("hani labas, bghit doliprane 500mg wa7ed 3elba", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "doliprane"), ("DOSAGE", "500mg"), ("QUANTITE", "wa7ed"), ("FORME", "3elba")]),
    ("est-ce que vous avez de l'amoxicilline 500 mg ?", "fr", "disponibilite_medicament",
     [("MEDICAMENT", "amoxicilline"), ("DOSAGE", "500 mg")]),
    ("kayn dolipran 1g chez vous ?", "mixte", "disponibilite_medicament",
     [("MEDICAMENT", "dolipran"), ("DOSAGE", "1g")]),
    ("3andkom efferalgan?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "efferalgan")]),

    # --- prix_remboursement ---
    ("chhal taman doliprane?", "ary_lat", "prix_remboursement",
     [("MEDICAMENT", "doliprane")]),
    ("شحال ثمن doliprane؟", "mixte", "prix_remboursement",
     [("MEDICAMENT", "doliprane")]),
    ("quel est le prix du efferalgan 1g ?", "fr", "prix_remboursement",
     [("MEDICAMENT", "efferalgan"), ("DOSAGE", "1g")]),
    ("est-ce que le doliprane est rembourse ?", "fr", "prix_remboursement",
     [("MEDICAMENT", "doliprane")]),
    ("قداش تمن الأموكسيسيلين؟", "ar", "prix_remboursement",
     [("MEDICAMENT", "الأموكسيسيلين")]),
    ("wach doliprane 1g marboul m3a CNOPS?", "ary_lat", "prix_remboursement",
     [("MEDICAMENT", "doliprane"), ("DOSAGE", "1g")]),
    ("bghit na3ref chhal ghadi tkhalasni doliprane", "ary_lat", "prix_remboursement",
     [("MEDICAMENT", "doliprane")]),

    # --- info_pharmacie ---
    ("فين كاينة الصيدلية؟", "ar", "info_pharmacie", []),
    ("fin kayna sidalia dyal l7ay?", "ary_lat", "info_pharmacie",
     [("LOCALISATION", "l7ay")]),
    ("quel est le numero de telephone de la pharmacie Al Amal ?", "fr", "info_pharmacie",
     [("PHARMACIE", "Al Amal")]),
    ("ach homa horaires dyal sidalia?", "ary_lat", "info_pharmacie", []),
    ("quelle est la pharmacie de garde la plus proche de Maarif ?", "fr", "info_pharmacie",
     [("LOCALISATION", "Maarif")]),
    ("ما هي ساعات عمل الصيدلية؟", "ar", "info_pharmacie", []),
    ("wach sidalia Ibn Sina 7alla daba?", "ary_lat", "info_pharmacie",
     [("PHARMACIE", "Ibn Sina")]),

    # --- posologie_information ---
    ("kifach nakhod doliprane 500mg?", "ary_lat", "posologie_information",
     [("MEDICAMENT", "doliprane"), ("DOSAGE", "500mg")]),
    ("comment prendre l'amoxicilline 500mg trois fois par jour ?", "fr", "posologie_information",
     [("MEDICAMENT", "amoxicilline"), ("DOSAGE", "500mg")]),
    ("كيفاش ناخد الدواء؟", "ary_ar", "posologie_information", []),
    ("est-ce que je peux prendre doliprane 1g a jeun ?", "fr", "posologie_information",
     [("MEDICAMENT", "doliprane"), ("DOSAGE", "1g")]),
    ("chhal men marra nakhod efferalgan f nhar?", "ary_lat", "posologie_information",
     [("MEDICAMENT", "efferalgan")]),

    # --- commande_reservation ---
    ("bghit njib juj boites dyal doliprane 1g", "ary_lat", "commande_reservation",
     [("QUANTITE", "juj"), ("FORME", "boites"), ("MEDICAMENT", "doliprane"), ("DOSAGE", "1g")]),
    ("je veux reserver trois boites de paracetamol", "fr", "commande_reservation",
     [("QUANTITE", "trois"), ("FORME", "boites"), ("MEDICAMENT", "paracetamol")]),
    ("bghit n7goz doliprane", "ary_lat", "commande_reservation",
     [("MEDICAMENT", "doliprane")]),
    ("il me faut 2 boites de doliprane 1g", "fr", "commande_reservation",
     [("QUANTITE", "2"), ("FORME", "boites"), ("MEDICAMENT", "doliprane"), ("DOSAGE", "1g")]),
    ("bghit nchri wa7ed 3elba dyal efferalgan", "ary_lat", "commande_reservation",
     [("QUANTITE", "wa7ed"), ("FORME", "3elba"), ("MEDICAMENT", "efferalgan")]),

    # --- salutation ---
    ("salam", "ary_lat", "salutation", []),
    ("السلام عليكم", "ar", "salutation", []),
    ("bonjour", "fr", "salutation", []),
    ("choukrane bzaf", "ary_lat", "salutation", []),
    ("merci beaucoup", "fr", "salutation", []),
    ("bslama", "ary_lat", "salutation", []),

    # --- autre (hors perimetre / fallback) ---
    ("j'ai mal a la tete, quel medicament je peux prendre ?", "fr", "autre", []),
    ("3andi sda3, ach ndir?", "ary_lat", "autre", []),
    ("quelle heure est-il ?", "fr", "autre", []),
    ("راني مريض بزاف", "ary_ar", "autre", []),

    # ============================================================
    # Extension : fautes d'orthographe, davantage de variantes darija,
    # quantites en toutes lettres, entites combinees, cas "autre".
    # ============================================================

    # --- disponibilite_medicament : fautes d'orthographe medicament ---
    ("wach 3andkom dolipran?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "dolipran")]),
    ("est-ce que vous avez de l'efferalgant 1g ?", "fr", "disponibilite_medicament",
     [("MEDICAMENT", "efferalgant"), ("DOSAGE", "1g")]),
    ("3andkom amoxiciline 500?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "amoxiciline"), ("DOSAGE", "500")]),
    ("wach kayn ventolin f sidalia?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "ventolin")]),
    ("bghit nchouf wach 3andkom augmentine", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "augmentine")]),
    ("avez vous du voltarene gel ?", "fr", "disponibilite_medicament",
     [("MEDICAMENT", "voltarene"), ("FORME", "gel")]),
    ("wach 3andkom smecta l tfal?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "smecta")]),
    ("est ce que aspegik disponible?", "mixte", "disponibilite_medicament",
     [("MEDICAMENT", "aspegik")]),
    ("ma3andkomch immodium?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "immodium")]),
    ("kayn clamoxyl 500 mg ola la?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "clamoxyl"), ("DOSAGE", "500 mg")]),
    ("wach spasfon lyoc mawjoud?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "spasfon lyoc")]),
    ("عندكم فلاجيل؟", "ary_ar", "disponibilite_medicament",
     [("MEDICAMENT", "فلاجيل")]),
    ("hal yatawafar dawa flagyl 500?", "ary_lat", "disponibilite_medicament",
     [("MEDICAMENT", "flagyl"), ("DOSAGE", "500")]),
    ("bghit nchri comprime dyal doliprane", "ary_lat", "disponibilite_medicament",
     [("FORME", "comprime"), ("MEDICAMENT", "doliprane")]),
    ("est-ce que vous avez des gelules d'amoxicilline?", "fr", "disponibilite_medicament",
     [("FORME", "gelules"), ("MEDICAMENT", "amoxicilline")]),
    ("wach 3andkom suppositoire dyal doliprane l drari?", "ary_lat", "disponibilite_medicament",
     [("FORME", "suppositoire"), ("MEDICAMENT", "doliprane")]),
    ("bghit pommade dyal voltarene", "ary_lat", "disponibilite_medicament",
     [("FORME", "pommade"), ("MEDICAMENT", "voltarene")]),

    # --- prix_remboursement : fautes + variantes ---
    ("chhal taman dolipran 1g?", "ary_lat", "prix_remboursement",
     [("MEDICAMENT", "dolipran"), ("DOSAGE", "1g")]),
    ("combien coute l'augmentine 1g?", "fr", "prix_remboursement",
     [("MEDICAMENT", "augmentine"), ("DOSAGE", "1g")]),
    ("قداش تمن سميكتا؟", "ary_ar", "prix_remboursement",
     [("MEDICAMENT", "سميكتا")]),
    ("wach spasfon marboul m3a l assurance?", "ary_lat", "prix_remboursement",
     [("MEDICAMENT", "spasfon")]),
    ("taux remboursement dyal voltarene chhal?", "mixte", "prix_remboursement",
     [("MEDICAMENT", "voltarene")]),
    ("hal amoxicilline mashmoula bi at-ta'min?", "ary_lat", "prix_remboursement",
     [("MEDICAMENT", "amoxicilline")]),

    # --- info_pharmacie : variantes localisation/pharmacie ---
    ("chnou howa ra9m telephone dyal sidalia?", "ary_lat", "info_pharmacie", []),
    ("y'a-t-il une pharmacie de garde a Agdal ce soir ?", "fr", "info_pharmacie",
     [("LOCALISATION", "Agdal")]),
    ("fin kayna sidalia lqrib li Hay Hassani?", "ary_lat", "info_pharmacie",
     [("LOCALISATION", "Hay Hassani")]),
    ("adresse dyal pharmacie Bennani fin hiya?", "mixte", "info_pharmacie",
     [("PHARMACIE", "Bennani")]),
    ("واش الصيدلية حلة داب؟", "ary_ar", "info_pharmacie", []),
    ("quels sont les horaires d'ouverture de la pharmacie Centrale ?", "fr", "info_pharmacie",
     [("PHARMACIE", "Centrale")]),
    ("bghit ra9m telephone dyal sidalia dyal Maarif", "ary_lat", "info_pharmacie",
     [("LOCALISATION", "Maarif")]),

    # --- posologie_information : variantes ---
    ("chhal men fois nakhod amoxicilline f nhar?", "ary_lat", "posologie_information",
     [("MEDICAMENT", "amoxicilline")]),
    ("dois-je prendre voltarene avant ou apres manger ?", "fr", "posologie_information",
     [("MEDICAMENT", "voltarene")]),
    ("كم مرة ناخد سبازفون في اليوم؟", "ary_ar", "posologie_information",
     [("MEDICAMENT", "سبازفون")]),
    ("wach doliprane 1g khass ykoun m3a makla?", "ary_lat", "posologie_information",
     [("MEDICAMENT", "doliprane"), ("DOSAGE", "1g")]),
    ("quelle est la dose maximale de doliprane par jour ?", "fr", "posologie_information",
     [("MEDICAMENT", "doliprane")]),

    # --- commande_reservation : quantites en toutes lettres darija ---
    ("bghit tlata 3olab dyal spasfon", "ary_lat", "commande_reservation",
     [("QUANTITE", "tlata"), ("FORME", "3olab"), ("MEDICAMENT", "spasfon")]),
    ("je voudrais commander cinq boites d'amoxicilline 500mg", "fr", "commande_reservation",
     [("QUANTITE", "cinq"), ("FORME", "boites"), ("MEDICAMENT", "amoxicilline"), ("DOSAGE", "500mg")]),
    ("bghit rb3a 3elab dyal doliprane 500mg", "ary_lat", "commande_reservation",
     [("QUANTITE", "rb3a"), ("FORME", "3elab"), ("MEDICAMENT", "doliprane"), ("DOSAGE", "500mg")]),
    ("reserve li khamsa boites dyal efferalgan", "ary_lat", "commande_reservation",
     [("QUANTITE", "khamsa"), ("FORME", "boites"), ("MEDICAMENT", "efferalgan")]),
    ("je passe commande pour une boite de voltarene", "fr", "commande_reservation",
     [("QUANTITE", "une"), ("FORME", "boite"), ("MEDICAMENT", "voltarene")]),
    ("7goz liya doliprane, ghadi njiha ghdda", "ary_lat", "commande_reservation",
     [("MEDICAMENT", "doliprane")]),

    # --- salutation : plus de variantes ---
    ("salam alaykoum", "ary_lat", "salutation", []),
    ("wa alaykoum salam", "ary_lat", "salutation", []),
    ("bonsoir", "fr", "salutation", []),
    ("yallah bslama", "ary_lat", "salutation", []),
    ("شكرا بزاف", "ary_ar", "salutation", []),
    ("au revoir et merci", "fr", "salutation", []),
    ("labas 3lik", "ary_lat", "salutation", []),

    # --- autre : hors perimetre ---
    ("quel temps fait-il aujourd'hui ?", "fr", "autre", []),
    ("bghit na3ref ach kayn f akhbar", "ary_lat", "autre", []),
    ("est-ce que le coronavirus est dangereux ?", "fr", "autre", []),
    ("3tini chi wa9t bach nji l tabib", "ary_lat", "autre", []),
    ("ما هو أفضل مطعم قريب مني؟", "ar", "autre", []),
]


def build():
    records = []
    for i, (text, lang, intent, entities) in enumerate(RAW_EXAMPLES, start=1):
        record_entities = []
        for etype, value in entities:
            start = text.find(value)
            if start == -1:
                raise ValueError(f"Entity value {value!r} not found in text {text!r}")
            record_entities.append({
                "type": etype,
                "value": value,
                "start": start,
                "end": start + len(value),
            })
        records.append({
            "id": f"seed_{i:04d}",
            "text": text,
            "lang": lang,
            "intent": intent,
            "entities": record_entities,
        })

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} examples to {OUT_PATH}")

    intent_counts = {}
    lang_counts = {}
    for r in records:
        intent_counts[r["intent"]] = intent_counts.get(r["intent"], 0) + 1
        lang_counts[r["lang"]] = lang_counts.get(r["lang"], 0) + 1
    print("Par intent:", intent_counts)
    print("Par langue:", lang_counts)


if __name__ == "__main__":
    build()
