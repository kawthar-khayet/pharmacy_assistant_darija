# NLU — Intents & Entities (Challenge #1)

## Fichiers
- `schema.json` — taxonomie : 7 intents, 6 types d'entites, avec description et langues supportees.
- `build_seed_dataset.py` — genere `seed_dataset.jsonl` a partir d'exemples bruts (texte + valeurs d'entites) ; les offsets de caracteres sont calcules automatiquement (`str.find`), jamais comptes a la main.
- `seed_dataset.jsonl` — 99 exemples de bootstrap, repartis sur les 7 intents et 5 variantes linguistiques (fr, ar, darija graphie arabe, darija graphie latine, mixte), avec fautes d'orthographe volontaires sur les noms de medicaments.
- `llm_prototype.py` — prototype NLU par LLM few-shot via **Ollama Cloud** (endpoint OpenAI-compatible `https://ollama.com/v1`, modele par defaut `gpt-oss:20b-cloud` — accessible en tier gratuit ; `qwen3.5:cloud`, teste en premier pour son meilleur support multilingue, renvoie HTTP 402 "requires a subscription"). Construit le prompt systeme depuis `schema.json` + 8 exemples de `seed_dataset.jsonl`, renvoie un JSON valide `{intent, entities}`. Necessite `OLLAMA_API_KEY` (cle creee sur ollama.com/settings/keys) dans un fichier `.env` a la racine du projet (`OLLAMA_API_KEY=...`) — plus fiable qu'une variable d'environnement shell, chaque appel d'outil tournant dans son propre process. Modele configurable via `OLLAMA_MODEL`.
- `evaluate.py` — evalue `llm_prototype.py` sur le reste du seed dataset (Intent Accuracy + Entity F1). Meme prerequis. **Resultat obtenu (gpt-oss:20b-cloud, 91 exemples)** : Intent accuracy 94.5%, Entity F1 91.9% — voir section dediee plus bas.
- `entity_linking.py` — resolution d'un nom de medicament (potentiellement mal orthographie ou en arabe) contre `data/clean/medicaments_reference.csv`, via normalisation + RapidFuzz + une petite table de translitteration arabe→latin. Aucune dependance externe payante, s'utilise directement en CLI : `python nlu/entity_linking.py "dolipran" "1g"`.
- `evaluate_entity_linking.py` — evaluation locale (sans cout) du matcher sur 22 cas manuels (fautes d'orthographe + arabe) : **100% top-1** actuellement.
- `pharmacy_linking.py` — meme approche (normalisation + RapidFuzz) pour resoudre les entites `PHARMACIE`/`LOCALISATION` contre `data/clean/pharmacies_reference.csv` (2652 pharmacies scrapees depuis saydalia.ma). Recherche par nom, par localisation (ville, avec repli sur recherche en sous-chaine dans l'adresse pour les quartiers), ou les deux combines (la localisation filtre d'abord le pool, ce qui evite les confusions entre plusieurs pharmacies homonymes dans des villes differentes). CLI : `python nlu/pharmacy_linking.py "Ibn Sina" "Casablanca"` (ou `""` pour le nom si recherche par lieu seul).
- `evaluate_pharmacy_linking.py` — evaluation locale sur 10 cas nominatifs (dont fautes de frappe) + 3 cas de recherche par localisation : **90% top-1** (le seul "echec" est un cas ambigu de deux pharmacies homonymes dans des villes differentes, comportement attendu sans indice de localisation).

## Intents (7)
| id | description |
|---|---|
| `disponibilite_medicament` | le medicament est-il en stock ? |
| `prix_remboursement` | prix et/ou taux de remboursement |
| `info_pharmacie` | coordonnees, horaires, pharmacie de garde |
| `posologie_information` | comment/quand prendre un medicament |
| `commande_reservation` | reserver/commander une quantite |
| `salutation` | politesse, small talk |
| `autre` | hors perimetre / fallback |

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
Offsets = index caractere Python (`text[start:end] == value`). Un exemple sans entite a `"entities": []` (cas `salutation`, `autre`, ou intent info_pharmacie sans mention explicite de lieu/nom).

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
4. score de confiance par palier : `auto` (>=90), `a_confirmer` (70-89), `non_fiable` (<70).

Limites connues :
- La table de translitteration arabe est un point de depart (7 entrees) — un mot arabe absent de la table ne matchera rien. A etoffer au fur et a mesure des cas reels.
- Pas de gestion de la darija en graphie arabe non couverte par la table (ex. variantes orthographiques du meme mot).
- Matching purement lexical : deux medicaments au nom proche mais a l'usage tres different peuvent se confondre (risque a garder en tete pour la validation humaine sur les cas `a_confirmer`).

## Pharmacy Linking — resultats et limites
Meme logique que l'entity linking medicaments, sur `data/clean/pharmacies_reference.csv` :
1. normalisation du nom ET suppression du prefixe "Pharmacie/La Pharmacie/Grande Pharmacie" (quasi tous les noms commencent par ce mot, il faut l'ignorer pour bien discriminer) ;
2. si une localisation est fournie : filtre d'abord sur la ville (fuzzy match >=90) puis, a defaut, recherche en sous-chaine dans l'adresse (pour les quartiers, non captures par le champ ville) ;
3. fuzzy matching du nom dans le pool filtre ; sans nom, retourne la liste du lieu (pharmacies de garde en tete) ;
4. memes paliers de confiance que pour les medicaments.

Limites connues :
- Plusieurs pharmacies peuvent porter le meme nom dans des villes differentes (ex. "Pharmacie Ibn Sina", tres frequent) — une recherche par nom seul, sans localisation, est ambigue par construction. Toujours privilegier nom+localisation quand les deux sont disponibles dans l'entity linking amont.
- Couverture geographique dependante de la base saydalia elle-meme (voir `data/README.md`) : pas de garantie d'exhaustivite par ville/quartier.
- Pas de coordonnees GPS fiables (la source ne les fournit pas correctement) : uniquement adresse texte.

## Prochaine etape
- **NLU** : `evaluate.py` a ete lance (gpt-oss:20b-cloud) : 94.5% intent accuracy / 91.9% entity F1 sur 91 exemples. A ameliorer : corriger 3 labels ambigus du seed dataset (chevauchement `disponibilite_medicament`/`commande_reservation` sur les tournures "bghit..."), puis lancer la comparaison LLM few-shot vs fine-tune.
- **Entity Linking** : etoffer la table de translitteration arabe et le jeu de test au fil des cas reels rencontres.
- **Bout en bout** : brancher NLU → Entity Linking (medicaments + pharmacies) → reponse structuree, puis exposer via FastAPI.
