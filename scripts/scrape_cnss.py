"""Scrape the CNSS "Liste des medicaments admis au remboursement".

Source: https://www.cnss.ma/fr/professionnel-de-sante/demarches-et-procedures/liste-des-medicaments-remboursables
Public, unauthenticated JSON API backing that page (found by inspecting the page's
network calls): POST https://www.cnss.ma/api/search
Body: {"module": "medicaments", "group": "medicaments_default", "langcode": "fr",
       "query_params": {"page": N, "limit": L}}
No auth/cookies required. Polite delay between requests.
"""
import csv
import sys
import time
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://www.cnss.ma/api/search"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_FILE = OUT_DIR / "cnss_medicaments.csv"

PAGE_LIMIT = 500

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DataCleaningResearch/1.0 (contact: khayetkaouthar@gmail.com)",
    "Content-Type": "application/json",
}

FIELDS = [
    "code", "laboratoire", "nom", "dci", "dosage", "unite_dosage", "forme",
    "presentation", "ppv", "ph", "ppv_br", "princeps_generique",
    "classe_therapeutique", "taux_remboursement_cnss",
]

FIELD_MAP = {
    "Code": "code",
    "Laboratoire": "laboratoire",
    "Nom": "nom",
    "DCI": "dci",
    "Dosage": "dosage",
    "Unité Dosage": "unite_dosage",
    "Forme": "forme",
    "Présentation": "presentation",
    "PPV": "ppv",
    "PH": "ph",
    "PPV - BR": "ppv_br",
    "Princeps / Générique": "princeps_generique",
    "Classe Thérapeutique": "classe_therapeutique",
    "Taux Rembours": "taux_remboursement_cnss",
}


def fetch_page(session: requests.Session, page: int) -> dict:
    payload = {
        "module": "medicaments",
        "group": "medicaments_default",
        "langcode": "fr",
        "query_params": {"page": page, "limit": PAGE_LIMIT},
    }
    for attempt in range(3):
        try:
            r = session.post(API_URL, json=payload, headers=HEADERS, timeout=30, verify=False)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  page {page} attempt {attempt + 1} failed: {e}", flush=True)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"page {page} failed after retries")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    print("Fetching page 1 to determine total pages...", flush=True)
    data = fetch_page(session, 1)
    total = data["pagination"]["total"]
    total_pages = data["pagination"]["pages"]
    print(f"Total records: {total}, pages of {PAGE_LIMIT}: {total_pages}", flush=True)

    with open(OUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        page = 1
        rows_written = 0
        while True:
            for item in data["items"]:
                rec = {FIELD_MAP[k]: v for k, v in item.items() if k in FIELD_MAP}
                writer.writerow(rec)
                rows_written += 1
            f.flush()
            print(f"  page {page}/{total_pages} (+{len(data['items'])} rows, total {rows_written})", flush=True)

            if not data["pagination"]["links"].get("next"):
                break
            page += 1
            time.sleep(0.3)
            data = fetch_page(session, page)

    print(f"Done. {rows_written} rows written to {OUT_FILE}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
