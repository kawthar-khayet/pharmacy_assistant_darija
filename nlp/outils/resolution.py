"""Le matcher de medicaments, partage par tout le serveur."""
from functools import lru_cache

from nlp.linking.medicaments import MedicamentMatcher


@lru_cache(maxsize=1)
def matcher() -> MedicamentMatcher:
    """La base (~20 000 lignes) n'est chargee qu'une fois par serveur."""
    return MedicamentMatcher()
