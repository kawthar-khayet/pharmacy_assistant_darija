# DwaTalk — Assistant pharmacie en darija, arabe et français (Challenge #1)

Assistant conversationnel qui répond aux questions des patients, **à l'écrit ou à la voix**, en darija (graphie latine ou arabe), en arabe standard ou en français, à partir des bases de référence marocaines : prix et remboursement des médicaments, notice officielle, pharmacies proches, conseil pour un symptôme bénin, urgences.

```
voix ──► Whisper (local) ──┐
                           ├──► filet urgence ──► analyse (1 appel LLM) ──► médicaments, lieux,
texte ─────────────────────┘    (mots-clés)       situation + demandes      pharmacies retrouvés
                                                                              │
                                    réponse courte, dans la langue  ◄── outils (data/) : seulement
                                    du patient (phrases du bot)          ce qui est demandé
```

**Un seul appel LLM par message.** Le modèle ne fait que comprendre la question (situation, demandes, médicaments, lieu…) ; c'est le code qui cherche dans les bases et rédige la réponse, avec ses propres phrases, et seulement sur ce qui a été demandé.

## Ce que fait le bot

| Question | Réponse |
|---|---|
| Prix, remboursement CNOPS / CNSS | prix public par présentation ; taux et montant remboursé pour **le** régime du patient (demandé une fois, retenu pour la conversation) |
| Formes et dosages | ce qui existe au Maroc, et si la forme demandée existe |
| Notice (à quoi il sert, effets indésirables, contre-indications, précautions, interactions, grossesse) | extrait de la rubrique demandée de la notice officielle (BDPM), résumé dans la langue du patient, texte complet replié en dessous |
| Posologie (comment / combien en prendre) | **toujours** : « pose la question à ton médecin » — DwaTalk ne donne jamais de dose |
| Pharmacies d'un quartier | les 5 plus proches, avec la distance |
| Pharmacie de garde | celles ouvertes 24h/24 ou la nuit dans la ville, en disant que le tour de garde du jour n'est pas connu |
| Une pharmacie par son nom | adresse et téléphone ; si le nom existe dans plusieurs villes, le bot demande laquelle |
| Symptôme courant et bénin | la molécule à demander au pharmacien (liste blanche `data/clean/conseil_symptomes.csv`), sans marque ; enfant, bébé, grossesse, symptôme qui dure → un professionnel |
| Urgence (surdosage, détresse) | numéros d'urgence seulement : SAMU 141, Protection civile 15, Centre antipoison 0801 000 180 — détectée par mots-clés même si le LLM est en panne |
| Stock, générique, livraison… | « je n'ai pas cette information » : DwaTalk n'est pas une pharmacie |

## Installation

```
py -m pip install -r requirements.txt
```

Crée un fichier `.env` à la racine :

```
GEMINI_API_KEY=ta_cle_ici
```

Clé gratuite sur https://aistudio.google.com/apikey. Options, toutes facultatives :

| Variable | Défaut | Rôle |
|---|---|---|
| `GEMINI_MODEL` | `gemini-3.5-flash` | modèle de l'analyse |
| `GEMINI_MODEL_SECOURS` | `gemini-3.1-flash-lite` | même clé, prend le relais quand le premier est saturé (503) ou à court de quota |
| `GROQ_API_KEY`, `OLLAMA_API_KEY` | — | fournisseurs de secours supplémentaires (ignorés sans clé) |
| `LLM_ORDRE` | `gemini,gemini_secours,groq,ollama` | ordre d'essai des fournisseurs |
| `GEMINI_MODEL_RESUME` | `gemini-3.1-flash-lite` | résumés des notices (pré-calculés, voir `scripts/precalculer_resumes.py`) |

⚠️ Le palier gratuit de Gemini est limité (une vingtaine de requêtes par jour et par modèle) : chaque message envoyé au bot en consomme une. Quand aucun fournisseur ne répond, le bot le dit poliment et rappelle les numéros d'urgence.

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

Les tests simulent l'analyse du LLM : ils vérifient notre code (validation, recherche dans les bases, outils, rédaction, API, voix), pas la qualité du modèle. Un garde-fou fait échouer tout test qui appellerait un vrai LLM.

## Structure

```
nlp/                    le moteur
  moteur.py              un message -> une reponse (enchaine tout le reste)
  config.py              chemins, fournisseurs LLM, cles (.env)
  llm.py                 le seul appel LLM, avec fournisseurs de secours
  analyse/               prompt.md + schema.json (ce que le LLM a le droit de renvoyer),
                         validation.py, urgence.py (filet par mots-cles)
  linking/               medicaments, lieux (villes et quartiers), pharmacies, translitteration
  outils/                prix, medicament (formes), securite (notice), pharmacies, conseil
  reponse/               phrases du bot (4 langues), composeur, detection de la langue
  preparation/           scripts lances une fois : fusion des pharmacies, quartiers
api/                    service FastAPI (main.py), voix (parole.py), resumes des notices, client terminal
data/                   bases : 19 974 medicaments (AMMPS, CNOPS, CNSS), ~8 000 pharmacies
                        (OpenStreetMap + annuaire), 1 854 quartiers, notices BDPM
scripts/                recuperation et nettoyage des sources (deja executes)
frontend/               interface React (Vite)
tests/                  tests automatises (pytest)
```

## Limites connues

- **Darija à la voix** : Whisper n'a pas de modèle de darija. Le texte transcrit est rendu au champ de saisie pour être relu avant envoi ; la graphie arabe qui en résulte est ensuite rapprochée des bases par translittération et clé phonétique.
- **Pas de stock, pas de tour de garde** : DwaTalk ne sait ni ce qui est en rayon, ni quelle pharmacie est de garde aujourd'hui. Il le dit.
- **Notice** : elle vient de la base française (BDPM) et décrit la molécule, pas la boîte vendue au Maroc ; 221 molécules sont couvertes. Le texte reste en français, un résumé est proposé dans la langue du patient quand il a été pré-calculé.
- **Conseil symptômes** : la liste `conseil_symptomes.csv` doit être relue par un pharmacien avant tout usage réel.
- **Lieux** : un quartier présent dans plusieurs villes (Agdal, Hay Riad…) fait demander la ville ; un quartier absent d'OpenStreetMap et de l'annuaire n'est pas reconnu.
- **Historique** : conservé dans le navigateur uniquement ; la mémoire de conversation côté API (régime, ville) est en mémoire vive et disparaît au redémarrage.
