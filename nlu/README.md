# NLU — Intents & Entities (Challenge #1)

## Fichiers
- `schema.json` — taxonomie v2 : 8 intents, 6 types d'entites, avec description et langues supportees.
- `build_seed_dataset.py` — genere `seed_dataset.jsonl` a partir d'exemples bruts (texte + valeurs d'entites) ; les offsets de caracteres sont calcules automatiquement (`str.find`), jamais comptes a la main.
- `seed_dataset.jsonl` — 121 exemples de bootstrap, repartis sur les 8 intents et 5 variantes linguistiques (fr, ar, darija graphie arabe, darija graphie latine, mixte), avec fautes d'orthographe volontaires sur les noms de medicaments.
- `llm_prototype.py` — prototype NLU par LLM few-shot via **Ollama Cloud** (endpoint OpenAI-compatible `https://ollama.com/v1`, modele par defaut `gpt-oss:20b-cloud` — accessible en tier gratuit ; `qwen3.5:cloud`, teste en premier pour son meilleur support multilingue, renvoie HTTP 402 "requires a subscription"). Construit le prompt systeme depuis `schema.json` + 11 exemples de `seed_dataset.jsonl` (au moins un par intention), renvoie un JSON valide `{intent, entities}`. Le prompt pose explicitement que `sidalia` / `saydalia` / `صيدلية` / `pharmacie` sont des noms COMMUNS et jamais des entites `PHARMACIE` (seul le nom propre l'est : dans "sidalia Ibn Sina", l'entite est "Ibn Sina") — sans cette regle le modele annotait le mot lui-meme, ce qui causait 5 des 11 ecarts d'entites de l'evaluation. Necessite `OLLAMA_API_KEY` (cle creee sur ollama.com/settings/keys) dans un fichier `.env` a la racine du projet (`OLLAMA_API_KEY=...`) — plus fiable qu'une variable d'environnement shell, chaque appel d'outil tournant dans son propre process. Modele configurable via `OLLAMA_MODEL`.
- `evaluate.py` — evalue `llm_prototype.py` sur les 90 exemples qui ne servent pas de few-shot (Intent Accuracy + Entity F1). Meme prerequis ; un second passage reprend les exemples en echec (surcharges passageres d'Ollama). **Resultat (gpt-oss:20b-cloud, 90 exemples)** : intent 97,8 %, entites F1 98,6 % — voir « Resultats » plus bas.
- `baseline.py` — NLU classique pour comparaison : TF-IDF sur n-grammes de caracteres + regression logistique pour l'intent, regles et lexiques pour les entites. Lexiques ecrits a partir de connaissances generales, jamais a partir des annotations de test.
- `compare_baseline.py` — compare le LLM et la baseline sur exactement les memes 90 phrases (validation croisee a 5 plis pour la baseline, few-shot ajoutes a chaque entrainement). Sans appel payant ; ecrit `comparison_results.json`.
- `entity_linking.py` — resolution d'un nom de medicament (potentiellement mal orthographie ou en arabe) contre `data/clean/medicaments_reference.csv`, via normalisation + RapidFuzz + une petite table de translitteration arabe→latin. Aucune dependance externe payante, s'utilise directement en CLI : `python nlu/entity_linking.py "dolipran" "1g"`.
- `evaluate_entity_linking.py` — evaluation locale (sans cout) du matcher sur 22 cas manuels (fautes d'orthographe + arabe) : **100% top-1** actuellement.
- `pharmacy_linking.py` — meme approche (normalisation + RapidFuzz) pour resoudre les entites `PHARMACIE`/`LOCALISATION` contre `data/clean/pharmacies_reference.csv` (2652 pharmacies scrapees depuis saydalia.ma). Recherche par nom, par localisation (ville, avec repli sur recherche en sous-chaine dans l'adresse pour les quartiers), ou les deux combines (la localisation filtre d'abord le pool, ce qui evite les confusions entre plusieurs pharmacies homonymes dans des villes differentes). CLI : `python nlu/pharmacy_linking.py "Ibn Sina" "Casablanca"` (ou `""` pour le nom si recherche par lieu seul).
- `evaluate_pharmacy_linking.py` — evaluation locale sur 10 cas nominatifs (dont fautes de frappe) + 3 cas de recherche par localisation : **90% top-1** (le seul "echec" est un cas ambigu de deux pharmacies homonymes dans des villes differentes, comportement attendu sans indice de localisation).

## Intents (8) — taxonomie v2
| id | description | phrases |
|---|---|---|
| `disponibilite_medicament` | le patient cherche un medicament : disponibilite, achat, reservation, commande | 40 |
| `prix_remboursement` | prix et/ou taux de remboursement | 13 |
| `alternative_moins_chere` | equivalent, generique ou alternative moins chere | 11 |
| `info_pharmacie` | coordonnees, horaires, pharmacie de garde | 14 |
| `posologie_information` | comment/quand prendre un medicament | 10 |
| `conseil_medical` | symptome, maladie, question medicale : orienter vers un professionnel | 10 |
| `salutation` | politesse, small talk | 13 |
| `hors_sujet` | sans rapport avec les medicaments, les pharmacies ou la sante | 10 |

Changements par rapport a la v1 (detail et justification : [docs/changements_intentions.md](../docs/changements_intentions.md)) :
- `commande_reservation` est fusionnee dans `disponibilite_medicament` : l'API les traitait de facon identique, et leur frontiere etait la premiere source d'erreurs ;
- `autre` est scinde en `conseil_medical` (redirection vers un professionnel, numeros d'urgence) et `hors_sujet` ;
- `alternative_moins_chere` est nouvelle.

## Entites (6)
`MEDICAMENT`, `DOSAGE`, `FORME`, `QUANTITE`, `PHARMACIE`, `LOCALISATION` — voir `schema.json` pour le detail et le lien avec `data/clean/medicaments_reference.csv`.

## Format d'un exemple (`seed_dataset.jsonl`)
```json
{
  "id": "seed_0007",
  "text": "wach kayn doliprane 1g? bghit juj boites",
  "lang": "mixte",
  "intent": "disponibilite_medicament",
  "entities": [
    {"type": "MEDICAMENT", "value": "doliprane", "start": 10, "end": 19},
    {"type": "DOSAGE", "value": "1g", "start": 20, "end": 22},
    {"type": "QUANTITE", "value": "juj", "start": 33, "end": 36},
    {"type": "FORME", "value": "boites", "start": 37, "end": 43}
  ]
}
```
Offsets = index caractere Python (`text[start:end] == value`). Un exemple sans entite a `"entities": []` (cas `salutation`, `conseil_medical`, `hors_sujet`, ou intent info_pharmacie sans mention explicite de lieu/nom).

## Equivalents moins chers (`alternative_moins_chere`)
`entity_linking.equivalents()` cherche les produits de **meme composition** (DCI identique), **meme dosage** et **meme voie d'administration**, disponibles en officine, du moins cher au plus cher. Trois garde-fous, chacun ajoute apres un cas faux observe :
- **composition fiable uniquement** : la liste CNSS decoupe une association en une ligne par molecule (l'Augmentin y apparait comme « amoxicilline » seule). Seules les lignes AMMPS et CNOPS, qui donnent la composition complete, sont utilisees -- sans cela, NEOMOX (amoxicilline seule, injectable) etait propose a la place de l'Augmentin ;
- **meme famille de forme** (orale solide, orale liquide, poudre orale, injectable, rectale, cutanee...) : sans cela, un suppositoire etait propose a la place d'un comprime ;
- **disponible en officine** : les produits « Non Commercialise », « Retire » ou « Suspendu » du marche, vendus a l'export ou sur appel d'offres hospitalier sont exclus.

## Resultats
Sur les 110 phrases de test (hors 11 few-shot), taxonomie v2 :

| | LLM few-shot | Baseline |
|---|---|---|
| Intent — exactitude | **98,2 %** | 62,7 % |
| Intent — F1 macro | **97,9 %** | 53,8 % |
| Entites — precision | 97,6 % | 97,5 % |
| Entites — rappel | 97,6 % | 93,5 % |
| Entites — F1 | **97,6 %** | 95,4 % |

- **Les trois nouvelles intentions sont reconnues a 100 %** : `alternative_moins_chere` 10/10, `conseil_medical` 9/9, `hors_sujet` 9/9 (pieges compris).
- **L'intent reste le point fort du LLM.** Avec 8 intents et 9 a 10 exemples pour la plupart, la baseline statistique manque d'exemples (62,7 %).
- **Les entites restent proches** entre les deux approches. Les 3 ecarts du LLM : deux articles elides (« l'efferalgan », « l'amoxicilline ») et « sirop dyal la toux » pris pour un medicament.
- **Les 2 erreurs d'intent** : « كيفاش ناخد الدواء؟ » (posologie sans nom de medicament, predit `conseil_medical`) et « hal amoxicilline mashmoula bi at-ta'min? » (arabe standard translittere).

Le detail, la comparaison avec la v1 (97,8 % / 98,6 % sur 90 phrases et 7 intents) et ses limites sont dans [docs/changements_intentions.md](../docs/changements_intentions.md).

**Limites du protocole** : phrases ecrites par l'equipe, pas des messages reels de patients ; petits sous-groupes (4 phrases en arabe standard) ; temperature 0 sans garantie de determinisme cote service.

## Comment etendre le dataset
Ajouter des tuples dans `RAW_EXAMPLES` de `build_seed_dataset.py` : `(text, lang, intent, [(ENTITY_TYPE, "valeur exacte presente dans text"), ...])`, puis relancer le script. Il valide automatiquement que chaque valeur d'entite existe bien dans le texte (leve une erreur sinon) — impossible d'introduire un offset faux.

## Usage prevu
1. **Prototype rapide (LLM few-shot)** : injecter `schema.json` (intents + entites) dans le prompt systeme + quelques exemples de `seed_dataset.jsonl`, demander une sortie JSON strictement conforme au schema.
2. **Fine-tuning local** (AraBERT/DarijaBERT ou equivalent) : `seed_dataset.jsonl` sert de depart ; a etoffer (cible indicative : 500-1500 exemples, en ajoutant des variantes orthographiques de medicaments, des fautes de frappe, plus d'exemples reels/valides) avant entrainement.
3. **Comparaison A/B/C** (LLM few-shot vs fine-tune vs hybride) : ce meme fichier sert de test set commun pour comparer Intent Accuracy / NER F1 entre approches.

## Entity Linking — resultats et limites
`entity_linking.py` implemente l'etape recommandee "normalisation + RapidFuzz" (avant d'envisager des embeddings si besoin) :
1. normalisation (accents, casse, ponctuation) ;
2. translitteration arabe→latin (`translitteration.py`) : table de correspondances pour les cas connus, puis transcription lettre a lettre pour tout le reste ;
3. fuzzy matching (`rapidfuzz.fuzz.WRatio`) contre les colonnes `nom` ET `dci` de la reference, avec un filtre optionnel par dosage ;
   les variantes renvoyees portent les taux des **deux** regimes (`taux_remboursement_cnops` et `taux_remboursement_cnss`), un produit pouvant etre pris en charge par l'un et pas par l'autre ;
4. score de confiance par palier : `auto` (>=90), `a_confirmer` (70-89), `non_fiable` (<70) ;
5. garde-fou anti-bruit : `WRatio` (qui sert au classement) integre `partial_ratio`, lequel
   note tres haut un nom court quasi-inclus dans une requete longue -- "BIDON INEXISTANTE
   XYZ123" ressortait ainsi sur OXISTAT a 77, donc `a_confirmer`, soit un vrai medicament
   propose pour une requete qui ne veut rien dire. Un controle mot-a-mot
   (`best_token_similarity`, seuil `TOKEN_OVERLAP_FLOOR = 75`) rabat ces cas en
   `non_fiable`. Il est compare a la chaine qui a reellement produit le match : le `nom`
   pour un match direct, mais la `dci` pour un match indirect, sinon une resolution
   legitime par DCI (requete "ibuprofene" -> ADFENE) serait rejetee a tort ;
6. **passe phonetique** : une troisieme comparaison, sur la cle sonore (`cle_phonetique`)
   de la requete et des noms de la base. Elle rattrape ce que la comparaison lettre a
   lettre ne rapproche pas -- typiquement un nom dicte en arabe, ou l'arabe n'a ni p ni v
   et ne note pas les voyelles breves : "دوليبران" se translittere "doulibran", a 66 de
   DOLIPRANE en toutes lettres, mais les deux se reduisent a la meme cle `dolibran`.
   Un candidat trouve par cette passe est decote de 5 %, son garde-fou anti-bruit est
   releve (`TOKEN_OVERLAP_FLOOR_PHON = 85`, la cle rapprochant plus facilement deux mots
   sans rapport), et il est rabattu en `a_confirmer` si plusieurs produits de la base
   partagent la meme cle : le matcher ne peut pas savoir lequel a ete prononce.

### Resultats (`py nlu/evaluate_entity_linking.py`, 37 cas, hors ligne)

| Graphie | Top-1 | Top-3 |
|---|---|---|
| latine (fautes de frappe, noms partiels, bruit) | 18/18 = 100 % | 18/18 = 100 % |
| arabe (dont 14 hors table de correspondances) | 18/19 = 94,7 % | 19/19 = 100 % |

Avant la translitteration lettre a lettre, les 14 cas arabes hors table ne renvoyaient
**aucun** candidat. Le seul cas non resolu en top-1 est un homophone (باراسيتامول sort
PARACETAL avant PARACETAMOL B.BRAUN) : il est justement rendu en `a_confirmer`, et le
bon produit reste dans les trois premiers.

Limites connues :
- Le garde-fou anti-bruit filtre les requetes absurdes, pas les confusions plausibles :
  deux noms reellement proches restent departages par le seul score lexical.
- La cle phonetique ecrase des distinctions reelles (p/b, s/z, i/e) : elle augmente le
  rappel sur l'arabe au prix d'homophones a departager, d'ou le rabattement systematique
  en `a_confirmer` quand la cle est partagee.
- Une lettre arabe hors table est ignoree plutot qu'inventee : un mot ecrit dans une
  graphie tres eloignee peut encore passer a cote.
- Matching purement lexical : deux medicaments au nom proche mais a l'usage tres different peuvent se confondre (risque a garder en tete pour la validation humaine sur les cas `a_confirmer`).

## Pharmacy Linking — resultats et limites
Meme logique que l'entity linking medicaments, sur `data/clean/pharmacies_reference.csv` :
1. normalisation du nom ET suppression du prefixe "Pharmacie/La Pharmacie/Grande Pharmacie" — ainsi que "صيدلية", qui ouvre presque toute demande dictee en arabe (quasi tous les noms commencent par ce mot, il faut l'ignorer pour bien discriminer) ;
2. si une localisation est fournie : filtre d'abord sur la ville (fuzzy match >=90) puis, a defaut, recherche en sous-chaine dans l'adresse (pour les quartiers, non captures par le champ ville) ;
3. fuzzy matching du nom dans le pool filtre ; sans nom, retourne la liste du lieu (pharmacies de garde en tete) ;
4. memes paliers de confiance que pour les medicaments, garde-fou anti-bruit compris
   (sans lui, "Bidon Inexistante Xyz123" ressortait sur "Pharmacie Abid" en `a_confirmer`) ;
5. meme passe phonetique que pour les medicaments, pour les noms dictes en arabe ;
6. **alias de villes** (`ALIAS_VILLES`) : un toponyme ne se translittere pas, il se
   traduit -- "الدار البيضاء" et "Casablanca" n'ont aucune lettre en commun. La table
   couvre les villes les mieux representees dans l'annuaire, plus les diminutifs d'usage
   ("kaza", "casa").

7. **alerte homonymes** : quand un nom demande sans ville est porte par plusieurs
   officines dans des villes differentes, `last_name_note` le signale. Renvoyer la
   premiere de la liste reviendrait a choisir une ville au hasard pour l'utilisateur
   sans le lui dire ; l'assistant demande donc laquelle.

Resultats (`py nlu/evaluate_pharmacy_linking.py`) : 12/12 en top-1, dont les 3 cas dictes
en arabe, plus le cas ambigu par construction ("Pharmacie Granada" sans ville, presente
dans trois villes) ou la reussite consiste a demander la ville.

Limites connues :
- Plusieurs pharmacies peuvent porter le meme nom dans des villes differentes (ex. "Pharmacie Ibn Sina", present dans 18 villes) — une recherche par nom seul, sans localisation, est ambigue par construction. C'est maintenant signale (point 7) plutot que tranche en silence, mais la levee de l'ambiguite demande un tour de dialogue de plus. Toujours privilegier nom+localisation quand les deux sont disponibles dans l'entity linking amont.
- Couverture geographique dependante de la base saydalia elle-meme (voir `data/README.md`) : pas de garantie d'exhaustivite par ville/quartier.
- Pas de coordonnees GPS fiables (la source ne les fournit pas correctement) : uniquement adresse texte.

## Pistes
- **Donnees reelles** : remplacer ou completer les 99 phrases de l'equipe par des messages anonymises de vrais patients. C'est la limite principale de l'evaluation.
- **Hybride** : utiliser les regles de `baseline.py` pour les entites quand le LLM est indisponible, et les confronter a sa sortie pour detecter ses omissions.
- **Fine-tuning** (DarijaBERT / AraBERT) : a envisager a partir de quelques centaines de phrases annotees. Avec 99 phrases, le modele serait trop instable pour etre compare honnetement.
- **Translitteration arabe → latin** : la transcription lettre a lettre couvre desormais tout mot arabe ; restent a etoffer au fil des cas reels la table de correspondances (`ARABIC_TO_LATIN`, pour les noms trop eloignes de leur graphie latine) et la table d'alias de villes (`ALIAS_VILLES`, 40 entrees).
