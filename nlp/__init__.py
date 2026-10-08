"""Moteur de comprehension et de reponse de DwaTalk.

Un seul appel LLM par message (Gemini ; secours : un second modele Gemini,
puis Groq et Ollama Cloud si leurs cles sont dans le .env) : le modele analyse
la question, le code cherche dans data/ et redige la reponse.

    moteur.py    un message -> une reponse (enchaine tout ce qui suit)
    analyse/     comprendre la question (seul appel LLM) + validation + filet urgence
    linking/     retrouver medicaments, lieux et pharmacies malgre les fautes
    outils/      chercher dans les donnees (liste blanche)
    reponse/     composer une reponse courte, seulement ce qui est demande
    preparation/ scripts lances une fois, hors conversation
"""
