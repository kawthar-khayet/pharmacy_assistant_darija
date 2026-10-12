"""Moteur de comprehension et de reponse de DwaTalk (RAG).

Deux appels LLM par message (Gemini ; secours : un second modele Gemini, puis
Groq et Ollama Cloud si leurs cles sont dans le .env) : le premier comprend la
question et dit quoi chercher, le code cherche les fiches dans nos donnees, le
second redige la reponse avec ces fiches seulement.

    moteur.py    un message -> une reponse (enchaine tout ce qui suit)
    rag/         fiches (data/ en textes), index (ChromaDB), comprendre (1er appel),
                 recherche (noms, distance, sens), repondre.md (regles du 2e appel)
    analyse/     filet urgence par mots-cles, avant tout appel LLM
    linking/     retrouver medicaments, lieux et pharmacies malgre les fautes
    outils/      pharmacies d'un lieu, de garde, par nom ; prix et notices pour les fiches
    reponse/     langue du patient ; phrases fixes (urgence, service en panne)
    preparation/ scripts lances une fois, hors conversation
"""
