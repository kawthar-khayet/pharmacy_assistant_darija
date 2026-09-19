"""LLM few-shot prototype for the pharmacy-assistant NLU (intent + NER).

Builds a system prompt from schema.json + a handful of few-shot examples
from seed_dataset.jsonl, sends the patient's message to a model running on
Ollama Cloud (OpenAI-compatible endpoint), and validates the JSON response
against the schema (intent must be a known id, entity types must be known
types, entity values must actually occur in the input text).

Requires OLLAMA_API_KEY (create one at https://ollama.com/settings/keys),
either as an environment variable or in a `.env` file at the project root
(OLLAMA_API_KEY=...) -- the latter is more reliable since each tool
invocation of this script may run in its own fresh process that does not
inherit a shell's exported variables. Not called automatically -- run
manually (`python nlu/llm_prototype.py "wach kayn doliprane 1g?"`) once
you have a key configured, since it makes a billed/metered API call per run.
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "schema.json"
SEED_PATH = HERE / "seed_dataset.jsonl"
ENV_PATH = HERE.parent / ".env"

OLLAMA_BASE_URL = "https://ollama.com/v1"


def load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE per line, '#' comments) -- avoids
    depending on shell-exported env vars, which don't survive across the
    separate processes each tool invocation runs in."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv(ENV_PATH)

# gpt-oss:20b-cloud is free-tier accessible; qwen3.5:cloud (better multilingual
# support, tried first) returned HTTP 402 -- requires a subscription/credits.
MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:20b-cloud")

# Au moins un exemple par intention, dans des graphies variees (fr / darija
# latine / darija arabe / arabe / mixte). Deux exemples info_pharmacie montrent
# la regle "sidalia" (seed_0020 en arabe, seed_0026 en graphie latine), et
# seed_0034 rappelle qu'un verbe de reservation reste une demande de medicament
# depuis la fusion avec l'ancienne intention commande_reservation. seed_0121 est
# un piege hors sujet ("wach kayn match") qui ressemble a une question de stock.
FEW_SHOT_IDS = [
    "seed_0001",  # disponibilite_medicament, ary_lat
    "seed_0007",  # disponibilite_medicament, mixte, multi-entity
    "seed_0034",  # disponibilite_medicament, ary_lat, "bghit n7goz" (ex-commande)
    "seed_0013",  # prix_remboursement, ary_lat
    "seed_0100",  # alternative_moins_chere, ary_lat
    "seed_0020",  # info_pharmacie, ar, "sidalia" seul -> aucune entite
    "seed_0026",  # info_pharmacie, ary_lat, "sidalia Ibn Sina" -> PHARMACIE="Ibn Sina"
    "seed_0027",  # posologie_information, ary_lat
    "seed_0043",  # conseil_medical, fr
    "seed_0038",  # salutation, ar
    "seed_0121",  # hors_sujet, ary_lat, piege "wach kayn match"
]


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_seed_examples() -> dict[str, dict]:
    examples = {}
    with open(SEED_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            examples[rec["id"]] = rec
    return examples


def build_system_prompt(schema: dict, few_shot: list[dict]) -> str:
    intents = "\n".join(
        f"- {i['id']}: {i['description']}" for i in schema["intents"]
    )
    entities = "\n".join(
        f"- {e['id']}: {e['description']}" for e in schema["entities"]
    )

    shots = []
    for ex in few_shot:
        shots.append(
            "Message: " + ex["text"] + "\n" +
            "Reponse: " + json.dumps({
                "intent": ex["intent"],
                "entities": [
                    {"type": e["type"], "value": e["value"]} for e in ex["entities"]
                ],
            }, ensure_ascii=False)
        )
    shots_block = "\n\n".join(shots)

    return f"""Tu es le module NLU d'un assistant pharmacie au Maroc. Les patients ecrivent
en francais, arabe standard, darija (graphie arabe ou latine), ou en melangeant
ces langues dans la meme phrase.

Pour chaque message, tu dois renvoyer UNIQUEMENT un objet JSON (aucun texte
autour) avec exactement ces champs :
{{"intent": "<un id parmi la liste>", "entities": [{{"type": "<un id parmi la liste>", "value": "<sous-chaine EXACTE du message>"}}]}}

