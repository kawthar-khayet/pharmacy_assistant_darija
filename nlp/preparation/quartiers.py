"""Prepare data/clean/quartiers.csv : les quartiers de chaque ville du Maroc,
depuis OpenStreetMap.

A lancer une fois (puis seulement pour rafraichir la liste), depuis la racine :
    py -m nlp.preparation.quartiers

Pour chaque commune du Maroc, OSM renvoie les quartiers (suburb, quarter,
neighbourhood) situes A L'INTERIEUR de ses limites : c'est OSM qui dit qu'un
quartier appartient a une ville, sans calcul de distance. Un meme nom de
quartier peut exister dans plusieurs villes : le rapport les liste, et le bot
demandera alors au patient de quelle ville il parle.
Donnees OpenStreetMap, licence ODbL : attribution requise.
"""
import csv
import re
import sys
import time
from collections import defaultdict

import requests

from nlp.config import DATA_CLEAN

SORTIE = DATA_CLEAN / "quartiers.csv"
RAPPORT = DATA_CLEAN / "quartiers_report.txt"

SERVEUR = "https://overpass-api.de/api/interpreter"
MIROIR = "https://overpass.kumi.systems/api/interpreter"   # dernier recours : copie parfois ancienne
# Niveau administratif des communes marocaines dans OSM (Rabat, Temara, Sale...).
NIVEAU_VILLE = "8"
# Tout le Maroc d'un coup est trop lourd pour les serveurs gratuits : on
# decoupe par region (codes officiels MA-01 a MA-12, provinces du Sud comprises).
REQUETE_REGIONS = """[out:json][timeout:120];
rel["boundary"="administrative"]["admin_level"="4"]["ISO3166-2"~"^MA-"];
out tags;"""
# Les quartiers situes A L'INTERIEUR de chaque commune d'une region.
REQUETE_REGION = """[out:json][timeout:600];
area({zone_id})->.region;
rel(area.region)["boundary"="administrative"]["admin_level"="{niveau}"]->.villes;
foreach.villes->.ville(
  .ville out tags;
  .ville map_to_area->.zone;
  nwr["place"~"^(suburb|quarter|neighbourhood)$"](area.zone);
  out center tags;
);"""
PAUSE_ENTRE_REGIONS = 5   # secondes, pour ne pas saturer le serveur
ENTETES = {"User-Agent": "DwaTalk/1.0 (assistant pharmacie, projet etudiant)"}
AGE_MAX_JOURS = 30

_ARABE = re.compile(r"[؀-ۿ]")
_TIFINAGH = re.compile(r"[ⴰ-⵿]+")
CLES_NOMS = ("name:fr", "name", "name:en", "name:ar", "alt_name", "alt_name:fr",
             "alt_name:ar", "old_name", "official_name")


def _interroger(url: str, requete: str) -> dict | None:
    try:
        r = requests.post(url, data={"data": requete}, headers=ENTETES, timeout=700)
        # un serveur sature repond parfois 200 avec une page HTML d'erreur
        return r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"    {url} indisponible ({e.__class__.__name__})")
        return None


def telecharger(requete: str) -> dict | None:
    """Reponse Overpass, ou None. Le serveur principal est reessaye avant de
    passer au miroir, dont la copie d'OSM peut dater de plusieurs mois."""
    for tentative in range(3):
        reponse = _interroger(SERVEUR, requete)
        if reponse:
            return reponse
        if tentative < 2:
            attente = 30 * (tentative + 1)
            print(f"    nouvel essai dans {attente} s")
            time.sleep(attente)
    print("    serveur principal indisponible : essai sur le miroir")
    return _interroger(MIROIR, requete)


def separer_noms(tags: dict) -> tuple[str | None, str | None, list[str]]:
    """(nom latin, nom arabe, autres noms) a partir des etiquettes OSM.

    "Riad ⵔⵉⵢⴰⴷ الرياض" -> "Riad", "الرياض" : le tifinagh est retire, et un nom
    qui melange les ecritures est coupe en partie latine et partie arabe.
    """
    latins, arabes = [], []
    for cle in CLES_NOMS:
        valeur = tags.get(cle)
        if not valeur:
            continue
        for morceau in re.split(r"[;/|]", _TIFINAGH.sub(" ", valeur)):
            mots = morceau.split()
            arabe = " ".join(m for m in mots if _ARABE.search(m)).strip(" -,")
            latin = " ".join(m for m in mots if not _ARABE.search(m)).strip(" -,")
            if latin and latin not in latins:
                latins.append(latin)
            if arabe and arabe not in arabes:
                arabes.append(arabe)
    nom = latins[0] if latins else None
    nom_ar = arabes[0] if arabes else None
    return nom, nom_ar, latins[1:] + arabes[1:]


def _est_ville(element: dict) -> bool:
    tags = element.get("tags", {})
    return (element["type"] == "relation" and tags.get("boundary") == "administrative"
            and tags.get("admin_level") == NIVEAU_VILLE)


