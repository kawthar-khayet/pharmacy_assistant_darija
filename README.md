# Challenge #1 — Assistant Pharmacie Arabic/Darija

Assistant conversationnel qui comprend les demandes des patients (fr/arabe/darija, texte) sur les medicaments et pharmacies, et retourne une reponse structuree.

Pipeline : `texte -> NLU (intent + entites, LLM few-shot Ollama Cloud) -> Entity Linking medicaments/pharmacies -> reponse`.

## Installation

```
pip install -r requirements.txt
```

Cree un fichier `.env` a la racine du projet (a cote de ce README) avec ta propre cle Ollama Cloud :

```
OLLAMA_API_KEY=ta_cle_ici
```

Cle a creer sur https://ollama.com/settings/keys (gratuite pour le modele par defaut `gpt-oss:20b-cloud`).

## Lancer le serveur

```
uvicorn api.main:app --reload --port 8000
```

Doc interactive : http://localhost:8000/docs

## Lancer l'interface web (React)

Le serveur API doit tourner (voir ci-dessus). Dans un autre terminal :

```
cd frontend
npm install     # la premiere fois seulement
npm run dev
```

Interface : http://localhost:5173

L'origine du front est autorisee explicitement cote API (`FRONTEND_ORIGINS` dans
`api/main.py`) : sans ce reglage CORS, le navigateur bloquerait tous les appels.
Si tu sers le front sur un autre port ou domaine, ajoute-le a cette liste.
L'URL de l'API est configurable via `VITE_API_BASE` (defaut `http://127.0.0.1:8000`).

L'historique des conversations est conserve dans le `localStorage` du navigateur :
il n'y a ni compte ni base cote serveur, donc il est propre a cet appareil et
disparait si le cache est vide. Le passer cote serveur demanderait d'ajouter une
base et des endpoints dedies, l'API gardant aujourd'hui son etat de dialogue en
memoire.

## Tester en terminal

Dans un autre terminal, pendant que le serveur tourne :

```
python api/chat_cli.py
```

Pose une question (darija/arabe/francais), ex. `wach kayn doliprane 1g?`. Si le bot demande la ville, reponds simplement au prompt `Ville/quartier >` qui s'affiche.

## Structure du projet

```
data/                    donnees de reference (medicaments + pharmacies), nettoyees et brutes
  README.md              details des sources (AMMPS, CNOPS, CNSS, Saydalia) et du pipeline de nettoyage
nlu/                      NLU (intents/entites) + Entity Linking
  README.md               taxonomie, format du dataset, resultats d'evaluation
  schema.json              7 intents, 6 types d'entites
  seed_dataset.jsonl       99 exemples etiquetes (fr/ar/darija)
  llm_prototype.py         NLU few-shot via Ollama Cloud
  entity_linking.py        matching medicaments (RapidFuzz)
  pharmacy_linking.py      matching pharmacies (RapidFuzz)
api/                      service API
  README.md                documentation des endpoints
  main.py                  FastAPI (endpoints /health, /schema, /chat)
  chat_cli.py               client terminal interactif
frontend/                 interface web React (Vite)
  src/App.jsx              coquille : barre laterale + conversation courante
  src/Chat.jsx             le chat (tours, multi-tours, detail NLU)
  src/Sidebar.jsx          historique des conversations
  src/conversations.js     stockage de l'historique (localStorage)
  src/api.js               client de l'API
  src/index.css            identite visuelle (jetons de couleur, motif khatim)
scripts/                  scraping/nettoyage des donnees sources (deja executes, resultats dans data/)
```

## Etat d'avancement

- [x] Donnees de reference medicaments (CNOPS + AMMPS + CNSS, 19 974 entrees, dont 12 075 avec taux de remboursement)
- [x] Donnees de reference pharmacies (Saydalia, 2652 entrees)
- [x] NLU few-shot (Ollama Cloud) : 94.5% intent accuracy / 91.9% entity F1 sur le seed dataset
- [x] Entity Linking medicaments et pharmacies (RapidFuzz), avec gestion des lieux ambigus
- [x] API FastAPI avec conversation multi-tours (demande la ville si besoin)
- [x] Interface web React (chat epure, francais, desktop d'abord)
- [x] Historique des conversations dans la barre laterale (stocke dans le navigateur)
- [ ] Entree vocale (Whisper)
- [ ] Etude comparative LLM few-shot vs fine-tuning
- [ ] Etude du probleme / related work (livrable attendu par le challenge)