Intents possibles :
{intents}

Types d'entites possibles :
{entities}

Regles :
- "value" doit etre une sous-chaine copiee telle quelle depuis le message (ne pas corriger l'orthographe, ne pas traduire).
- N'invente pas d'entite qui n'est pas explicitement dans le message.
- Si aucune entite n'est presente, renvoie "entities": [].
- Si le message parle de sante sans demande sur un medicament precis, utilise "conseil_medical" ; s'il ne concerne ni les medicaments, ni les pharmacies, ni la sante, utilise "hors_sujet".
- "sidalia", "saydalia", "صيدلية", "pharmacie" sont des noms COMMUNS qui designent
  la pharmacie en general : ce ne sont jamais des entites PHARMACIE. N'extrais une
  entite PHARMACIE que pour le nom propre lui-meme, sans ce mot (dans "sidalia Ibn
  Sina", l'entite est "Ibn Sina", pas "sidalia Ibn Sina"). Si le message dit
  seulement "sidalia" sans nom propre, il n'y a pas d'entite PHARMACIE du tout.

Exemples :
{shots_block}
"""


# Codes que le service renvoie quand il est momentanement sature plutot que
# quand la requete est fautive : ils meritent une seconde chance, alors qu'une
# cle invalide (401) ou un modele payant (402) echoueront toujours.
TRANSIENT_STATUS = {429, 500, 502, 503, 504}
MAX_TENTATIVES = 3


def call_llm(api_key: str, system_prompt: str, text: str) -> dict:
    charge = {
        "model": MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    }

    response = None
    for tentative in range(MAX_TENTATIVES):
        response = requests.post(
            f"{OLLAMA_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=charge,
            timeout=60,
        )
        if response.ok or response.status_code not in TRANSIENT_STATUS:
            break
        if tentative < MAX_TENTATIVES - 1:
            # attente croissante : 1s puis 2s, de quoi laisser passer un pic
            time.sleep(1.5 * (tentative + 1))

    if not response.ok:
        if response.status_code in TRANSIENT_STATUS:
            raise SystemExit(
                "Le modele est momentanement surcharge. Reessaie dans quelques instants."
            )
        raise SystemExit(f"Ollama API error {response.status_code}: {response.text}")
    raw = response.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    # Some models wrap reasoning/text around the JSON despite instructions;
    # fall back to extracting the outermost {...} block if direct parse fails.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise
        return json.loads(raw[start:end + 1])


def validate_output(schema: dict, text: str, parsed: dict) -> list[str]:
    errors = []
    valid_intents = {i["id"] for i in schema["intents"]}
    valid_entities = {e["id"] for e in schema["entities"]}

    if parsed.get("intent") not in valid_intents:
        errors.append(f"intent inconnu: {parsed.get('intent')!r}")

    for ent in parsed.get("entities", []):
        if ent.get("type") not in valid_entities:
            errors.append(f"type d'entite inconnu: {ent.get('type')!r}")
        value = ent.get("value", "")
        if value not in text:
            errors.append(f"valeur d'entite absente du texte source: {value!r}")

    return errors


def run(text: str) -> dict:
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        raise SystemExit(
            "OLLAMA_API_KEY n'est pas configuree. Cree une cle sur "
            "https://ollama.com/settings/keys et mets-la dans un fichier "
            f".env a la racine du projet ({ENV_PATH}) : OLLAMA_API_KEY=ta_cle"
        )

    schema = load_schema()
    seed_examples = load_seed_examples()
    few_shot = [seed_examples[i] for i in FEW_SHOT_IDS if i in seed_examples]

    system_prompt = build_system_prompt(schema, few_shot)

    parsed = call_llm(api_key, system_prompt, text)
    errors = validate_output(schema, text, parsed)

    return {"input": text, "output": parsed, "validation_errors": errors}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print('Usage: python nlu/llm_prototype.py "wach kayn doliprane 1g?"')
        sys.exit(1)
    result = run(" ".join(sys.argv[1:]))
    print(json.dumps(result, ensure_ascii=False, indent=2))
