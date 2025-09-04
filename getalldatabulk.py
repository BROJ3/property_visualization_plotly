import requests
from bs4 import BeautifulSoup
import csv

BASE_URL      = "https://townofpotsdam.prosgar.com"
SEARCH_PAGE   = BASE_URL + "/PROSSearch/SearchIndex?FilterWaterfronts=False"
API_ENDPOINT  = BASE_URL + "/PROSSearch/GetAjax"

# 1) grab the anti-forgery token and cookies
session = requests.Session()
resp = session.get(SEARCH_PAGE)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")
token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]

# 2) page through all results
start  = 0
length = 100   # you can bump this up if the server allows
all_data = []

while True:
    payload = {
        "__RequestVerificationToken": token,
        "start":  start,
        "length": length,
        # if you want to apply any search/filter, add e.g.
        # "search[value]": "",
        # "address":    "",
        # "owner":      "",
        # …etc…
    }

    r = session.post(API_ENDPOINT, data=payload)
    r.raise_for_status()
    js = r.json()

    rows = js.get("data", [])
    if not rows:
        break

    all_data.extend(rows)
    print(f"Fetched {len(rows)} rows (start={start})")
    start += length

# 3) write out to CSV (assumes each row is a dict; if it’s a list, tweak accordingly)
if all_data:
    with open("parcels.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
        writer.writeheader()
        writer.writerows(all_data)

    print(f"Done! Wrote {len(all_data)} rows to parcels.csv")
else:
    print("No data pulled.")
