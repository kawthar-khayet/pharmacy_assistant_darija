"""Index du RAG : les fiches de fiches.py, rangees dans ChromaDB avec leur vecteur.

Le vecteur d'une fiche resume son sens ; celui d'une question aussi. Chercher
"par le sens", c'est demander a ChromaDB les fiches dont le vecteur est le plus
proche de celui de la question. Le modele tourne sur la machine : pas de cle,
pas de quota.

Construire l'index, une fois, puis apres chaque `py -m nlp.rag.fiches` :
    py -m nlp.rag.index
(premier lancement : telecharge le modele, ~470 Mo ; quelques minutes de calcul)
"""
import json
import os
from functools import lru_cache

from nlp.config import RACINE
from nlp.rag.fiches import FICHES_PATH

INDEX_PATH = RACINE / "data" / "rag" / "chroma"
COLLECTION = "fiches"
MODELE_EMBEDDINGS = os.environ.get("EMBEDDINGS_MODEL", "intfloat/multilingual-e5-small")

# Les modeles e5 attendent ces prefixes : sans eux, la recherche est nettement moins bonne.
PREFIXE_FICHE = "passage: "
PREFIXE_QUESTION = "query: "
LOT = 256   # fiches envoyees a ChromaDB en une fois


@lru_cache(maxsize=1)
def modele():
    # import ici : l'API demarre sans attendre le chargement de torch
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(MODELE_EMBEDDINGS)


def _vecteurs(textes: list[str], prefixe: str) -> list[list[float]]:
    # vecteurs normalises : la distance "cosine" de ChromaDB compare alors le sens seul
    return modele().encode([prefixe + t for t in textes], normalize_embeddings=True,
                           batch_size=32).tolist()


def vecteur_question(question: str) -> list[float]:
    return _vecteurs([question], PREFIXE_QUESTION)[0]


def _client():
    import chromadb
    return chromadb.PersistentClient(path=str(INDEX_PATH))


@lru_cache(maxsize=1)
def collection():
    """La collection des fiches, ouverte une seule fois pour toute l'API."""
    return _client().get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def lire_fiches() -> list[dict]:
    with FICHES_PATH.open(encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f if ligne.strip()]


def construire() -> int:
    """Refait l'index a partir de fiches.jsonl ; renvoie le nombre de fiches."""
    fiches = lire_fiches()
    client = _client()
    try:
        # on repart de zero : une fiche disparue des CSV ne doit pas rester dans l'index
        client.delete_collection(COLLECTION)
    except Exception:
        pass   # premier lancement : rien a supprimer
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    for debut in range(0, len(fiches), LOT):
        lot = fiches[debut:debut + LOT]
        textes = [f["texte"] for f in lot]
        col.upsert(
            ids=[f["id"] for f in lot],
            documents=textes,
            embeddings=_vecteurs(textes, PREFIXE_FICHE),
            # le type rejoint meta : ChromaDB filtre dessus ("seulement les notices")
            metadatas=[{"type": f["type"], **f["meta"]} for f in lot],
        )
        print(f"  {min(debut + LOT, len(fiches))} / {len(fiches)}")
    collection.cache_clear()
    return len(fiches)


def main():
    if not FICHES_PATH.exists():
        raise SystemExit("fiches.jsonl absent : lance d'abord  py -m nlp.rag.fiches")
    print(f"{construire()} fiches indexees dans {INDEX_PATH}")


if __name__ == "__main__":
    main()
