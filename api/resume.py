"""Resume court, en darija, des rubriques de securite d'une molecule.

Le texte officiel reste la reference et continue d'etre affiche en entier : ce
resume ne le remplace pas, il sert de porte d'entree a quelqu'un qui ne lit pas
le francais medical.

Trois precautions, parce qu'un modele qui reecrit une contre-indication peut
produire une erreur de sante et non une maladresse de style :

1. Le prompt interdit d'ajouter quoi que ce soit. Le modele n'a le droit de
   reprendre que ce qui est dans le texte fourni, et on le lui dit deux fois.
2. Aucun conseil, aucune posologie, aucune dose : ce sont les deux terrains ou
   une invention serait la plus dangereuse.
3. Le resume est marque comme automatique cote interface, et le texte officiel
   est toujours affiche dessous.

Les resumes sont mis en cache sur disque : une molecule a un texte stable, il
n'y a aucune raison de payer un appel par affichage. Le cache est la seule
memoire du module -- si la cle Gemini manque, l'API repond simplement sans
resume, et l'interface n'affiche que le texte officiel.
"""
import json
import os
import time

import requests

# nlp.config lit le .env a l'import : la cle Gemini est alors dans l'environnement.
from nlp.config import FOURNISSEURS
from nlp.outils.securite import EXPLICATIONS_PATH, RESUMES_PATH

GEMINI_BASE_URL = FOURNISSEURS["gemini"]["url"]
# Meme fichier que celui que lit le bot (nlp/outils/securite.py).
CACHE_PATH = RESUMES_PATH

# Modele distinct de celui du NLU, et volontairement plus leger : resumer un
# texte fourni est plus simple que comprendre une phrase en darija. Surtout,
# le palier gratuit compte ses quotas PAR MODELE et PAR JOUR -- 20 requetes
# par jour pour gemini-3.5-flash. Faire porter les resumes par un autre modele
# evite qu'ils epuisent le quota dont le NLU a besoin pour repondre aux
# patients. Changeable par GEMINI_MODEL_RESUME.
MODELE = os.environ.get("GEMINI_MODEL_RESUME", "gemini-3.1-flash-lite")

# Le resume tient en trois phrases : au-dela, il cesse d'etre une porte
# d'entree et redevient un pave, ce que le texte officiel fait deja mieux.
MAX_PHRASES = 3

# Codes renvoyes quand le service est momentanement sature : ils meritent une
# seconde chance, contrairement a une cle invalide.
#
# Le 429 (quota par minute du palier gratuit) en est absent volontairement :
# l'attendre demanderait de tenir la requete du patient pendant une minute
# entiere. On abandonne le resume pour cette fois -- le texte officiel s'affiche
# quand meme -- et c'est scripts/precalculer_resumes.py, lance a froid, qui
# remplit le cache sans presser personne.
STATUTS_PASSAGERS = {500, 502, 503, 504}
MAX_TENTATIVES = 3

CONSIGNES = {
    "ary_lat": "darija marocaine ecrite en lettres latines (arabizi)",
    "ary_ar": "darija marocaine ecrite en lettres arabes",
    "ar": "arabe standard",
    "fr": "francais simple",
}

# Rubriques resumees, dans l'ordre : ce qui interdit la prise d'abord.
ORDRE = ["contre_indications", "precautions", "interactions", "effets_indesirables"]


def _prompt(langue: str) -> str:
    return f"""Tu resumes une notice de medicament pour un patient au Maroc.

Ecris en {CONSIGNES.get(langue, CONSIGNES['fr'])}, au maximum {MAX_PHRASES} phrases courtes.

Regles absolues :
- N'ecris QUE ce qui figure dans le texte fourni. N'ajoute aucune information,
  meme si elle te parait evidente ou utile.
- Ne donne jamais de dose, de posologie, de duree de traitement ni de conseil
  personnel, meme si le texte en contient.
- Ne rassure pas et ne dramatise pas : rapporte, c'est tout.
- Nomme les organes et les maladies exactement comme le texte les nomme. Un
  premier essai a ecrit "estomac" la ou la notice disait "foie" : c'est le
  genre d'erreur qui rend ce resume dangereux.
- N'ajoute aucune explication entre parentheses, aucun synonyme, aucune
  traduction d'un terme par un autre.
- Si le texte ne permet pas de resumer, reponds exactement : RIEN.
- Termine par une phrase qui invite a lire le texte officiel en dessous ou a
  demander au pharmacien.

Donne la priorite a ce qui interdit de prendre le medicament, puis aux effets
indesirables les plus frequents."""


