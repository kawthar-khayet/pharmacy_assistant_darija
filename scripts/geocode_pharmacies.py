"""Ajoute des coordonnees GPS a l'annuaire des pharmacies.

Entrees :
  - data/clean/pharmacies_reference.csv  (2652 pharmacies, adresse libre)
  - data/raw/osm_pharmacies.csv          (pharmacies OSM, via fetch_osm_pharmacies.py)

Sorties :
  - data/clean/pharmacies_reference.csv  (colonnes latitude, longitude,
    precision_gps, source_gps ajoutees)
  - data/clean/pharmacies_geo_report.txt (couverture par source et par precision)

Deux passes, dans cet ordre de fiabilite :

1. OSM : une pharmacie de notre annuaire retrouvee dans OpenStreetMap par son
   nom, a portee du centre de sa ville, herite d'une position posee sur le
   terrain -- la meilleure qu'on puisse avoir.
2. Nominatim : pour les autres, on geocode l'adresse telle qu'elle est ecrite.
   Les adresses de l'annuaire sont libres ("hay essalam, imm. bicha, cplxe azrou
   AGADIR"), donc le resultat retombe souvent sur la rue ou le quartier.

`precision_gps` dit laquelle de ces situations s'applique (`exacte`, `rue`,
`quartier`, `ville`). L'interface ne doit poser une epingle que pour `exacte` :
une position de niveau ville affichee comme l'adresse d'une officine enverrait
quelqu'un au mauvais endroit, de nuit, pour une urgence.

Le cache (data/raw/nominatim_cache.json) est ecrit au fil de l'eau : le script
peut etre interrompu et relance sans refaire les appels deja faits.

Usage :
    py scripts/fetch_osm_pharmacies.py   # une fois, pour la source OSM
    py scripts/geocode_pharmacies.py     # ~45 min la premiere fois
    py scripts/geocode_pharmacies.py --osm-seulement   # sans appel reseau
"""
import json
import math
import re
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests
from rapidfuzz import fuzz, process

ROOT = Path(__file__).resolve().parent.parent
PHARMA_PATH = ROOT / "data" / "clean" / "pharmacies_reference.csv"
OSM_PATH = ROOT / "data" / "raw" / "osm_pharmacies.csv"
CACHE_PATH = ROOT / "data" / "raw" / "nominatim_cache.json"
VILLES_PATH = ROOT / "data" / "raw" / "villes_geo.json"
RAPPORT_PATH = ROOT / "data" / "clean" / "pharmacies_geo_report.txt"

NOMINATIM = "https://nominatim.openstreetmap.org/search"
# La politique d'usage de Nominatim impose un User-Agent identifiable et au
# plus une requete par seconde. 1,1 s laisse une marge.
ENTETES = {"User-Agent": "DwaTalk/0.1 (projet etudiant Maroc; contact via depot du projet)"}
DELAI_S = 1.1

# Rayon de recherche autour du centre-ville pour accepter un candidat OSM.
# 25 km couvre l'etalement de Casablanca ou Marrakech sans permettre qu'une
# "Pharmacie Al Amal" de Rabat soit rapprochee de son homonyme de Sale.
RAYON_VILLE_KM = 25
# Seuil de ressemblance des noms. 88 laisse passer les variantes d'ecriture
# ("Pharmacie Al Firdaous" / "Pharmacie Al Firdawss") mais pas deux noms
# differents. Un ecart d'au moins 6 points avec le deuxieme candidat est exige
# en plus, pour ne pas trancher au hasard entre deux homonymes proches.
SEUIL_NOM = 88
ECART_MIN = 6

# Mots qui designent l'officine en general : ils sont dans presque tous les
# noms des deux cotes et gonfleraient artificiellement les scores.
MOTS_VIDES = {"pharmacie", "pharmacy", "parapharmacie", "صيدلية", "de", "du", "la", "le", "l"}


def sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")


