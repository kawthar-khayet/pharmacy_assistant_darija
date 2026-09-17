# API — Assistant Pharmacie (Challenge #1)

Connecte les briques deja construites en un seul service :
```
texte patient → NLU (intent + entites, LLM few-shot Ollama Cloud)
              → Entity Linking medicaments (si entite MEDICAMENT)
              → Entity Linking pharmacies (si entite PHARMACIE/LOCALISATION)
              → reponse JSON structuree
```

## Lancer le serveur
```
uvicorn api.main:app --reload --port 8000
```
Necessite un fichier `.env` a la racine du projet avec `OLLAMA_API_KEY=...` (voir `nlu/README.md`) : chaque appel `/chat` fait un appel LLM metre sur Ollama Cloud.

Documentation interactive (Swagger) : http://localhost:8000/docs

## Endpoints

### `GET /health`
Verification basique que le service tourne. Reponse : `{"status": "ok"}`.

### `GET /schema`
Retourne la taxonomie intents/entites (`nlu/schema.json`) — utile pour un client qui veut connaitre les valeurs possibles.

### `POST /chat`
Requete :
```json
{"text": "wach kayn doliprane 1g? bghit juj boites"}
```
Reponse :
```json
{
  "input": "wach kayn doliprane 1g? bghit juj boites",
  "intent": "disponibilite_medicament",
  "entities": [
    {"type": "MEDICAMENT", "value": "doliprane"},
    {"type": "DOSAGE", "value": "1g"},
    {"type": "QUANTITE", "value": "juj"},
    {"type": "FORME", "value": "boites"}
  ],
  "medicament_matches": [
    {"nom_candidat": "DOLIPRANE", "score": 100.0, "confidence": "auto", "nb_variantes": 22, "variantes": [...]}
  ],
  "pharmacie_matches": [],
  "validation_errors": []
}
```
- `medicament_matches` n'est rempli que si une entite `MEDICAMENT` a ete extraite (utilise aussi `DOSAGE` si present pour affiner).
- Le `reply` nomme le regime de remboursement, CNOPS et CNSS publiant chacun son taux : `rembourse a 70% (CNOPS et CNSS)`, `rembourse a 70% (CNSS)`, ou `remboursement : CNOPS 70%, CNSS 0%` quand ils divergent. Un taux de 0 signifie « inscrit sur la liste mais non rembourse » et s'affiche `non rembourse (...)`, pas `rembourse a 0%`.
- `pharmacie_matches` n'est rempli que si une entite `PHARMACIE` et/ou `LOCALISATION` a ete extraite.
- `400` si `text` est vide ; `500` si `OLLAMA_API_KEY` n'est pas configuree.

## Limites actuelles (a lever pour un vrai MVP)
- Une seule entite `MEDICAMENT`/`PHARMACIE` par message est liee (la premiere trouvee) — un message qui parle de deux medicaments ne lierait que le premier.
- Pas de reponse en langage naturel : la sortie est un JSON technique, pas encore une phrase du type "Oui, le Doliprane 1g est disponible a 60.70 DH". A ajouter si le chatbot doit repondre directement au patient plutot que d'alimenter un systeme aval.
- Pas d'entree vocale (Whisper) branchee sur cette API pour l'instant.
- Pas d'authentification/rate limiting (hors scope pour un prototype de challenge).
