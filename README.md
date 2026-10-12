# DwaTalk — Assistant pharmacie en darija, arabe et français (Challenge #1)

Assistant conversationnel qui répond aux questions des patients, **à l'écrit ou à la voix**, en darija (graphie latine ou arabe), en arabe standard ou en français, à partir des bases de référence marocaines : prix et remboursement des médicaments, notice officielle, pharmacies proches, conseil pour un symptôme bénin, urgences.

```
voix ──► Whisper (local) ──┐
                           ├──► filet urgence ──► 1er appel LLM : comprendre ──► recherche (code)
texte ─────────────────────┘    (mots-clés)       quoi chercher, question       dans nos fiches :
                                                  reformulée en français        noms, distance, sens
                                                                                     │
                                    réponse dans la langue du patient  ◄── 2e appel LLM : rédiger
                                                                            avec ces fiches SEULEMENT
```

**RAG, deux appels LLM par message.** Le modèle comprend la question et dit quoi chercher ; le code retrouve les fiches qui y répondent dans nos données (ChromaDB + recherche par nom + distance GPS) ; le modèle rédige la réponse **uniquement avec ces fiches**. Si l'information n'y est pas, il répond qu'elle n'existe pas dans nos données.

## Ce que fait le bot

| Question | Réponse |
|---|---|
| Prix, remboursement CNOPS / CNSS | prix public par présentation ; taux et montant remboursé pour **le** régime du patient (le bot le demande s'il ne le connaît pas) |
| Formes et dosages | ce qui existe au Maroc |
| Notice (à quoi il sert, effets indésirables, contre-indications, précautions, interactions, grossesse) | la partie demandée de la notice officielle (BDPM), expliquée simplement dans la langue du patient |
| Posologie (comment / combien en prendre) | **toujours** : « pose la question à ton médecin » — DwaTalk ne donne jamais de dose |
| Pharmacies d'un quartier | les 5 plus proches, avec la distance |
| Pharmacie de garde | celles ouvertes 24h/24 ou la nuit dans la ville, en disant que le tour de garde du jour n'est pas connu |
| Une pharmacie par son nom | adresse et téléphone ; si le nom existe dans plusieurs villes, le bot demande laquelle |
| Symptôme courant et bénin | la molécule à demander au pharmacien (liste blanche `data/clean/conseil_symptomes.csv`), sans marque ; enfant, bébé, grossesse, symptôme qui dure → un professionnel |
| Urgence (surdosage, détresse) | numéros d'urgence seulement : SAMU 141, Protection civile 15, Centre antipoison 0801 000 180 — phrase fixe, détectée par mots-clés même si le LLM est en panne |
| Tout le reste (stock, générique, livraison, information absente) | « cette information n'existe pas dans nos données » |

## Installation

```
py -m pip install -r requirements.txt
```

Puis construis l'index du RAG, **une fois** (et après chaque mise à jour des CSV de `data/clean/`) :

```
py -m nlp.rag.fiches     # data/clean/*.csv -> data/rag/fiches.jsonl (~18 000 fiches, ~1 min)
py -m nlp.rag.index      # embeddings + ChromaDB -> data/rag/chroma/
```

Le premier lancement de `nlp.rag.index` télécharge le modèle d'embeddings `multilingual-e5-small` (~470 Mo) et calcule les vecteurs sur CPU (plusieurs minutes). `data/rag/` n'est pas suivi par git : chacun le reconstruit. Sans index, `/chat` répond 503 avec ces deux commandes.

Crée un fichier `.env` à la racine :

```
GEMINI_API_KEY=ta_cle_ici
```

Clé gratuite sur https://aistudio.google.com/apikey. Options, toutes facultatives :

| Variable | Défaut | Rôle |
|---|---|---|
| `GEMINI_MODEL` | `gemini-3.5-flash` | modèle des deux appels (comprendre, rédiger) |
| `GEMINI_MODEL_SECOURS` | `gemini-3.1-flash-lite` | même clé, prend le relais quand le premier est saturé (503) ou à court de quota |
| `GROQ_API_KEY`, `OLLAMA_API_KEY` | — | fournisseurs de secours supplémentaires (ignorés sans clé) |
| `LLM_ORDRE` | `gemini,gemini_secours,groq,ollama` | ordre d'essai des fournisseurs |
| `GEMINI_MODEL_RESUME` | `gemini-3.1-flash-lite` | résumés des notices de la page Médicaments (pré-calculés, voir `scripts/precalculer_resumes.py`) |
| `EMBEDDINGS_MODEL` | `intfloat/multilingual-e5-small` | modèle d'embeddings local (changer impose de relancer `nlp.rag.index`) |

⚠️ Le palier gratuit de Gemini est limité (une vingtaine de requêtes par jour et par modèle) : chaque message envoyé au bot en consomme **deux**. Quand aucun fournisseur ne répond, le bot le dit poliment et rappelle les numéros d'urgence.

La première question posée **à la voix** télécharge le modèle Whisper « small » (~460 Mo, une seule fois). Les suivantes prennent ~3 s sur CPU.

> Sous Windows, utilise `py` et non `python`, qui ouvre souvent le Microsoft Store.

## Lancer

**API** (terminal 1, depuis la racine) :

```
py -m uvicorn api.main:app --reload --port 8000
```

Documentation interactive : http://localhost:8000/docs

**Interface web** (terminal 2) :

```
cd frontend
npm install
npm run dev
```

Puis ouvre http://localhost:5173. Le front appelle l'API sur le port 8000 (configurable via `VITE_API_BASE`).

**Client terminal** (optionnel, API lancée) : `py api/chat_cli.py`

## Tester

```
py -m pip install -r requirements-dev.txt
py -m pytest -m "not lent"     # quelques secondes, sans réseau ni appel LLM
py -m pytest                   # + 2 tests Whisper réels (charge le modèle)
```

Les tests simulent les deux appels LLM et remplacent l'index par un petit index en mémoire rempli de vraies fiches : ils vérifient notre code (fiches, recherche, ce qui est envoyé au LLM, API, voix), pas la qualité du modèle. Un garde-fou fait échouer tout test qui appellerait un vrai LLM ou chargerait le modèle d'embeddings.

## Structure

```
nlp/                    le moteur
  moteur.py              un message -> une reponse (enchaine tout le reste)
  config.py              chemins, fournisseurs LLM, cles (.env)
  llm.py                 les appels LLM (JSON ou texte), avec fournisseurs de secours
  rag/                   fiches.py (CSV -> fiches de texte), index.py (embeddings + ChromaDB),
                         comprendre.py + comprendre.md (1er appel : quoi chercher),
                         recherche.py (noms, distance, sens), repondre.md (regles du 2e appel)
  analyse/urgence.py     filet urgence par mots-cles, avant tout appel LLM
  linking/               medicaments, lieux (villes et quartiers), pharmacies, translitteration
  outils/                pharmacies (lieu, garde, nom) ; prix et notices pour les fiches
  reponse/               detection de la langue ; phrases fixes (urgence, service en panne)
  preparation/           scripts lances une fois : fusion des pharmacies, quartiers
api/                    service FastAPI (main.py), voix (parole.py), resumes des notices, client terminal
data/                   bases : 19 974 medicaments (AMMPS, CNOPS, CNSS), ~8 000 pharmacies
                        (OpenStreetMap + annuaire), 1 854 quartiers, notices BDPM ;
                        data/rag/ = fiches et index generes (non suivis par git)
scripts/                recuperation et nettoyage des sources (deja executes)
frontend/               interface React (Vite)
tests/                  tests automatises (pytest)
```

## Limites connues

- **Darija à la voix** : Whisper n'a pas de modèle de darija. Le texte transcrit est rendu au champ de saisie pour être relu avant envoi ; la graphie arabe qui en résulte est ensuite rapprochée des bases par translittération et clé phonétique.
- **Pas de stock, pas de tour de garde** : DwaTalk ne sait ni ce qui est en rayon, ni quelle pharmacie est de garde aujourd'hui. Il le dit.
- **Le LLM rédige** : il a pour consigne de ne répondre qu'avec les fiches et de recopier les chiffres tels quels, mais une reformulation fautive reste possible. `sources` (dans la réponse de `/chat`) liste les fiches qui lui ont été données.
- **Notice** : elle vient de la base française (BDPM) et décrit la molécule, pas la boîte vendue au Maroc ; 221 molécules sont couvertes.
- **Conseil symptômes** : la liste `conseil_symptomes.csv` doit être relue par un pharmacien avant tout usage réel.
- **Lieux** : un quartier présent dans plusieurs villes (Agdal, Hay Riad…) fait demander la ville ; un quartier absent d'OpenStreetMap et de l'annuaire n'est pas reconnu.
- **Historique** : conservé dans le navigateur uniquement ; la mémoire de conversation côté API (derniers messages, ville) est en mémoire vive et disparaît au redémarrage.
