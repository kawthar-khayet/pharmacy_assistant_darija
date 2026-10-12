"""Pharmacies de garde du jour, lues sur Telecontact (les Pages Jaunes du Maroc).

Nos bases ne connaissent aucun tour de garde. Telecontact le publie chaque
jour, par ville et par quartier, avec le nom, l'adresse, le telephone et la
position de chaque officine (donnees structurees JSON-LD dans la page).

A la demande : la premiere question sur une ville va lire ses pages, puis le
resultat est garde pour la journee (en memoire et dans data/rag/garde/) ; les
autres villes ne sont jamais telechargees. Si le site ne repond pas ou ne
couvre pas la ville, `garde_du_jour` rend None et le bot retombe sur les
pharmacies ouvertes 24h/24 ou la nuit d'apres leurs horaires.

Trois listes par quartier : toutes les officines de garde, celles de nuit et
celles ouvertes 24h/24 ; une officine absente des deux dernieres est de jour.
"""
import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import requests
from bs4 import BeautifulSoup

from nlp.config import RACINE
from nlp.linking.medicaments import normalize

log = logging.getLogger(__name__)

BASE = "https://www.telecontact.ma"
INDEX_URL = f"{BASE}/services/pharmacies-de-garde/Maroc"
SOURCE = "Telecontact"
# On se presente : le site peut ainsi nous reconnaitre, et nous bloquer s'il le souhaite.
ENTETES = {"User-Agent": "DwaTalk/1.0 (assistant pharmacie, projet etudiant)"}
DELAI = 10              # secondes par page
EN_PARALLELE = 6        # pages lues en meme temps : assez pour ne pas attendre, sans charger le site
CACHE_DIR = RACINE / "data" / "rag" / "garde"

_LIEN_VILLE = re.compile(r"/services/pharmacies-de-garde/(.+)-Maroc$")
_LIEN_QUARTIER = re.compile(r"/pharmacie-de-garde-zone/([^/]+)/([^/]+)\.html$")
# numeros des listes filtrees du site
NUIT, H24 = 2, 3

_verrou = threading.Lock()
_memoire: dict[tuple[str, str], dict | None] = {}     # (jour, ville) -> garde
_villes: dict[str, dict[str, str]] = {}               # jour -> {cle de ville: url}


def _page(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=ENTETES, timeout=DELAI)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def _donnees(page: BeautifulSoup) -> list[dict]:
    """Les blocs JSON-LD de la page ; un bloc illisible est ignore."""
    blocs = []
    for script in page.find_all("script", type="application/ld+json"):
        try:
            bloc = json.loads(script.string or "")
        except json.JSONDecodeError:
            continue
        if isinstance(bloc, dict):
            blocs.append(bloc)
    return blocs


def _liste(page: BeautifulSoup) -> list[dict]:
    for bloc in _donnees(page):
        if bloc.get("@type") == "ItemList":
            return bloc.get("itemListElement") or []
    return []


def _date(page: BeautifulSoup) -> str | None:
    """Le jour de garde annonce par la page ("2026-10-12")."""
    for bloc in _donnees(page):
        if bloc.get("@type") == "DataFeedItem":
            return bloc.get("dateModified")
    return None


def _texte(x) -> str | None:
    x = re.sub(r"\s+", " ", str(x or "")).strip()
    return x or None


