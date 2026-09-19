# API — DwaTalk (Challenge #1)

Relie les briques du projet en un seul service :

```
audio ─► Whisper (parole.py) ─┐
                              ├─► NLU (LLM few-shot) ─► entity linking ─► reponse JSON + texte
texte ────────────────────────┘                          medicaments / pharmacies
```

## Lancer

```
py -m uvicorn api.main:app --reload --port 8000
```

Necessite un `.env` a la racine avec `OLLAMA_API_KEY=...` : chaque `/chat` fait un appel LLM. Documentation interactive : http://localhost:8000/docs

## Endpoints

| Methode | Chemin | Role |
|---|---|---|
| GET | `/health` | Le service repond |
| GET | `/schema` | Taxonomie intents / entites (`nlu/schema.json`) |
| POST | `/chat` | Question texte → interpretation structuree + reponse |
| POST | `/transcription` | Audio → texte (Whisper, local) |
| POST | `/chat/audio` | Audio → transcription → meme traitement que `/chat` |
| GET | `/medicaments?q=` | Recherche de medicaments (nom ou molecule, fautes tolerees) |
| GET | `/pharmacies?ville=&q=` | Recherche de pharmacies par lieu et/ou nom |

### `POST /chat`

```json
{"text": "wach kayn doliprane 1g? bghit juj boites", "session_id": null}
```

Reponse :

```json
{
  "session_id": "3f0c…",
  "input": "wach kayn doliprane 1g? bghit juj boites",
  "reply": "DOLIPRANE (1 G, comprime effervescent) -- 13.7 DH, rembourse a 70% (CNOPS et CNSS)\nDans quelle ville ou quel quartier es-tu … ?",
  "intent": "disponibilite_medicament",
  "entities": [
    {"type": "MEDICAMENT", "value": "doliprane"},
    {"type": "DOSAGE", "value": "1g"},
    {"type": "QUANTITE", "value": "juj"},
    {"type": "FORME", "value": "boites"}
  ],
  "medicament_matches": [{"nom_candidat": "DOLIPRANE", "score": 100.0, "confidence": "auto", "variantes": ["…"]}],
  "pharmacie_matches": [],
  "validation_errors": [],
  "awaiting_localisation": true
}
```

- **Multi-tours** : quand la demande porte sur un medicament sans lieu, `awaiting_localisation` vaut `true`. Le message suivant, envoye avec le meme `session_id`, est lu comme la ville ou le quartier.
- **Paliers de confiance appliques** : un candidat `non_fiable` n'est jamais utilise. Si rien de fiable ne correspond, la reponse dit « Je ne trouve pas … » au lieu de proposer un medicament au hasard. Un candidat `a_confirmer` est presente comme une hypothese (« Tu parles peut-etre de … »).
- **Remboursement** : CNOPS et CNSS publient chacun son taux, et le regime est toujours nomme. Un taux de 0 s'affiche « non rembourse ».
- **Hors perimetre** : si l'intent est `autre` mais qu'un medicament a ete reconnu (« chno kaydir doliprane ? »), la fiche est donnee avec une reserve plutot qu'un « je n'ai pas compris ».
- `400` si le texte est vide ; `500` si le LLM est indisponible, avec un message explicite (les surcharges passageres d'Ollama sont retentees 3 fois).

### `POST /transcription` et `POST /chat/audio`

Formulaire `multipart/form-data` :

| Champ | Obligatoire | Description |
|---|---|---|
| `fichier` | oui | Enregistrement (webm/opus, ogg, mp4, wav…), 60 s et 10 Mo maximum |
| `langue` | non | `ar` ou `fr` pour forcer la langue ; detection automatique sinon |
| `session_id` | non (`/chat/audio`) | Pour continuer une conversation |

`/transcription` renvoie `{"texte", "langue", "confiance_langue", "duree_audio"}`. `/chat/audio` renvoie la reponse de `/chat` augmentee d'un champ `transcription`. Un audio vide, illisible ou trop long donne une `422` avec la raison.

Le front utilise `/transcription` et non `/chat/audio` : l'utilisateur relit ce que Whisper a entendu avant d'envoyer, ce qui compte en darija.

## Limites

- Une seule entite `MEDICAMENT` et une seule `PHARMACIE` sont liees par message (les premieres trouvees).
- Etat de conversation en memoire : il disparait au redemarrage et ne se partage pas entre plusieurs processus. Un vrai deploiement le mettrait dans Redis ou une base.
- Pas d'authentification ni de limitation de debit (hors perimetre du prototype). Les origines autorisees sont listees explicitement (`FRONTEND_ORIGINS`).
- Whisper tourne sur CPU : ~3 s par question, et le premier appel charge le modele.