def cle_nom(nom) -> str:
    if pd.isna(nom):
        return ""
    s = sans_accents(nom).lower()
    s = re.sub(r"[^a-z0-9؀-ۿ ]+", " ", s)
    mots = [m for m in s.split() if m not in MOTS_VIDES]
    return " ".join(mots)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance orthodromique (formule de haversine), en kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def charger_cache(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def ecrire_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def interroger_nominatim(requete: str) -> dict | None:
    """Un resultat Nominatim, ou None. Les erreurs reseau ne sont pas fatales :
    une pharmacie sans position vaut mieux qu'un script qui s'arrete au bout de
    2000 appels reussis."""
    try:
        reponse = requests.get(
            NOMINATIM,
            params={"q": requete, "format": "jsonv2", "limit": 1, "countrycodes": "ma",
                    "addressdetails": 1},
            headers=ENTETES,
            timeout=30,
        )
        if not reponse.ok:
            return None
        resultats = reponse.json()
        return resultats[0] if resultats else None
    except (requests.RequestException, ValueError):
        return None


# Ce que Nominatim renvoie comme type de lieu, traduit en niveau de precision.
# Tout ce qui n'est pas liste retombe sur "quartier" : mieux vaut sous-estimer
# la precision que laisser croire a une adresse exacte.
PRECISION_PAR_TYPE = {
    "pharmacy": "exacte", "building": "exacte", "house": "exacte", "shop": "exacte",
    "amenity": "exacte", "commercial": "exacte", "retail": "exacte",
    "road": "rue", "residential": "rue", "street": "rue", "highway": "rue",
    "city": "ville", "town": "ville", "village": "ville", "municipality": "ville",
    "administrative": "ville", "state": "ville", "province": "ville",
}


def precision_de(resultat: dict) -> str:
    for cle in ("addresstype", "type", "category", "class"):
        valeur = resultat.get(cle)
        if valeur in PRECISION_PAR_TYPE:
            return PRECISION_PAR_TYPE[valeur]
    return "quartier"


# Elements d'adresse que Nominatim ne sait pas exploiter et qui font echouer la
# requete entiere : numero d'immeuble, de lot, de bloc, d'appartement.
DETAILS_BATIMENT = re.compile(
    r"(?i)\b(imm\.?|immeuble|r[ée]sid(ence)?\.?|lot(issement)?\.?|bloc|n[°o]\s*\d+|appt\.?|"
    r"apt\.?|cplxe|complexe|magasin|mag\.?|etage|[ée]tg\.?|rdc|ang\.?|angle|face|pr[èe]s de)\b[^,]*"
)
# Mots qui introduisent un quartier dans les adresses marocaines.
MOTS_QUARTIER = re.compile(r"(?i)\b(hay|hy|quartier|qu?tr?\.?|cit[ée]|sectuer|secteur|douar)\s+([\w' -]{3,30})")


def adresse_simplifiee(adresse) -> str:
    """Adresse reduite a sa voie : les details de batiment font echouer la
    requete entiere, alors que le boulevard seul se retrouve."""
    texte = DETAILS_BATIMENT.sub("", str(adresse))
    texte = re.sub(r"\d+", "", texte)
    return re.sub(r"[ ,]{2,}", ", ", texte).strip(" ,-")


def quartier_de(adresse) -> str | None:
    trouve = MOTS_QUARTIER.search(str(adresse))
    return trouve.group(0).strip(" ,-") if trouve else None


# Du plus precis au plus vague.
ORDRE_PRECISION = ["exacte", "rue", "quartier", "ville"]
# Ce qu'une requete peut donner au mieux : chercher un quartier ne situe pas
# l'officine, meme quand Nominatim repond par un batiment de ce quartier.
PLAFOND_PAR_ORIGINE = {"adresse": "exacte", "nom": "exacte", "voie": "rue", "quartier": "quartier"}


def precision_bornee(precision: str, origine: str) -> str:
    plafond = PLAFOND_PAR_ORIGINE.get(origine, "ville")
    if ORDRE_PRECISION.index(precision) < ORDRE_PRECISION.index(plafond):
        return plafond
    return precision


def cherche_avec_cache(requete: str, cache: dict) -> dict | None:
    """Une recherche Nominatim, memorisee -- y compris ses echecs, pour ne pas
    redemander eternellement une adresse introuvable."""
    if requete not in cache:
        resultat = interroger_nominatim(requete)
        cache[requete] = (
            {"lat": resultat["lat"], "lon": resultat["lon"], "precision": precision_de(resultat)}
            if resultat else None
        )
        ecrire_cache(CACHE_PATH, cache)
        time.sleep(DELAI_S)
    return cache[requete]


def geocoder_ligne(ligne: pd.Series, cache: dict, centres: dict) -> dict | None:
    """Position d'une pharmacie, du plus precis au plus approximatif.

    Les adresses de l'annuaire sont ecrites a la main ("7 hay taddart - secteur
    a lot 5 anza") : demandees telles quelles, 93 % ne donnent rien. On essaie
    donc, dans l'ordre : le nom de l'officine (Nominatim connait beaucoup de
    pharmacies comme lieux), la voie seule, puis le quartier. Le centre de la
    ville ferme la marche -- il ne situe pas l'officine, mais il permet de
    cadrer un plan, et sa precision le dit."""
    ville = ligne.get("ville")
    ville_txt = str(ville) if pd.notna(ville) else ""

    tentatives = [
        ("adresse", f"{ligne.get('adresse')}, {ville_txt}, Maroc"
         if pd.notna(ligne.get("adresse")) else None),
        ("nom", f"{ligne.get('nom')}, {ville_txt}, Maroc"
         if pd.notna(ligne.get("nom")) else None),
        ("voie", f"{adresse_simplifiee(ligne.get('adresse'))}, {ville_txt}, Maroc"
         if pd.notna(ligne.get("adresse")) and adresse_simplifiee(ligne.get("adresse")) else None),
        ("quartier", f"{quartier_de(ligne.get('adresse'))}, {ville_txt}, Maroc"
         if quartier_de(ligne.get("adresse")) else None),
    ]
    centre = centres.get(ville_txt)
    for origine, requete in tentatives:
        if not requete:
            continue
        trouve = cherche_avec_cache(requete, cache)
        if not trouve:
            continue
        # Nominatim repond parfois avec un lieu homonyme a l'autre bout du pays
        # ("Pharmacie Al Amal" existe partout) : hors du secteur de la ville
        # annoncee, le resultat est ecarte plutot que corrige.
        if centre and distance_km(
            centre["lat"], centre["lon"], float(trouve["lat"]), float(trouve["lon"])
        ) > RAYON_VILLE_KM:
            continue
        return {
            **trouve,
            "precision": precision_bornee(trouve["precision"], origine),
            "source": f"nominatim_{origine}",
        }

    centre = centres.get(ville_txt)
    if centre:
        # Deja en cache depuis la passe 1 : aucune requete supplementaire.
        return {"lat": centre["lat"], "lon": centre["lon"], "precision": "ville",
                "source": "centre_ville"}
    return None


def centres_villes(villes: list[str], cache: dict) -> dict:
    """Centre approximatif de chaque ville, pour borner la recherche OSM."""
    manquantes = [v for v in villes if v not in cache]
    for i, ville in enumerate(manquantes, start=1):
        resultat = interroger_nominatim(f"{ville}, Maroc")
        cache[ville] = (
            {"lat": float(resultat["lat"]), "lon": float(resultat["lon"])} if resultat else None
        )
        print(f"  ville {i}/{len(manquantes)} : {ville}", flush=True)
        ecrire_cache(VILLES_PATH, cache)
        time.sleep(DELAI_S)
    return cache


def apparier_osm(pharmacies: pd.DataFrame, osm: pd.DataFrame, centres: dict) -> dict:
    """Pour chaque pharmacie de l'annuaire, le meilleur candidat OSM du meme
    secteur, si son nom est assez ressemblant et nettement meilleur que le
    suivant. Renvoie {index annuaire: (lat, lon)}."""
    osm = osm[osm["nom"].astype(str).str.strip() != ""].copy()
    osm["cle"] = osm["nom"].map(cle_nom)
    osm = osm[osm["cle"] != ""]

    trouves = {}
    for ville, groupe in pharmacies.groupby("ville"):
        centre = centres.get(ville)
        if not centre:
            continue
        proches = osm[
            osm.apply(
                lambda r: distance_km(centre["lat"], centre["lon"], r["lat"], r["lon"])
                <= RAYON_VILLE_KM,
                axis=1,
            )
        ]
        if proches.empty:
            continue
        candidats = proches["cle"].tolist()
        for idx, ligne in groupe.iterrows():
            cle = cle_nom(ligne["nom"])
            if not cle:
                continue
            meilleurs = process.extract(cle, candidats, scorer=fuzz.WRatio, limit=2)
            if not meilleurs or meilleurs[0][1] < SEUIL_NOM:
                continue
            if len(meilleurs) > 1 and meilleurs[0][1] - meilleurs[1][1] < ECART_MIN:
                continue  # deux homonymes aussi proches : on ne tranche pas
            gagnant = proches.iloc[meilleurs[0][2]]
            trouves[idx] = (float(gagnant["lat"]), float(gagnant["lon"]))
    return trouves


def main(osm_seulement: bool = False) -> None:
    pharmacies = pd.read_csv(PHARMA_PATH)
    osm = pd.read_csv(OSM_PATH)
    print(f"{len(pharmacies)} pharmacies dans l'annuaire, {len(osm)} dans OSM", flush=True)

    for colonne in ("latitude", "longitude", "precision_gps", "source_gps"):
        if colonne not in pharmacies.columns:
            pharmacies[colonne] = None

    villes = sorted(pharmacies["ville"].dropna().unique())
    cache_villes = charger_cache(VILLES_PATH)
    if not osm_seulement or any(v not in cache_villes for v in villes):
        print(f"Centres des {len(villes)} villes...", flush=True)
        cache_villes = centres_villes(villes, cache_villes)

    print("Passe 1 : rapprochement avec OpenStreetMap...", flush=True)
    apparies = apparier_osm(pharmacies, osm, cache_villes)
    for idx, (lat, lon) in apparies.items():
        pharmacies.loc[idx, ["latitude", "longitude", "precision_gps", "source_gps"]] = [
            lat, lon, "exacte", "osm",
        ]
    print(f"  {len(apparies)} pharmacies retrouvees dans OSM", flush=True)

    if not osm_seulement:
        restantes = pharmacies[pharmacies["latitude"].isna()]
        print(f"Passe 2 : geocodage Nominatim de {len(restantes)} adresses "
              f"(jusqu'a ~{len(restantes) * DELAI_S * 3 / 60:.0f} min)...", flush=True)
        cache = charger_cache(CACHE_PATH)
        for n, (idx, ligne) in enumerate(restantes.iterrows(), start=1):
            trouve = geocoder_ligne(ligne, cache, cache_villes)
            if trouve:
                pharmacies.loc[idx, ["latitude", "longitude", "precision_gps", "source_gps"]] = [
                    float(trouve["lat"]), float(trouve["lon"]), trouve["precision"],
                    trouve.get("source", "nominatim"),
                ]
            if n % 50 == 0:
                print(f"  {n}/{len(restantes)}", flush=True)

    pharmacies.to_csv(PHARMA_PATH, index=False, encoding="utf-8")

    avec = pharmacies["latitude"].notna().sum()
    lignes = [
        "Couverture GPS de l'annuaire des pharmacies",
        f"total : {len(pharmacies)}",
        f"avec position : {avec} ({avec / len(pharmacies) * 100:.1f} %)",
        "",
        "par source :",
        pharmacies["source_gps"].value_counts(dropna=False).to_string(),
        "",
        "par precision :",
        pharmacies["precision_gps"].value_counts(dropna=False).to_string(),
        "",
        "Seule la precision 'exacte' designe l'officine elle-meme ; 'rue', "
        "'quartier' et 'ville' situent le secteur et ne doivent pas etre "
        "affichees comme l'adresse de la pharmacie.",
        "",
        "Sources : OpenStreetMap et Nominatim (c) contributeurs OpenStreetMap, licence ODbL.",
    ]
    RAPPORT_PATH.write_text("\n".join(lignes), encoding="utf-8")
    print("\n".join(lignes[:8]))
    print(f"\n-> {PHARMA_PATH}\n-> {RAPPORT_PATH}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(osm_seulement="--osm-seulement" in sys.argv)
