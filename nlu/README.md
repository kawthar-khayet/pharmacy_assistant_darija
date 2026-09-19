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
Sur les 90 phrases de test (hors few-shot) :

| | LLM few-shot | Baseline |
|---|---|---|
| Intent — exactitude | **97,8 %** | 67,8 % |
| Intent — F1 macro | **97,3 %** | 61,5 % |
| Entites — precision | 99,1 % | 98,1 % |
| Entites — rappel | 98,2 % | 92,8 % |
| Entites — F1 | **98,6 %** | 95,4 % |

- **L'intent, c'est le point fort du LLM.** Avec 81 phrases d'entrainement par pli (72 du jeu de test + les 9 few-shot) pour 7 intents et 5 variantes de langue, un classifieur statistique manque d'exemples.
- **Les entites, c'est presque egalite.** Les regles battent meme le LLM sur la forme galenique (96,8 % contre 93,3 %), pour 0,5 ms par phrase, hors ligne et sans cout. Un systeme hybride est donc defendable : le LLM pour l'intent, les regles pour les entites ou en secours quand le LLM est indisponible.
- Les deux erreurs d'intent restantes du LLM : « bghit njib juj boites » (cas limite de la regle bghit, predit commande) et « hal amoxicilline mashmoula bi at-ta'min? » (arabe standard translittere, predit hors perimetre).

**Comparaison avec la premiere mesure (94,5 % / 91,9 % sur 91 exemples)** : entre les deux, trois choses ont change a la fois — la regle « sidalia » dans le prompt, la correction des labels « bghit », et un few-shot remplace (le jeu de test differe donc d'une phrase). C'est un progres reel, mais ce n'est pas une mesure fine : sur 90 phrases, chaque exemple pese 1,1 point.

**Limites du protocole** : 99 phrases ecrites par l'equipe, pas des messages reels de patients. Certains sous-groupes sont minuscules (4 phrases en arabe standard). Le modele est appele a temperature 0, sans garantie de determinisme cote service.

## Comment etendre le dataset
Ajouter des tuples dans `RAW_EXAMPLES` de `build_seed_dataset.py` : `(text, lang, intent, [(ENTITY_TYPE, "valeur exacte presente dans text"), ...])`, puis relancer le script. Il valide automatiquement que chaque valeur d'entite existe bien dans le texte (leve une erreur sinon) — impossible d'introduire un offset faux.

## Usage prevu
1. **Prototype rapide (LLM few-shot)** : injecter `schema.json` (intents + entites) dans le prompt systeme + quelques exemples de `seed_dataset.jsonl`, demander une sortie JSON strictement conforme au schema.
2. **Fine-tuning local** (AraBERT/DarijaBERT ou equivalent) : `seed_dataset.jsonl` sert de depart ; a etoffer (cible indicative : 500-1500 exemples, en ajoutant des variantes orthographiques de medicaments, des fautes de frappe, plus d'exemples reels/valides) avant entrainement.
3. **Comparaison A/B/C** (LLM few-shot vs fine-tune vs hybride) : ce meme fichier sert de test set commun pour comparer Intent Accuracy / NER F1 entre approches.

## Entity Linking — resultats et limites
`entity_linking.py` implemente l'etape recommandee "normalisation + RapidFuzz" (avant d'envisager des embeddings si besoin) :
1. normalisation (accents, casse, ponctuation) ;
2. translitteration arabe→latin via une petite table seed (`ARABIC_TO_LATIN`, a etendre) ;
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
   legitime par DCI (requete "ibuprofene" -> ADFENE) serait rejetee a tort.

Limites connues :
- Le garde-fou anti-bruit filtre les requetes absurdes, pas les confusions plausibles :
  deux noms reellement proches restent departages par le seul score lexical.
- La table de translitteration arabe est un point de depart (7 entrees) — un mot arabe absent de la table ne matchera rien. A etoffer au fur et a mesure des cas reels.
- Pas de gestion de la darija en graphie arabe non couverte par la table (ex. variantes orthographiques du meme mot).
- Matching purement lexical : deux medicaments au nom proche mais a l'usage tres different peuvent se confondre (risque a garder en tete pour la validation humaine sur les cas `a_confirmer`).

## Pharmacy Linking — resultats et limites
Meme logique que l'entity linking medicaments, sur `data/clean/pharmacies_reference.csv` :
1. normalisation du nom ET suppression du prefixe "Pharmacie/La Pharmacie/Grande Pharmacie" (quasi tous les noms commencent par ce mot, il faut l'ignorer pour bien discriminer) ;
2. si une localisation est fournie : filtre d'abord sur la ville (fuzzy match >=90) puis, a defaut, recherche en sous-chaine dans l'adresse (pour les quartiers, non captures par le champ ville) ;
3. fuzzy matching du nom dans le pool filtre ; sans nom, retourne la liste du lieu (pharmacies de garde en tete) ;
4. memes paliers de confiance que pour les medicaments, garde-fou anti-bruit compris
   (sans lui, "Bidon Inexistante Xyz123" ressortait sur "Pharmacie Abid" en `a_confirmer`).

Limites connues :
- Plusieurs pharmacies peuvent porter le meme nom dans des villes differentes (ex. "Pharmacie Ibn Sina", tres frequent) — une recherche par nom seul, sans localisation, est ambigue par construction. Toujours privilegier nom+localisation quand les deux sont disponibles dans l'entity linking amont.
- Couverture geographique dependante de la base saydalia elle-meme (voir `data/README.md`) : pas de garantie d'exhaustivite par ville/quartier.
- Pas de coordonnees GPS fiables (la source ne les fournit pas correctement) : uniquement adresse texte.

## Pistes
- **Donnees reelles** : remplacer ou completer les 99 phrases de l'equipe par des messages anonymises de vrais patients. C'est la limite principale de l'evaluation.
- **Hybride** : utiliser les regles de `baseline.py` pour les entites quand le LLM est indisponible, et les confronter a sa sortie pour detecter ses omissions.
- **Fine-tuning** (DarijaBERT / AraBERT) : a envisager a partir de quelques centaines de phrases annotees. Avec 99 phrases, le modele serait trop instable pour etre compare honnetement.
- **Translitteration arabe → latin** : la table `ARABIC_TO_LATIN` compte 8 entrees, a etoffer au fil des cas reels.
