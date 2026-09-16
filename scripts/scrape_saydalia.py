"""Scrape the pharmacy directory used by Saydalia's own map widget
(saydalia.ma) to build a pharmacies database for the assistant's
info_pharmacie intent (address, phone, city, on-duty status).

This is NOT a documented public API: it's the internal endpoint
(`/api/siteweb_api.php`) that saydalia.ma's own "find a pharmacy" map
widget calls client-side, discovered by reading their public JS
(wp-content/plugins/nearest-saydalia/js/nearest-saydalia.js). The API
key used here is the one already exposed in that public page source
for their own widget -- nothing here bypasses authentication.

Each call returns (at most) the 40 nearest entries to a given lat/lng,
regardless of the requested `limit` -- so full coverage requires
querying many points (city centers + a few extra points inside the
largest, most sprawling cities) and de-duplicating by `id`.

Runs politely: one request every ~0.4s, ~230 requests total for the
whole grid below (~2 minutes). Not intended for repeated/frequent runs.
"""
import csv
import json
import time
from pathlib import Path

import requests

API_URL = "https://saydalia.ma/api/siteweb_api.php"
API_KEY = "808RBAI77YIO2HZQ9WYSJKHK9WDEVVXXERFB77CALCU6U0"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_FILE = OUT_DIR / "saydalia_pharmacies.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DataCleaningResearch/1.0 (contact: ferdaouselhadfi07@gmail.com)"
}

# Major city centers across Morocco, plus a few extra points spread across
# the largest/most sprawling cities (Casablanca, Rabat-Sale, Marrakech, Fes,
# Tanger, Agadir) so a single 40-nearest query per city doesn't miss
# districts far from the city center.
QUERY_POINTS = {
    # Casablanca -- multiple districts
    "Casablanca-Centre": (33.5731, -7.5898),
    "Casablanca-Maarif": (33.5731, -7.6350),
    "Casablanca-SidiBernoussi": (33.6142, -7.5133),
    "Casablanca-AinSebaa": (33.6086, -7.5389),
    "Casablanca-HayHassani": (33.5544, -7.6631),
    "Casablanca-SidiMaarouf": (33.5237, -7.6392),
    "Casablanca-AinChock": (33.5397, -7.6142),
    "Mohammedia": (33.6835, -7.3831),
    "Nouaceur": (33.3667, -7.5833),
    "Bouskoura": (33.4436, -7.6547),
    "DarBouazza": (33.5289, -7.8156),
    "Berrechid": (33.2650, -7.5878),

    # Rabat-Sale-Kenitra
    "Rabat-Centre": (34.0209, -6.8416),
    "Rabat-Agdal": (33.9944, -6.8567),
    "Sale": (34.0531, -6.7985),
    "Temara": (33.9287, -6.9066),
    "Skhirat": (33.8500, -7.0333),
    "Kenitra": (34.2610, -6.5802),
    "Khemisset": (33.8242, -6.0658),
    "SidiSlimane": (34.2654, -5.9257),
    "SidiKacem": (34.2214, -5.7100),

    # Fes-Meknes
    "Fes-Centre": (34.0331, -5.0003),
    "Fes-Est": (34.0500, -4.9700),
    "Meknes": (33.8935, -5.5473),
    "Ifrane": (33.5228, -5.1106),
    "Azrou": (33.4342, -5.2213),
    "Sefrou": (33.8305, -4.8330),
    "Taza": (34.2100, -4.0100),
    "Khenifra": (32.9394, -5.6694),

    # Marrakech-Safi
    "Marrakech-Centre": (31.6295, -7.9811),
    "Marrakech-Sud": (31.6000, -8.0100),
    "Marrakech-Nord": (31.6600, -7.9700),
    "Safi": (32.2994, -9.2372),
    "Essaouira": (31.5085, -9.7595),
    "ElJadida": (33.2316, -8.5007),
    "Azemmour": (33.2891, -8.3417),
    "SidiBennour": (32.6499, -8.4283),
    "Youssoufia": (32.2464, -8.5290),
    "FquihBenSalah": (32.5013, -6.6892),
    "BeniMellal": (32.3373, -6.3498),

    # Tanger-Tetouan-Al Hoceima
    "Tanger-Centre": (35.7595, -5.8340),
    "Tanger-Est": (35.7300, -5.7900),
    "Tetouan": (35.5785, -5.3684),
    "Martil": (35.6167, -5.2750),
    "Mdiq": (35.6845, -5.3213),
    "Larache": (35.1932, -6.1557),
    "KsarElKebir": (35.0018, -5.9042),
    "Chefchaouen": (35.1688, -5.2636),
    "AlHoceima": (35.2517, -3.9372),

    # Oriental
    "Oujda": (34.6814, -1.9086),
    "Nador": (35.1681, -2.9287),
    "Berkane": (34.9218, -2.3202),
    "Taourirt": (34.4079, -2.8988),
    "Guercif": (34.2258, -3.3536),

    # Souss-Massa / Sud
    "Agadir-Centre": (30.4278, -9.5981),
    "Agadir-Est": (30.4000, -9.5500),
    "Inezgane": (30.3550, -9.5378),
    "Taroudant": (30.4703, -8.8770),
    "Tiznit": (29.6974, -9.7316),
    "Guelmim": (28.9870, -10.0574),
    "TanTan": (28.4378, -11.1030),
    "Laayoune": (27.1418, -13.1878),
    "Dakhla": (23.6848, -15.9579),

    # Draa-Tafilalet
    "Errachidia": (31.9314, -4.4241),
    "Ouarzazate": (30.9189, -6.8934),
    "Zagora": (30.3320, -5.8382),
    "Midelt": (32.6852, -4.7371),

    # Khouribga / Settat area
    "Khouribga": (32.8811, -6.9063),
    "Settat": (33.0011, -7.6166),
}

FIELDS = ["id", "title", "phone", "address", "address_2", "ville", "garde", "query_point"]


def fetch_point(session: requests.Session, name: str, lat: float, lng: float) -> list[dict]:
    resp = session.get(
        API_URL,
        params={"origin": f"{lat},{lng}", "limit": 40, "api_key": API_KEY},
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        return []

    records = []
    for item in data:
        records.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "phone": item.get("Phone"),
            "address": item.get("address"),
            "address_2": item.get("Adresse 2"),
            "ville": item.get("Ville"),
            "garde": item.get("garde"),
            "query_point": name,
        })
    return records


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    seen_ids = {}
    total_points = len(QUERY_POINTS)

    for i, (name, (lat, lng)) in enumerate(QUERY_POINTS.items(), start=1):
        try:
            records = fetch_point(session, name, lat, lng)
        except requests.RequestException as e:
            print(f"[{i}/{total_points}] {name}: ERREUR {e}", flush=True)
            time.sleep(1)
            continue

        new_count = 0
        for rec in records:
            rid = rec["id"]
            if rid not in seen_ids:
                seen_ids[rid] = rec
                new_count += 1

        print(f"[{i}/{total_points}] {name}: {len(records)} recus, {new_count} nouveaux (total unique={len(seen_ids)})", flush=True)
        time.sleep(0.4)

    with open(OUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for rec in seen_ids.values():
            writer.writerow(rec)

    print(f"\nTermine : {len(seen_ids)} etablissements uniques -> {OUT_FILE}")


if __name__ == "__main__":
    main()
