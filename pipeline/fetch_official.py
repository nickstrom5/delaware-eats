"""Official Delaware records -> data/raw/official/ (git-ignored), dated by fetch day so each fetch is a snapshot (DPH's window rolls:
inspections older than two years drop out of the feed). data.delaware.gov was robots-checked first (check_sources.py).

- DPH Office of Food Protection "Food Establishment Inspection Violations" (384s-wygj, Public Domain, weekly): every row, via SODA.
- Division of Revenue "Delaware Business Licenses" (5zy2-grhr, Public Domain, daily): the RETAILER  RESTAURANT business activity.
"""
import json, os, sys, time
import requests

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "official")
UA = {"User-Agent": "DelawareEats/1.0 (+nick@eatsranked.com)"}
API = "https://data.delaware.gov/resource"
os.makedirs(OUT, exist_ok=True)
DAY = time.strftime("%Y-%m-%d")


def _all(ds, where=None):
    rows, off = [], 0
    while True:
        p = {"$limit": 50000, "$offset": off, "$order": ":id"}
        if where:
            p["$where"] = where
        r = requests.get(f"{API}/{ds}.json", params=p, headers=UA, timeout=300)
        r.raise_for_status()
        got = r.json()
        rows += got
        if len(got) < 50000:
            return rows
        off += len(got)
        time.sleep(1)


def dph():
    rows = _all("384s-wygj")
    meta = requests.get("https://data.delaware.gov/api/views/384s-wygj.json", headers=UA, timeout=60).json()
    json.dump(rows, open(f"{OUT}/dph_inspections_{DAY}.json", "w"))
    json.dump({"rowsUpdatedAt": meta.get("rowsUpdatedAt"), "fetched": DAY, "rows": len(rows)}, open(f"{OUT}/dph_meta_{DAY}.json", "w"))
    print("dph rows", len(rows))


def revenue():
    rows = _all("5zy2-grhr", "category like '%RESTAURANT%'")
    json.dump(rows, open(f"{OUT}/revenue_restaurant_{DAY}.json", "w"))
    print("revenue restaurant licenses", len(rows))


if __name__ == "__main__":
    for w in sys.argv[1:] or ["dph", "revenue"]:
        globals()[w]()
