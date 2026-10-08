"""Recupere les pharmacies deja cartographiees au Maroc dans OpenStreetMap.

Source : API Overpass (donnees OSM, licence ODbL -- attribution requise).
Sortie : data/raw/osm_pharmacies.csv (nom, lat, lon, ville, telephone, horaires)

Les positions OSM sont posees par des contributeurs sur le terrain : quand une
pharmacie de notre annuaire y est retrouvee, sa position est exacte, contrairement
au geocodage d'une adresse libre (voir geocode_pharmacies.py, qui prend le relais
pour les autres).

Une seule requete suffit pour tout le pays, donc pas de boucle ni de delai poli :
Overpass renvoie ~2 a 3 minutes de calcul cote serveur.
"""
import csv
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT_PATH = RAW_DIR / "osm_pharmacies.csv"

ENDPOINT = "https://overpass-api.de/api/interpreter"

# `nwr` = nodes, ways et relations : une pharmacie peut etre un simple point ou
# le contour d'un batiment. `out center` donne un couple lat/lon dans les trois
# cas. Le filtre de zone porte sur le code pays, pas sur un nom de pays, qui
# existe en plusieurs graphies.
REQUETE = """
[out:json][timeout:180];
area["ISO3166-1"="MA"][admin_level=2]->.ma;
(
  nwr["amenity"="pharmacy"](area.ma);
);
out center tags;
"""

CHAMPS = ["osm_id", "osm_type", "nom", "lat", "lon", "ville", "telephone", "horaires"]


def extraire(element: dict) -> dict | None:
    tags = element.get("tags", {})
    centre = element if "lat" in element else element.get("center", {})
    lat, lon = centre.get("lat"), centre.get("lon")
    if lat is None or lon is None:
        return None
    return {
        "osm_id": element.get("id"),
        "osm_type": element.get("type"),
        # `name:fr` quand le nom principal est en arabe : notre annuaire est en
        # graphie latine, c'est cette forme-la qui pourra etre rapprochee.
        "nom": tags.get("name") or tags.get("name:fr") or tags.get("name:ar") or "",
        "lat": lat,
        "lon": lon,
        "ville": tags.get("addr:city", ""),
        "telephone": tags.get("phone") or tags.get("contact:phone", ""),
        "horaires": tags.get("opening_hours", ""),
    }


def main() -> None:
    print("Requete Overpass (peut prendre 1 a 3 minutes)...", flush=True)
    reponse = requests.post(
        ENDPOINT,
        data={"data": REQUETE},
        headers={"User-Agent": "DwaTalk/0.1 (projet etudiant, assistant pharmacie Maroc)"},
        timeout=300,
    )
    if not reponse.ok:
        sys.exit(f"Overpass a repondu {reponse.status_code} : {reponse.text[:300]}")

    elements = reponse.json().get("elements", [])
    lignes = [l for l in (extraire(e) for e in elements) if l]

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CHAMPS)
        writer.writeheader()
        writer.writerows(lignes)

    nommees = sum(1 for l in lignes if l["nom"])
    horaires = sum(1 for l in lignes if l["horaires"])
    print(f"{len(lignes)} pharmacies OSM au Maroc -> {OUT_PATH}")
    print(f"  dont {nommees} avec un nom (rapprochables) et {horaires} avec des horaires")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
