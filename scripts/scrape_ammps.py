"""Scrape the AMMPS "Liste Marocaine des Medicaments" public database.

Source: https://www.ammps.gov.ma/basesdedonnes/liste_marocaine_des_medicaments
Public open data, robots.txt allows crawling of this path. Polite delay between requests.
"""
import csv
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ammps.gov.ma/basesdedonnes/liste_marocaine_des_medicaments"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_FILE = OUT_DIR / "ammps_medicaments.csv"
STATE_FILE = OUT_DIR / "ammps_scrape_state.txt"

FIELDS = [
    "nom", "dosage", "forme", "substance_active", "classe_therapeutique",
    "epi_laboratoire", "statut_commercialisation", "statut_amm",
    "presentation", "pp_gn", "ppv", "ph", "pfht", "tva", "lien_rcp_naf",
    "source_page",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DataCleaningResearch/1.0 (contact: ferdaouselhadfi07@gmail.com)"
}


def get_total_pages(session: requests.Session) -> int:
    r = session.get(BASE_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    max_page = 1
    for a in soup.select("ul.pagination a.page-link"):
        href = a.get("href", "")
        m = re.search(r"page=(\d+)", href)
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page, r.text


def parse_page(html: str, page_num: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="medicamentsTable")
    if not table:
        return []
    tbody = table.find("tbody")
    if not tbody:
        return []

    records = []
    for tr in tbody.find_all("tr", recursive=False):
        btn = tr.find("button", attrs={"data-bs-target": True})
        modal_id = btn["data-bs-target"].lstrip("#") if btn else None
        modal = soup.find("div", id=modal_id) if modal_id else None

        rec = {f: "" for f in FIELDS}
        rec["source_page"] = page_num

        if modal:
            title = modal.find("h5", class_="modal-title")
            rec["nom"] = title.get_text(strip=True) if title else ""
            subtitle = modal.find("div", class_="ammps-modal-subtitle")
            if subtitle:
                parts = [p.strip() for p in subtitle.get_text(strip=True).split("|")]
                rec["dosage"] = parts[0] if len(parts) > 0 else ""
                rec["forme"] = parts[1] if len(parts) > 1 else ""

            label_map = {
                "Statut AMM": "statut_amm",
                "Statut commercialisation": "statut_commercialisation",
                "Présentation": "presentation",
                "PP / GN": "pp_gn",
                "Substance active": "substance_active",
                "Classe thérapeutique": "classe_therapeutique",
                "EPI": "epi_laboratoire",
                "PPV": "ppv",
                "PH": "ph",
                "PFHT": "pfht",
                "TVA": "tva",
                "Lien RCP / NAF": "lien_rcp_naf",
            }
            for item in modal.find_all("div", class_="ammps-modal-item"):
                label_el = item.find("span", class_="ammps-modal-label")
                value_el = item.find("span", class_="ammps-modal-value")
                if not label_el or not value_el:
                    continue
                label = label_el.get_text(strip=True)
                value = value_el.get_text(strip=True)
                key = label_map.get(label)
                if key:
                    rec[key] = value
        else:
            # fallback to plain table cells if modal missing
            tds = tr.find_all("td")
            cell_names = ["nom", "dosage", "forme", "substance_active", "classe_therapeutique", "epi_laboratoire"]
            for name, td in zip(cell_names, tds):
                rec[name] = td.get_text(strip=True)

        if rec["nom"]:
            records.append(rec)
    return records


def load_done_pages() -> set[int]:
    if STATE_FILE.exists():
        return {int(x) for x in STATE_FILE.read_text().split() if x.strip()}
    return set()


def mark_page_done(page: int):
    with open(STATE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{page}\n")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    print("Fetching page 1 to determine total pages...", flush=True)
    total_pages, first_html = get_total_pages(session)
    print(f"Total pages detected: {total_pages}", flush=True)

    done_pages = load_done_pages()
    write_header = not OUT_FILE.exists()

    with open(OUT_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()

        for page in range(1, total_pages + 1):
            if page in done_pages:
                continue
            if page == 1:
                html = first_html
            else:
                for attempt in range(3):
                    try:
                        r = session.get(BASE_URL, params={"page": page}, headers=HEADERS, timeout=30)
                        r.raise_for_status()
                        html = r.text
                        break
                    except requests.RequestException as e:
                        print(f"  page {page} attempt {attempt+1} failed: {e}", flush=True)
                        time.sleep(2 * (attempt + 1))
                else:
                    print(f"  page {page} FAILED after retries, skipping", flush=True)
                    continue

            records = parse_page(html, page)
            for rec in records:
                writer.writerow(rec)
            f.flush()
            mark_page_done(page)

            if page % 25 == 0 or page == total_pages:
                print(f"  scraped page {page}/{total_pages} (+{len(records)} rows)", flush=True)

            time.sleep(0.3)

    print("Done.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