def _nombre(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _pharmacies(page: BeautifulSoup) -> list[dict]:
    pharmacies = []
    for element in _liste(page):
        item = element.get("item") or {}
        nom = _texte(item.get("name"))
        if not nom:
            continue
        adresse, geo = item.get("address") or {}, item.get("geo") or {}
        pharmacies.append({
            "nom": nom,
            "adresse": _texte(adresse.get("streetAddress")),
            "ville": _texte(adresse.get("addressLocality")),
            "telephone": _texte(item.get("telephone")),
            "latitude": _nombre(geo.get("latitude")),
            "longitude": _nombre(geo.get("longitude")),
        })
    return pharmacies


def _quartiers(page: BeautifulSoup) -> list[tuple[str, str, str]]:
    """(nom du quartier, ville et quartier tels qu'ecrits dans l'adresse du site)."""
    quartiers = []
    for element in _liste(page):
        m = _LIEN_QUARTIER.search(element.get("url") or "")
        if m:
            nom = re.sub(r"^Pharmacie de garde\s+", "", element.get("name") or "").strip()
            quartiers.append((nom, m.group(1), m.group(2)))
    return quartiers


def _quartier(args: tuple[str, str, str]) -> tuple[list[dict], str | None]:
    """Les officines de garde d'un quartier, avec leur type d'ouverture."""
    nom, ville, quartier = args
    toutes = _page(f"{BASE}/pharmacie-de-garde-zone/{ville}/{quartier}.html")

    def noms(filtre: int) -> set[str]:
        page = _page(f"{BASE}/pharmacie-de-garde-zone-jour/{ville}/{filtre}/{quartier}.html")
        return {p["nom"] for p in _pharmacies(page)}

    nuit, h24 = noms(NUIT), noms(H24)
    pharmacies = _pharmacies(toutes)
    for p in pharmacies:
        p["quartier"] = nom
        p["ouverture"] = "24h" if p["nom"] in h24 else "nuit" if p["nom"] in nuit else "jour"
    return pharmacies, _date(toutes)


def _villes_couvertes(jour: str) -> dict[str, str]:
    """Cle de ville -> adresse de sa page, lue une fois par jour."""
    if jour not in _villes:
        villes = {}
        for lien in _page(INDEX_URL).find_all("a", href=True):
            m = _LIEN_VILLE.search(lien["href"])
            if m:
                villes[normalize(m.group(1))] = BASE + lien["href"]
        _villes.clear()
        _villes[jour] = villes
    return _villes[jour]


def _lire(ville: str, jour: str) -> dict | None:
    url = _villes_couvertes(jour).get(normalize(ville))
    if not url:
        return None                       # ville absente de Telecontact
    quartiers = _quartiers(_page(url))
    with ThreadPoolExecutor(EN_PARALLELE) as ex:
        resultats = list(ex.map(_quartier, quartiers))

    pharmacies, vues, dates = [], set(), set()
    for trouvees, jour_page in resultats:
        if jour_page:
            dates.add(jour_page)
        for p in trouvees:
            cle = (p["nom"], p["adresse"])
            if cle not in vues:           # une officine peut figurer dans deux quartiers
                vues.add(cle)
                pharmacies.append(p)
    if not pharmacies:
        return None
    return {"ville": ville, "date": max(dates) if dates else jour, "source": SOURCE,
            "pharmacies": pharmacies}


def garde_du_jour(ville: str | None) -> dict | None:
    """Les pharmacies de garde de la ville aujourd'hui, ou None si on ne sait pas.

    {"ville", "date" (celle annoncee par le site), "source", "pharmacies": [{"nom",
    "adresse", "ville", "quartier", "telephone", "latitude", "longitude",
    "ouverture": "jour" | "nuit" | "24h"}]}
    """
    if not ville:
        return None
    jour = date.today().isoformat()
    cle = (jour, ville)
    with _verrou:                         # deux patients, une seule lecture du site
        if cle in _memoire:
            return _memoire[cle]
        fichier = CACHE_DIR / f"{jour}_{normalize(ville).replace(' ', '_')}.json"
        if fichier.exists():
            garde = json.loads(fichier.read_text(encoding="utf-8"))
        else:
            try:
                garde = _lire(ville, jour)
            except (requests.RequestException, ValueError) as e:
                # panne passagere : on ne retient rien, la prochaine question reessaiera
                log.warning("garde du jour indisponible pour %s : %s", ville, e)
                return None
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            fichier.write_text(json.dumps(garde, ensure_ascii=False), encoding="utf-8")
        for ancienne in [c for c in _memoire if c[0] != jour]:
            del _memoire[ancienne]
        _memoire[cle] = garde
        return garde
