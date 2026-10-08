"""Prepare data/clean/pharmacies_fusion.csv : toutes les pharmacies du Maroc.

A lancer une fois (puis seulement pour rafraichir), depuis la racine, APRES
nlp.preparation.quartiers (on reutilise sa facon d'interroger OSM) :
    py -m nlp.preparation.pharmacies_fusion

1. OpenStreetMap, commune par commune : chaque pharmacie a sa position exacte
   et SA ville selon OSM (sans calcul de distance). Les pharmacies sans nom
   sont ecartees.
2. L'annuaire (data/clean/pharmacies_reference.csv) complete OSM : adresse,
   telephone, horaires de garde. Une pharmacie de l'annuaire absente d'OSM est
   ajoutee telle quelle.
Le rapport data/clean/pharmacies_fusion_report.txt est a relire, en
particulier les exemples de fusion.
Donnees OpenStreetMap, licence ODbL : attribution requise.
"""
import csv
import math
import random
import re
import sys
import time
import unicodedata
from collections import Counter

import pandas as pd
from rapidfuzz import fuzz

from nlp.config import DATA_CLEAN
from nlp.linking.translitteration import contient_arabe, translitterer
from nlp.preparation.quartiers import (
    NIVEAU_VILLE, PAUSE_ENTRE_REGIONS, REQUETE_REGIONS, separer_noms, telecharger,
)

ANNUAIRE = DATA_CLEAN / "pharmacies_reference.csv"
SORTIE = DATA_CLEAN / "pharmacies_fusion.csv"
RAPPORT = DATA_CLEAN / "pharmacies_fusion_report.txt"

# Les pharmacies situees A L'INTERIEUR de chaque commune d'une region.
REQUETE_REGION = """[out:json][timeout:600];
area({zone_id})->.region;
rel(area.region)["boundary"="administrative"]["admin_level"="{niveau}"]->.villes;
foreach.villes->.ville(
  .ville out tags;
  .ville map_to_area->.zone;
  nwr["amenity"="pharmacy"](area.zone);
  out center tags;
);"""

# Fusion d'une pharmacie de l'annuaire avec une pharmacie OSM :
DISTANCE_FUSION_M = 300      # position precise : a moins de 300 m...
SCORE_NOM_PROCHE = 80        # ...avec un nom ressemblant
SCORE_NOM_SEUL = 90          # position imprecise : meme ville, nom tres ressemblant, candidat unique
PRECISIONS_FIABLES = {"exacte", "rue", "quartier"}

# --- Normalisation des noms, copiee de l'ancien nlp/linking/pharmacies.py ---
# Gardee ici telle quelle pour que relancer le script redonne exactement la
# meme fusion. Le bot, lui, utilise nlp/linking/lieux.py et pharmacies.py.

# "Pharmacie", "la grande pharmacie de"... : en tete de presque tous les noms,
# ne distingue rien.
NAME_PREFIXES = re.compile(
    r"^(LA |GRANDE |NOUVELLE )*(PHARMACIE|SIDLIA|SAIDALIA)\s+(DE\s+|DU\s+|DES\s+|D')?",
    re.IGNORECASE,
)

# Villes ecrites en arabe -> graphie de l'annuaire. Un toponyme se traduit,
# il ne se translittere pas ("الدار البيضاء" n'a aucune lettre de "Casablanca").
ALIAS_VILLES = {
    "الدار البيضاء": "Casablanca", "دار البيضاء": "Casablanca", "كازا": "Casablanca",
    "كازابلانكا": "Casablanca", "casa": "Casablanca", "dar el beida": "Casablanca",
    "الرباط": "Rabat", "سلا": "Salé", "تمارة": "Témara",
    "مراكش": "Marrakech", "فاس": "Fès", "مكناس": "Meknès",
    "طنجة": "Tanger", "تطوان": "Tétouan", "أكادير": "Agadir", "اكادير": "Agadir",
    "وجدة": "Oujda", "القنيطرة": "Kénitra", "الجديدة": "El Jadida",
    "آسفي": "Safi", "اسفي": "Safi", "الصويرة": "Essaouira",
    "بني ملال": "Beni Mellal", "خريبكة": "Khouribga", "برشيد": "Berrechid",
    "سطات": "Settat", "الناظور": "Nador", "الحسيمة": "Al Hoceima",
    "ورزازات": "Ouarzazate", "العيون": "Laâyoune", "الداخلة": "Dakhla",
    "تازة": "Taza", "المحمدية": "Mohammedia", "الرشيدية": "Errachidia",
    "كلميم": "Guelmim", "تارودانت": "Taroudant", "انزكان": "Inezgane",
    "العرائش": "Larache", "خنيفرة": "Khénifra", "بركان": "Berkane",
    "صفرو": "Séfrou", "القصر الكبير": "Ksar El Kebir",
}

