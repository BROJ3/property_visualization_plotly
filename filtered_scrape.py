#!/usr/bin/env python3
"""
bruteforce_potsdam_parcels.py

Brute-force every parcel ID for a set of SWIS codes,
scrape the five target tables, and write results to CSV.
"""

import requests
from bs4 import BeautifulSoup
import csv
import time

# ─── CONFIG ─────────────────────────────────────────────────────────────────────

BASE_URL       = 'https://townofpotsdam.prosgar.com'
SWIS_CODES     = ['407401', '407403', '407489']
MIN_PARCEL_ID = 10000
MAX_PARCEL_ID  = 100000       # adjust lower if you want fewer requests
CONSECUTIVE_404_LIMIT = 100   # stop after this many 404s in a row per SWIS
DELAY_SECONDS  = 0.05         # pause between requests
OUTPUT_CSV     = 'potsdam_bruteforce.csv'
USER_AGENT     = 'Mozilla/5.0 (compatible; bruteforce-scraper/1.0)'

session = requests.Session()
session.headers.update({'User-Agent': USER_AGENT})


#Parsing
def parse_parcel_page(html):
    """Given a valid parcel HTML, extract the five target tables into a dict."""
    soup = BeautifulSoup(html, 'html.parser')
    data = {}

    #Header: address / SBL / SWIS
    h2 = soup.find('h2')
    if h2:
        parts = [p.strip() for p in h2.get_text(strip=True).split('–')]
        if len(parts) == 4:
            data['address'] = parts[1]
            data['sbl']     = parts[2]
            data['swis_hdr'] = parts[3].split(':',1)[1].strip()

    # 2) The five tables we want
    special_ids = [
        'residential_building_hdr',
        'assessment_hdr',
        'property_description_hdr',
        'owner_information_hdr',
        'sales_hdr'
    ]
    for sid in special_ids:
        # find <table id="sid"> or <div id="sid">→<table>
        tbl = soup.find('table', id=sid)
        if tbl is None:
            wrapper = soup.find('div', id=sid)
            if wrapper:
                tbl = wrapper.find('table')
        if not tbl:
            continue

        # pull label/value pairs
        for tr in tbl.find_all('tr'):
            cells = tr.find_all(['th','td'])
            if len(cells) == 2:
                label = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                data[f"{sid}.{label}"] = value

    return data


# ─── MAIN LOOP ──────────────────────────────────────────────────────────────────

def main():
    rows = []
    for swis in SWIS_CODES:
        print(f"\n=== SWIS {swis} ===")
        consecutive_404 = 0

        for pid in range(MIN_PARCEL_ID, MAX_PARCEL_ID + 1):
            url = f"{BASE_URL}/PROSParcel/Parcel/{pid}?swis={swis}"
            resp = session.get(url)

            if resp.status_code == 200:
                consecutive_404 = 0
                # skip pages that don’t have our target tables
                if 'id="sales_hdr"' not in resp.text:
                    # unlikely to have any of the 5 tables
                    time.sleep(DELAY_SECONDS)
                    continue

                record = parse_parcel_page(resp.text)
                record['parcel_id'] = pid
                record['swis']      = swis
                rows.append(record)
                print(f"  ✔ Found parcel {pid} (parsed)")
            elif resp.status_code == 404:
                consecutive_404 += 1
                # if we've seen many in a row, give up on this SWIS
                if consecutive_404 >= CONSECUTIVE_404_LIMIT:
                    print(f"  … {consecutive_404} consecutive 404s, moving to next SWIS.")
                    break
            else:
                print(f"  ⚠️ Unexpected {resp.status_code} for {url}")

            time.sleep(DELAY_SECONDS)

    # ─── WRITE CSV ────────────────────────────────────────────────────────────────

    if not rows:
        print("No parcel data was found.")
        return

    # figure out all columns
    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())
    fieldnames = sorted(all_keys)

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"\n✅ Done! Wrote {len(rows)} parcels to {OUTPUT_CSV}")


if __name__ == '__main__':
    main()
