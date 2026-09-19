# DwaTalk — Assistant pharmacie en darija, arabe et français (Challenge #1)

Assistant conversationnel qui comprend les demandes des patients, **à l'écrit ou à la voix**, en darija (graphie latine ou arabe), en arabe standard ou en français, et renvoie une **interprétation structurée** : intention, entités, médicaments et pharmacies résolus contre des bases de référence marocaines.

```
voix ──► Whisper (local) ──┐
                           ├──► NLU (LLM few-shot) ──► Entity linking ──► réponse structurée
texte ─────────────────────┘     intent + entités      médicaments         + fiches
                                                        pharmacies
```

## Installation

```
py -m pip install -r requirements.txt
```

Crée un fichier `.env` à la racine avec ta clé Ollama Cloud (gratuite pour le modèle par défaut `gpt-oss:20b-cloud`, à créer sur https://ollama.com/settings/keys) :

```
OLLAMA_API_KEY=ta_cle_ici
```

La première question posée **à la voix** télécharge le modèle Whisper « small » (~460 Mo, une seule fois). Les suivantes prennent ~3 s sur CPU.

> Sous Windows, utilise `py` et non `python`, qui ouvre souvent le Microsoft Store.

## Lancer

**API** (terminal 1, depuis la racine) :

```
py -m uvicorn api.main:app --reload --port 8000
```

Documentation interactive des endpoints : http://localhost:8000/docs

**Interface web** (terminal 2) :

```
cd frontend
npm install
npm run dev
```

Puis ouvre http://localhost:5173. Le front appelle l'API sur le port 8000 (configurable via `VITE_API_BASE`) ; ce port est autorisé côté API dans `FRONTEND_ORIGINS` (CORS).

**Client terminal** (optionnel, API lancée) : `py api/chat_cli.py`

## Tester et évaluer

```
py -m pip install -r requirements-dev.txt
py -m pytest -m "not lent"     # 170 tests, ~3 s, sans reseau ni appel LLM
py -m pytest                   # + 2 tests Whisper reels (charge le modele)
```

Les tests simulent le NLU : ils vérifient notre code (routage des intents, entity linking, formulation, API, voix), pas la qualité du modèle. Celle-ci se mesure à part :

| Script | Mesure | Coût |
|---|---|---|
| `py nlu/evaluate.py` | NLU LLM sur 90 phrases | 90 appels Ollama |
| `py nlu/compare_baseline.py` | LLM vs baseline classique, mêmes 90 phrases | aucun |
| `py nlu/evaluate_entity_linking.py` | résolution des médicaments | aucun |
| `py nlu/evaluate_pharmacy_linking.py` | résolution des pharmacies | aucun |

## Résultats

| | LLM few-shot | Baseline classique |
|---|---|---|
| Intent — exactitude | **97,8 %** | 67,8 % |
| Entités — F1 | **98,6 %** | 95,4 % |
| Coût par phrase | 1 appel réseau, plusieurs secondes | 0,5 ms, hors ligne |

Entity linking : 22/22 médicaments (fautes de frappe et graphie arabe comprises), 9/10 pharmacies. Détail et limites dans [nlu/README.md](nlu/README.md).

## Structure

```
api/                    service FastAPI
  main.py                /chat, /chat/audio, /transcription, /medicaments, /pharmacies
  parole.py              reconnaissance vocale (faster-whisper, local)
  chat_cli.py            client terminal
nlu/                    comprehension du langage
  schema.json            7 intents, 6 types d'entites
  seed_dataset.jsonl     99 phrases annotees (genere par build_seed_dataset.py)
  llm_prototype.py       NLU par LLM few-shot (Ollama Cloud)
  baseline.py            NLU classique (TF-IDF + regles), pour comparaison
  entity_linking.py      resolution des medicaments (RapidFuzz)
  pharmacy_linking.py    resolution des pharmacies
data/                   references : 19 974 medicaments (AMMPS, CNOPS, CNSS), 2 652 pharmacies
scripts/                scraping et nettoyage des sources (deja executes)
frontend/               interface React (Vite)
  src/pages/             Accueil, Assistant, Medicaments, Pharmacies, Historique, Parametres
  src/components/        composants reutilisables (ChatMessage, MedicineCard, SearchBar...)
  src/lib/               client API, enregistrement vocal, historique local
tests/                  tests automatises (pytest)
```

## Limites connues

- **Darija à la voix** : Whisper n'a pas de modèle de darija. Il la transcrit en arabe ou en français approchant. Le texte est donc rendu au champ de saisie pour être relu avant envoi.
- **Pas de stock en temps réel** : DwaTalk indique prix, forme et remboursement, puis oriente vers des pharmacies à appeler. Il ne sait pas ce qui est en rayon.
- **Pas d'information clinique** : les bases sont des registres d'autorisation et de remboursement, sans posologie ni effets indésirables. DwaTalk le dit plutôt que de l'inventer.
- **Pharmacies** : la source (saydalia.ma) ne donne ni coordonnées GPS fiables ni horaires complets. Le plan situe la ville, pas l'officine.
- **Historique** : il est conservé dans le navigateur uniquement.
