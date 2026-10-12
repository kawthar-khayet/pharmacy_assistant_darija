# API — DwaTalk (Challenge #1)

Expose le moteur `nlp/` et les recherches des pages de l'interface.

```
audio ─► Whisper (parole.py) ─┐
                              ├─► nlp/moteur.py (RAG) ─► reponse du LLM + fiches pharmacies
texte ────────────────────────┘
```

## Lancer

```
py -m uvicorn api.main:app --reload --port 8000
```

Necessite un `.env` a la racine avec `GEMINI_API_KEY=...` (voir le README principal) : chaque `/chat` fait **deux** appels LLM (comprendre, rediger). L'index du RAG doit etre construit (`py -m nlp.rag.fiches` puis `py -m nlp.rag.index`), sinon `/chat` repond `503`. Documentation interactive : http://localhost:8000/docs

## Endpoints

| Methode | Chemin | Role |
|---|---|---|
| GET | `/health` | Le service repond |
| POST | `/chat` | Question texte → reponse |
| POST | `/transcription` | Audio → texte (Whisper, local) |
| POST | `/chat/audio` | Audio → transcription → meme traitement que `/chat` |
| GET | `/medicaments?q=` | Recherche de medicaments (nom ou molecule, fautes tolerees) |
| GET | `/pharmacies?ville=&q=&lat=&lon=` | Pharmacies par lieu, par nom, ou autour d'un point |
| GET | `/securite?dci=&langue=` | Notice officielle d'une molecule, avec un resume |

### `POST /chat`

```json
{"text": "fin kayna pharmacie f m3arif ?", "session_id": null}
```

Reponse (extrait) :

```json
{
  "session_id": "3f0c…",
  "input": "fin kayna pharmacie f m3arif ?",
  "reply": "Hahoma l-pharmaciyat l9rab l Maârif (Casablanca) :\n- Pharmacie Cité Plateau, 24 Bis avenue Stendhal, 0522250571, 0.1 km\n…",
  "langue": "ary_lat",
  "situation": "repondre",
  "pharmacie_matches": [{"nom": "Pharmacie Cité Plateau", "distance_km": 0.1, "telephone": "0522 25 05 71", "garde": null, "…": "…"}],
  "urgence": null,
  "requete": {"question": "Où trouver une pharmacie à Maârif ?", "medicaments": [], "lieu": "m3arif", "pharmacie": null, "pharmacies": true, "garde": false},
  "sources": ["pharma:Pharmacie Cité Plateau:Casablanca:24 Bis, avenue Stendhal Casablanca", "…"],
  "fournisseur": "gemini"
}
```

- `reply` : la reponse redigee par le LLM a partir des fiches trouvees, dans la langue du patient (`langue` : `fr`, `ary_lat`, `ary_ar`, `ar`).
- `situation` : `repondre`, `urgence` (phrase fixe avec les numeros, sans redaction du LLM), ou `indisponible` quand aucun LLM n'a repondu (la reponse le dit et rappelle les numeros d'urgence, statut HTTP 200).
- `pharmacie_matches` : les pharmacies trouvees, que l'interface affiche en fiches.
- `requete` : ce que le premier appel LLM a compris (ce qu'on a cherche) ; `sources` : les fiches de nos donnees donnees au second appel. Utiles pendant les tests.
- **Conversation** : envoyer le meme `session_id`. L'API garde les derniers messages (transmis au LLM, pour completer « f maarif » apres « f ina 7ay ? » ou retenir le regime d'assurance) et la derniere ville reconnue.
- `400` si le texte est vide ; `503` si l'index du RAG n'est pas construit.

### `GET /pharmacies`

`ville` (ville ou quartier, en darija, arabe ou francais) et/ou `q` (nom) filtrent. `lat`/`lon` (position du navigateur) trient du plus proche au plus loin et ajoutent `distance_km` ; seuls, ils suffisent (« autour de moi »). `note` explique un lieu ambigu ou inconnu.

Chaque resultat porte `latitude`, `longitude`, `precision_gps` (`exacte`, `rue`, `quartier`, `ville`) et `garde` (les horaires quand la pharmacie est ouverte 24h/24 ou la nuit). Seule `exacte` designe l'officine elle-meme : l'interface n'affiche une distance que dans ce cas.

### `GET /securite`

Texte de la notice officielle francaise (BDPM), **mot pour mot** : il decrit la molecule, pas la boite vendue au Maroc. Seule coupe : le paragraphe de declaration a la pharmacovigilance **francaise**. `langue` ajoute un resume (trois phrases au plus, produit par le LLM a partir du seul texte officiel, mis en cache dans `data/clean/securite_resumes.json`). `404` quand la molecule n'est pas couverte (221 le sont).

### `POST /transcription` et `POST /chat/audio`

Formulaire `multipart/form-data` : `fichier` (webm/opus, ogg, mp4, wav…, 60 s et 10 Mo maximum), `langue` (`ar` ou `fr`, facultatif), `session_id` (`/chat/audio`). `/transcription` renvoie `{"texte", "langue", "confiance_langue", "duree_audio", "avertissement"}`. Un audio vide, illisible ou trop long donne une `422`.

Le front utilise `/transcription` : l'utilisateur relit ce que Whisper a entendu avant d'envoyer, ce qui compte en darija.

## Limites

- Etat de conversation en memoire (1 000 sessions au plus) : il disparait au redemarrage et ne se partage pas entre plusieurs processus.
- Pas d'authentification ni de limitation de debit (prototype). Les origines autorisees sont listees (`FRONTEND_ORIGINS`).
- Whisper tourne sur CPU : ~3 s par question, et le premier appel charge le modele.