def _charger_cache(chemin=None) -> dict:
    chemin = chemin or CACHE_PATH
    if chemin.exists():
        try:
            return json.loads(chemin.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _ecrire_cache(cache: dict, chemin=None) -> None:
    chemin = chemin or CACHE_PATH
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _texte_source(rubriques: dict) -> str:
    morceaux = []
    for cle in ORDRE:
        valeur = rubriques.get(cle)
        if valeur:
            # Chaque rubrique est bornee : un prompt de 20 000 caracteres coute
            # cher et n'ameliore pas un resume de trois phrases.
            morceaux.append(f"[{cle}]\n{valeur[:2500]}")
    return "\n\n".join(morceaux)


def _appeler_gemini(cle_api: str, consigne: str, texte: str, json_sortie: bool = False) -> str | None:
    charge = {
        "system_instruction": {"parts": [{"text": consigne}]},
        "contents": [{"role": "user", "parts": [{"text": texte}]}],
        "generationConfig": {
            # Temperature nulle : aucune variation creative sur un contenu
            # medical.
            "temperature": 0,
            # 6 rubriques expliquees en arabe depassent 1200 jetons ; une
            # reponse coupee reste rejetee plus bas (finishReason).
            "maxOutputTokens": 2000,
            # Sans cette ligne, le modele depense son budget de sortie en
            # raisonnement interne (341 jetons de "pensees" pour 18 jetons de
            # reponse) : les premiers resumes produits etaient coupes en plein
            # milieu, et l'un d'eux contenait le raisonnement lui-meme
            # ("Confidence Score: 1. Simple French? Yes."). La tache est un
            # resume extractif, elle ne demande aucune reflexion.
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    if json_sortie:
        charge["generationConfig"]["responseMimeType"] = "application/json"
    # Le service repond parfois 503 le temps d'un pic : sans reessai, la
    # molecule restait sans resume jusqu'au prochain affichage.
    reponse = None
    for tentative in range(MAX_TENTATIVES):
        try:
            reponse = requests.post(
                f"{GEMINI_BASE_URL}/models/{MODELE}:generateContent",
                headers={"x-goog-api-key": cle_api, "Content-Type": "application/json"},
                json=charge,
                timeout=30,
            )
        except requests.RequestException:
            return None
        if reponse.ok or reponse.status_code not in STATUTS_PASSAGERS:
            break
        if tentative < MAX_TENTATIVES - 1:
            time.sleep(1.5 * (tentative + 1))

    if not reponse.ok:
        return None
    try:
        candidat = reponse.json()["candidates"][0]
        # Une reponse coupee (MAX_TOKENS) ou filtree (SAFETY) s'arrete en plein
        # milieu d'une phrase : sur une contre-indication, une phrase coupee
        # peut dire l'inverse de la notice. On la jette.
        if candidat.get("finishReason") != "STOP":
            return None
        return candidat["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return None


def resumer(securite: dict, langue: str = "ary_lat") -> str | None:
    """Resume en langue du patient, ou None : pas de cle, pas de reseau, texte
    trop maigre, ou modele qui repond RIEN. L'absence de resume n'est jamais une
    erreur -- le texte officiel, lui, est toujours la."""
    rubriques = securite.get("rubriques") or {}
    texte = _texte_source(rubriques)
    if not texte:
        return None

    cle_cache = f"{securite.get('dci')}|{langue}"
    cache = _charger_cache()
    if cle_cache in cache:
        return cache[cle_cache]

    cle_api = os.environ.get("GEMINI_API_KEY")
    if not cle_api:
        return None

    produit = _appeler_gemini(cle_api, _prompt(langue), texte)
    if not produit or produit.strip().upper().startswith("RIEN"):
        return None

    cache[cle_cache] = produit
    _ecrire_cache(cache)
    return produit


# --- Explications simples, rubrique par rubrique (reponses du chat) -------------

def _prompt_explications(langue: str) -> str:
    return f"""Tu expliques une notice de medicament a un patient au Maroc qui n'est pas du metier.

Ecris en {CONSIGNES.get(langue, CONSIGNES['fr'])}.

Pour chaque rubrique fournie, ecris 1 ou 2 phrases courtes avec des mots de tous les jours :
- [indications] : les maladies et les symptomes que le medicament soigne ;
- les autres rubriques : l'essentiel de ce que le patient doit savoir.

Regles absolues :
- N'ecris QUE ce qui figure dans le texte de la rubrique. N'ajoute aucune information.
- Pas de jargon : ni famille pharmacologique pour dire a quoi sert le medicament
  (pas "anti-inflammatoire non steroidien"), ni nom de marque, ni dosage, ni forme.
  Si une contre-indication ou une interaction cite une famille de medicaments,
  garde-la, dite simplement : la supprimer serait dangereux.
- Ne donne jamais de dose, de posologie, de duree de traitement ni de conseil personnel.
- Garde le sens exact : nomme les organes et les maladies comme la notice (le foie
  reste le foie), avec le mot courant de la langue demandee.
- Ne rassure pas et ne dramatise pas : rapporte, c'est tout.

Reponds uniquement en JSON : un objet dont les cles sont les rubriques fournies et
les valeurs tes phrases, ou null si le texte ne permet pas d'expliquer."""


def expliquer(fiche: dict, langue: str) -> dict | None:
    """Une explication simple par rubrique, dans la langue du patient, ou None
    (pas de cle, pas de reseau, reponse coupee ou illisible). Mise en cache."""
    cle_cache = f"{fiche.get('dci')}|{langue}"
    cache = _charger_cache(EXPLICATIONS_PATH)
    if cle_cache in cache:
        return cache[cle_cache]
    rubriques = fiche.get("rubriques") or {}
    texte = "\n\n".join(f"[{r}]\n{t[:2500]}" for r, t in rubriques.items() if t)
    cle_api = os.environ.get("GEMINI_API_KEY")
    if not texte or not cle_api:
        return None
    produit = _appeler_gemini(cle_api, _prompt_explications(langue), texte, json_sortie=True)
    try:
        brut = json.loads(produit or "")
    except json.JSONDecodeError:
        return None
    if not isinstance(brut, dict):
        return None
    explications = {r: v.strip() for r, v in brut.items()
                    if r in rubriques and isinstance(v, str) and v.strip()}
    if not explications:
        return None
    cache[cle_cache] = explications
    _ecrire_cache(cache, EXPLICATIONS_PATH)
    return explications