def main() -> None:
    print("Liste des regions du Maroc...")
    reponse = telecharger(REQUETE_REGIONS)
    if not reponse:
        sys.exit("Overpass ne repond pas. Reessaie dans quelques minutes.")
    date_osm = reponse.get("osm3s", {}).get("timestamp_osm_base", "inconnue")
    regions = sorted(
        ((e["tags"].get("ISO3166-2"), separer_noms(e["tags"])[0] or "?", e["id"])
         for e in reponse["elements"]),
    )
    print(f"  {len(regions)} regions (donnees OSM du {date_osm})")

    elements: list[dict] = []
    regions_ratees: list[str] = []
    for code, nom_region, rel_id in regions:
        print(f"  {code} {nom_region}...")
        # l'identifiant d'une zone Overpass = 3 600 000 000 + celui de la relation
        requete = REQUETE_REGION.format(zone_id=3600000000 + rel_id, niveau=NIVEAU_VILLE)
        reponse_region = telecharger(requete)
        if reponse_region is None:
            regions_ratees.append(f"{code} {nom_region}")
            print("    ECHEC : region ignoree, relancer le script plus tard")
        else:
            elements += reponse_region["elements"]
            print(f"    {len(reponse_region['elements'])} elements")
        time.sleep(PAUSE_ENTRE_REGIONS)

    quartiers: list[dict] = []
    deja_vus: set[str] = set()
    sans_nom = 0
    ville, ville_ar = None, None
    # La reponse alterne : une ville, puis les quartiers qui sont dans ses limites.
    for e in elements:
        if _est_ville(e):
            ville, ville_ar, _ = separer_noms(e.get("tags", {}))
            continue
        osm_id = f"{e['type']}/{e['id']}"
        if osm_id in deja_vus:        # quartier a cheval sur deux communes : on le garde une fois
            continue
        deja_vus.add(osm_id)
        nom, nom_ar, autres = separer_noms(e.get("tags", {}))
        if not nom and not nom_ar:
            sans_nom += 1
            continue
        quartiers.append({
            "nom": nom or "",
            "nom_ar": nom_ar or "",
            "autres_noms": " | ".join(autres),
            "type": e.get("tags", {}).get("place"),
            "ville": ville or "",
            "ville_ar": ville_ar or "",
            "latitude": round(e.get("lat", e.get("center", {}).get("lat")), 7),
            "longitude": round(e.get("lon", e.get("center", {}).get("lon")), 7),
            "osm_id": osm_id,
        })

    colonnes = ["nom", "nom_ar", "autres_noms", "type", "ville", "ville_ar",
                "latitude", "longitude", "osm_id"]
    quartiers.sort(key=lambda q: (q["ville"], q["nom"] or q["nom_ar"]))
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=colonnes)
        ecrivain.writeheader()
        ecrivain.writerows(quartiers)

    # Meme nom de quartier dans plusieurs villes : le bot devra demander laquelle.
    villes_par_nom = defaultdict(set)
    for q in quartiers:
        villes_par_nom[(q["nom"] or q["nom_ar"]).lower()].add(q["ville"])
    homonymes = sorted((n, sorted(v)) for n, v in villes_par_nom.items() if len(v) > 1)

    par_ville = defaultdict(int)
    for q in quartiers:
        par_ville[q["ville"]] += 1

    try:
        age = (time.time() - time.mktime(time.strptime(date_osm[:10], "%Y-%m-%d"))) / 86400
        alerte_age = [f"ATTENTION : donnees vieilles de {age:.0f} jours (miroir ?)"] if age > AGE_MAX_JOURS else []
    except ValueError:
        alerte_age = []

    lignes = [
        "Quartiers du Maroc par ville -- source OpenStreetMap (ODbL)",
        f"Genere le {time.strftime('%Y-%m-%d %H:%M')} ; donnees OSM du {date_osm}",
        *alerte_age,
        f"Regions traitees : {len(regions) - len(regions_ratees)} sur {len(regions)}",
        *[f"ATTENTION : region manquante, relancer le script : {r}" for r in regions_ratees],
        "",
        f"Quartiers gardes : {len(quartiers)}  (sans nom, ecartes : {sans_nom})",
        f"  sans nom latin : {sum(1 for q in quartiers if not q['nom'])}",
        f"  sans nom arabe : {sum(1 for q in quartiers if not q['nom_ar'])}",
        f"Villes ayant au moins un quartier : {len(par_ville)}",
        "",
        f"Noms de quartier presents dans plusieurs villes ({len(homonymes)}) :",
        *[f"  {nom} : {', '.join(villes)}" for nom, villes in homonymes],
        "",
        "Par ville :",
        *[f"  {v} : {n}" for v, n in sorted(par_ville.items(), key=lambda x: -x[1])],
    ]
    RAPPORT.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"{len(quartiers)} quartiers ecrits dans {SORTIE}")
    print(f"Rapport : {RAPPORT}")


if __name__ == "__main__":
    main()
