"""Configuration du moteur nlp/ : chemins, fournisseurs LLM, cles et modeles.

Tout ce qui peut changer d'une machine a l'autre (cles, modeles, ordre des
fournisseurs) se lit dans le fichier .env a la racine du projet ; le reste est
fixe ici, en un seul endroit.
"""
import os
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DATA_CLEAN = RACINE / "data" / "clean"
ENV_PATH = RACINE / ".env"


def charger_env(chemin: Path) -> None:
    """Lecteur .env minimal (CLE=VALEUR par ligne, '#' pour les commentaires).

    Une variable deja definie dans l'environnement garde la priorite sur le
    fichier : pratique pour essayer un autre modele sans modifier le .env.
    """
    if not chemin.exists():
        return
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


charger_env(ENV_PATH)

# Un seul appel REUSSI par message. L'ordre dit qui on essaie en premier ; les
# suivants ne servent que si le precedent echoue (quota, surcharge, delai).
# Un fournisseur sans cle est ignore. Exemple pour n'utiliser que Groq :
# LLM_ORDRE=groq
LLM_ORDRE = [
    nom.strip().lower()
    for nom in os.environ.get("LLM_ORDRE", "gemini,gemini_secours,groq,ollama").split(",")
    if nom.strip()
]

# Les cles peuvent manquer : l'API demarre quand meme, et c'est llm.py qui
# signale clairement l'absence de cle au moment d'appeler un modele.
FOURNISSEURS = {
    "gemini": {
        "cle": os.environ.get("GEMINI_API_KEY", ""),
        # modele rapide, palier gratuit : l'analyse d'une question est courte
        "modele": os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
        "url": "https://generativelanguage.googleapis.com/v1beta",
    },
    # Meme cle, autre modele : quand le modele principal est sature (503),
    # le modele leger, qui a son propre quota, prend le relais.
    "gemini_secours": {
        "cle": os.environ.get("GEMINI_API_KEY", ""),
        "modele": os.environ.get("GEMINI_MODEL_SECOURS", "gemini-3.1-flash-lite"),
        "url": "https://generativelanguage.googleapis.com/v1beta",
    },
    "groq": {
        "cle": os.environ.get("GROQ_API_KEY", ""),
        "modele": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        "url": "https://api.groq.com/openai/v1",   # API compatible OpenAI
    },
    "ollama": {
        "cle": os.environ.get("OLLAMA_API_KEY", ""),
        "modele": os.environ.get("OLLAMA_MODEL", "gpt-oss:120b"),
        "url": "https://ollama.com/api",           # Ollama Cloud, pas un serveur local
    },
}

# On peut attendre un peu, pas au point de laisser le patient sans reponse :
# dans le pire cas (3 fournisseurs qui echouent tous), l'attente reste bornee.
LLM_TIMEOUT = 20         # secondes par tentative
LLM_TENTATIVES = 2       # par fournisseur : 1 appel + 1 relance si surcharge (429, 503)