_DIACRITIQUES_AR = re.compile(r"[ً-ْٰـ]")


def latiniser(texte: str) -> str:
    """Une saisie en arabe vers le latin de la base : alias de ville d'abord,
    sinon translitteration lettre a lettre."""
    brut = _DIACRITIQUES_AR.sub("", str(texte)).strip()
    alias = ALIAS_VILLES.get(brut) or ALIAS_VILLES.get(brut.lower())
    if alias:
        return alias
    return translitterer(brut) if contient_arabe(brut) else brut


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalize(s) -> str:
    if pd.isna(s):
        return ""
    s = latiniser(s).strip().upper()
    s = strip_accents(s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_pharmacie_prefix(name_norm: str) -> str:
    return NAME_PREFIXES.sub("", name_norm).strip()


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance a vol d'oiseau en metres (formule de haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(a))


def nom_court(nom: str) -> str:
    """"Pharmacie Ibn Sina" -> "IBN SINA" : le mot "pharmacie" ne distingue rien."""
    return strip_pharmacie_prefix(normalize(nom or ""))


def ressemblance(a: str, b: str) -> float:
    return fuzz.token_sort_ratio(nom_court(a), nom_court(b))


def _texte(x) -> str:
    return "" if pd.isna(x) else str(x).strip()


def pharmacies_osm() -> tuple[list[dict], str, list[str], int]:
    """(pharmacies OSM avec leur ville, date des donnees, regions ratees, sans nom)."""
    print("Liste des regions du Maroc...")
    reponse = telecharger(REQUETE_REGIONS)
    if not reponse:
        sys.exit("Overpass ne repond pas. Reessaie dans quelques minutes.")
    date_osm = reponse.get("osm3s", {}).get("timestamp_osm_base", "inconnue")
    regions = sorted((e["tags"].get("ISO3166-2"), separer_noms(e["tags"])[0] or "?", e["id"])
                     for e in reponse["elements"])

    pharmacies, ratees, deja_vues, sans_nom = [], [], set(), 0
    for code, nom_region, rel_id in regions:
        print(f"  {code} {nom_region}...")
        requete = REQUETE_REGION.format(zone_id=3600000000 + rel_id, niveau=NIVEAU_VILLE)
        rep = telecharger(requete)
        if rep is None:
            ratees.append(f"{code} {nom_region}")
            print("    ECHEC : region ignoree, relancer le script plus tard")
            time.sleep(PAUSE_ENTRE_REGIONS)
            continue
        ville, ville_ar = "", ""
        # La reponse alterne : une ville, puis les pharmacies qui sont dans ses limites.
        for e in rep["elements"]:
            tags = e.get("tags", {})
            if e["type"] == "relation" and tags.get("admin_level") == NIVEAU_VILLE:
                ville, ville_ar, _ = separer_noms(tags)
                continue
            osm_id = f"{e['type']}/{e['id']}"
            if osm_id in deja_vues:
                continue
            deja_vues.add(osm_id)
            nom, nom_ar, _ = separer_noms(tags)
            if not nom and not nom_ar:
                sans_nom += 1
                continue
            rue = " ".join(filter(None, (tags.get("addr:housenumber"), tags.get("addr:street"))))
            pharmacies.append({
                "nom": nom or nom_ar,
                "nom_ar": nom_ar or "",
                "adresse": rue,
                "telephone": tags.get("phone") or tags.get("contact:phone") or "",
                "horaires": tags.get("opening_hours") or "",
                "ville": ville or "",
                "ville_ar": ville_ar or "",
                "latitude": round(e.get("lat", e.get("center", {}).get("lat")), 7),
                "longitude": round(e.get("lon", e.get("center", {}).get("lon")), 7),
                "precision_gps": "exacte",
                "source": "osm",
                "osm_id": osm_id,
            })
        print(f"    {len(pharmacies)} pharmacies au total")
        time.sleep(PAUSE_ENTRE_REGIONS)
    return pharmacies, date_osm, ratees, sans_nom


def fusionner(osm: list[dict], annuaire: pd.DataFrame) -> tuple[list[dict], Counter, list[str]]:
    """Complete OSM avec l'annuaire ; ajoute les pharmacies de l'annuaire absentes d'OSM."""
    utilisees: set[int] = set()
    compte = Counter()
    exemples = []
    ajoutees = []
    par_ville: dict[str, list[int]] = {}
    for i, o in enumerate(osm):
        par_ville.setdefault(normalize(o["ville"]), []).append(i)

    for a in annuaire.to_dict("records"):
        precise = a.get("precision_gps") in PRECISIONS_FIABLES and pd.notna(a.get("latitude"))
        choisi, detail = None, ""
        if precise:
            proches = []
            for i, o in enumerate(osm):
                # tri grossier avant le calcul exact : ~0.005 degre = ~500 m
                if i in utilisees or abs(o["latitude"] - a["latitude"]) > 0.005 \
                        or abs(o["longitude"] - a["longitude"]) > 0.005:
                    continue
                d = distance_m(a["latitude"], a["longitude"], o["latitude"], o["longitude"])
                score = ressemblance(a["nom"], o["nom"])
                if d <= DISTANCE_FUSION_M and score >= SCORE_NOM_PROCHE:
                    proches.append((score, -d, i, d))
            if proches:
                _, _, choisi, d = max(proches)
                compte["fusion par position et nom"] += 1
                detail = f"{d:.0f} m"
        else:
            candidats = [
                i for i in par_ville.get(normalize(_texte(a.get("ville"))), [])
                if i not in utilisees and ressemblance(a["nom"], osm[i]["nom"]) >= SCORE_NOM_SEUL
            ]
            if len(candidats) == 1:     # en cas de doute (plusieurs candidats), on ne fusionne pas
                choisi = candidats[0]
                compte["fusion par nom et ville"] += 1
                detail = "meme ville"

        if choisi is not None:
            utilisees.add(choisi)
            o = osm[choisi]
            o["adresse"] = _texte(a.get("adresse")) or o["adresse"]
            o["telephone"] = o["telephone"] or _texte(a.get("telephone"))
            # l'annuaire est plus fiable pour la garde (24h/24, nuit...)
            o["horaires"] = _texte(a.get("garde")) or o["horaires"]
            o["source"] = "osm+annuaire"
            exemples.append(f"  {a['nom']}  <->  {o['nom']}  ({o['ville']}, {detail})")
            continue

        compte["annuaire seul, ajoutee" + ("" if precise else " (position imprecise)")] += 1
        ajoutees.append({
            "nom": a["nom"],
            "nom_ar": "",
            "adresse": _texte(a.get("adresse")),
            "telephone": _texte(a.get("telephone")),
            "horaires": _texte(a.get("garde")),
            "ville": _texte(a.get("ville")),
            "ville_ar": "",
            "latitude": a["latitude"] if pd.notna(a.get("latitude")) else "",
            "longitude": a["longitude"] if pd.notna(a.get("longitude")) else "",
            "precision_gps": _texte(a.get("precision_gps")) or "inconnue",
            "source": "annuaire",
            "osm_id": "",
        })
    return osm + ajoutees, compte, exemples


def main() -> None:
    osm, date_osm, ratees, sans_nom = pharmacies_osm()
    annuaire = pd.read_csv(ANNUAIRE, dtype={"telephone": str})
    annuaire = annuaire[annuaire["type_etablissement"] == "pharmacie"]
    print(f"Fusion avec l'annuaire ({len(annuaire)} pharmacies)...")
    toutes, compte, exemples = fusionner(osm, annuaire)

    colonnes = ["id", "nom", "nom_ar", "adresse", "telephone", "horaires", "ville", "ville_ar",
                "latitude", "longitude", "precision_gps", "source", "osm_id"]
    toutes.sort(key=lambda p: (p["ville"], p["nom"]))
    for n, p in enumerate(toutes, 1):
        p["id"] = n
    with SORTIE.open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=colonnes)
        ecrivain.writeheader()
        ecrivain.writerows(toutes)

    random.seed(0)   # memes exemples a chaque lancement, pour pouvoir comparer
    lignes = [
        "Pharmacies du Maroc -- OpenStreetMap (ODbL) + annuaire",
        f"Genere le {time.strftime('%Y-%m-%d %H:%M')} ; donnees OSM du {date_osm}",
        *[f"ATTENTION : region manquante, relancer le script : {r}" for r in ratees],
        "",
        f"OSM : {len(osm)} pharmacies gardees ({sans_nom} sans nom ecartees)",
        f"Annuaire : {len(annuaire)} pharmacies",
        *[f"  {k} : {v}" for k, v in compte.most_common()],
        f"TOTAL : {len(toutes)} pharmacies",
        "",
        "Par source : " + ", ".join(f"{s} {n}" for s, n in Counter(p["source"] for p in toutes).most_common()),
        f"Avec adresse : {sum(1 for p in toutes if p['adresse'])}",
        f"Avec telephone : {sum(1 for p in toutes if p['telephone'])}",
        f"Avec horaires : {sum(1 for p in toutes if p['horaires'])}",
        "",
        "30 exemples de fusion, a verifier :",
        *random.sample(exemples, min(30, len(exemples))),
        "",
        "Par ville (30 premieres) :",
        *[f"  {v or '(sans ville)'} : {n}"
          for v, n in Counter(p["ville"] for p in toutes).most_common(30)],
    ]
    RAPPORT.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"{len(toutes)} pharmacies ecrites dans {SORTIE}")
    print(f"Rapport : {RAPPORT}")


if __name__ == "__main__":
    main()
