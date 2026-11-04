"""Research helper: find places in the web build (site/delaware.json) by name words, with town, address and whether an official record matched.
Usage: ../.venv/bin/python lookup.py "loui's pizza" "buddy's pizza" ..."""
import json, sys, re, os
d = json.load(open(os.path.join(os.path.dirname(__file__), "..", "site", "delaware.json")))
C, m = d["cols"], d["meta"]
norm = lambda s: re.sub(r"[^a-z0-9 ]", "", (s or "").lower().replace("'", "").replace("’", ""))
for q in sys.argv[1:]:
    words = norm(q).split()
    hits = [i for i, n in enumerate(C["name"]) if all(w in norm(n).split() or any(t.startswith(w) for t in norm(n).split()) for w in words)]
    print(f"== {q}: {len(hits)}")
    for i in hits[:12]:
        city = m["cities"][C["city"][i]] if C["city"][i] is not None else None
        print(f"   {C['name'][i]} | {C['addr'][i]} | {city} | tier={['listing','both','official'][C['tier'][i]]} | jur={C['jur'][i]} | src={m['srcs'][C['src'][i]]}")
