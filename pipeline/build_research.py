"""Writes data/research/app/*.json (hand-checked Delaware guides), data/research/jbf.json and data/research/closed.json from the compact
lists below. Ported from oh-eats/pipeline/build_research.py.

Every entry needs two things, both on robots-checked hosts (check_sources.py; most Delaware papers block ClaudeBot: delawareonline.com,
delawarelive.com, townsquaredelaware.com, wdel.com, coastalpoint.com, delawaretoday.com):
- a page that names it for the guide (any date: the state or county tourism office, the Cape Gazette, the place's own site), and
- 2025-26 evidence that it operates: a dated 2025-26 page ("dated"), or a DPH inspection in 2025 or 2026 at the place ("dph"), from the
  Division of Public Health's statewide feed.
The address comes from the record we already hold for that name in that town (site/delaware.json), never from memory; a name that isn't
found once in its town is left out and listed in data/research/app/LEADS.md. A founding year is set only when a source says the place
opened at this address; a brand's founding year goes in the note.
Usage: ../.venv/bin/python build_research.py   (then delaware.py)"""
import json, os, re
ROOT = os.path.join(os.path.dirname(__file__), "..")
R = os.path.join(ROOT, "data", "research")
os.makedirs(f"{R}/app", exist_ok=True)
d = json.load(open(os.path.join(ROOT, "site", "delaware.json")))
C, M = d["cols"], d["meta"]
INSP = {sp[0]: sp for sp in d["sparse"]["insp"]}   # [row, routine count, routine date, routine n, last date, last count, last type]
norm = lambda s: re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower().replace("'", "").replace("’", ""))).strip()
DPH = "https://data.delaware.gov/Health/Food-Establishment-Inspection-Violations/384s-wygj"

FALL26 = "https://www.visitdelaware.com/blog/post/fall-foodie-road-trip/"                                   # Sep 3, 2026
DINNER23 = "https://www.visitdelaware.com/blog/post/dinner-is-served-delawares-most-unforgettable-over-the-top-dishes/"   # Mar 1, 2023
BRUNCH26 = "https://www.visitwilmingtonde.com/goodtaste/stories/post/best-brunch-spots-in-wilmington-the-brandywine-valley/"   # Jun 12, 2026
BRUNCH22 = "https://www.visitwilmingtonde.com/goodtaste/stories/post/out-and-about-magazine-the-evolution-of-brunch/"   # Feb 6, 2022
BEACH = "https://www.visitdelaware.com/beaches/dining/"                                                     # undated
WINDOWS = "https://www.capegazette.com/article/friendly-windows-offer-instant-access-yummy-beach-eats/206662"   # Aug 14, 2020
SURF25 = "https://www.capegazette.com/article/cruisin%E2%80%99-crab-set-hit-road/287820"                    # Mar 9, 2025
CRABCON = "https://www.capegazette.com/article/name-implies-crab-connect-place-crabs/245211"                 # 2022
INQ = "https://www.inquirer.com/philly-tips/wilmington-delaware-things-to-do.html"                         # 2022, updated Oct 2023
FRESH23 = "https://www.visitwilmingtonde.com/goodtaste/stories/post/freshly-picked-a-local-foodies-view-of-greater-wilmington-delawares-dining-scene/"   # Sep 5, 2023
ICE25 = "https://www.visitdelaware.com/blog/post/delicious-ice-cream-spots-in-delaware/"                    # Jun 19, 2025
HOPKINS26 = "https://www.wmdt.com/2026/07/discover-delmarva-hopkins-farm-creamery/"                         # Jul 6, 2026
UDAIRY26 = "https://www.udel.edu/udaily/2026/september/udairy-creamery-ice-cream-cow-cone/"                 # Sep 23, 2026
BREW = "https://visitsoutherndelaware.com/food-and-drink/breweries-wineries-distilleries/list/alpha"         # undated list
DATED = {FALL26, BRUNCH26, SURF25, ICE25, HOPKINS26, UDAIRY26}

# guide -> rows of (name as our data has it, town, street number, note, founded (at this address), founded note, [sources],
#                   evidence: "dated" | "dph")
GUIDES = {
 "scrapple": [
  ("Helen's Sausage House", "Smyrna", "4866", "Known for its sausage and scrapple breakfast platters (Delaware Tourism Office, 2026); scrapple and egg on bread.",
   None, None, [FALL26, DINNER23], "dated"),
  ("Cantwell's Tavern", "Odessa", "109", "A scrapple cheesesteak on its brunch menu, in a tavern built in 1822.", None, None, [BRUNCH26], "dated"),
  ("Roost Pub & Kitchen", "Wilmington", "829", "A scrapple bao bun at Sunday brunch.", None, None, [BRUNCH26], "dated"),
  ("First State Brewing Company", "Middletown", "109", "A scrapple cheesesteak at the brewery's own restaurant.", None, None, [DINNER23], "dph"),
  ("Skipjack Dining", "Newark", "401", "A scrapple sandwich with cheddar eggs at brunch.", None, None, [BRUNCH22], "dph"),
  ("The Peach Blossom Eatery", "Newark", "76", "Scrapple with two over-easy eggs, greens and hot pepper jam on rye.", None, None, [BRUNCH22], "dph"),
  ("Kid Shelleen's", "Wilmington", "1801", "The Union Street Benedict: scrapple and poached eggs under chipotle-cheese sauce.", None, None, [BRUNCH22], "dph"),
  ("Grain Craft Bar + Kitchen", "Newark", "270", "A scrapple cheesesteak.", None, None, [BRUNCH22], "dph"),
 ],
 "boardwalk": [
  ("Grotto Pizza", "Rehoboth Beach", "15", "Grotto's swirl-sauce slice, a Rehoboth boardwalk staple (Delaware Tourism Office).",
   None, None, [BEACH, WINDOWS], "dph"),
  ("Gus & Gus Place", "Rehoboth Beach", "15", "Burgers, dogs, fried chicken and cheesesteaks at a boardwalk window, an “obligatory pilgrimage” (Cape Gazette).",
   None, None, [WINDOWS], "dph"),
 ],
 "crab": [
  ("The Surfing Crab Restaurant and Bar", "Lewes", "16723", "Crab cakes and, in season, hard-shell crabs; its Cruising Crab truck sells crabs while the restaurant closes for the winter.",
   None, None, [SURF25], "dated"),
  ("The Crab Connect", "Lewes", "17580", "Crabs steamed on site, on Route 1 north of Lewes.", None, None, [CRABCON], "dph"),
  ("Henlopen City Oyster House", "Rehoboth Beach", "50", "An oyster house a block from the boardwalk.", None, None, [BEACH], "dph"),
 ],
 "italian": [
  ("Mrs. Robino's Restaurant", "Wilmington", "520", "Little Italy's “80-year-old Italian restaurant” (The Inquirer), a homey Italian-American favorite.",
   None, "The family's own count is open since 1940; not checked as this address.", [INQ, FRESH23], "dph"),
  ("Ristorante Attilio", "Wilmington", "1900", "A homey Italian-American favorite (Visit Wilmington).", None, None, [FRESH23], "dph"),
  ("Scalessa's \"My Way\" Old School Italian Kitchen", "Wilmington", "1836", "Old-school Italian, known for its spaghetti and meatball sub.",
   None, None, [FRESH23, DINNER23], "dph"),
  ("Piccolina Toscana", "Wilmington", "1412", "Tuscan Italian, “higher aspirations and impeccable execution” (Visit Wilmington).", None, None, [FRESH23], "dph"),
  ("Gaudiello's Italian Hoagies", "Wilmington", "29", "A local favorite for subs (Visit Wilmington).", None, None, [FRESH23], "dph"),
 ],
 "creamery": [
  ("Woodside Farm Creamery", "Hockessin", "1310", "Ice cream made on a family farm, with savory flavors like “Motor Oil” and “Bacon”.", None, None, [ICE25], "dated"),
  ("Hopkins Farm Creamery", "Lewes", "18186", "Ice cream made fresh on the farm every day, more than 25 flavors.", None, None, [HOPKINS26, ICE25], "dated"),
  ("Vanderwende Farm Creamery", "Bridgeville", "4003", "Ice cream made on the farm from its own dairy herd of 300-plus cows.", None, None, [ICE25], "dated"),
  ("UDairy Creamery", "Newark", "549", "The University of Delaware's creamery, scooping ice cream from the college farm's milk since 2011; its seasonal 1st State Cobbler is peach.",
   None, None, [UDAIRY26, ICE25], "dated"),
 ],
 "brewpub": [
  ("Dogfish Head", "Rehoboth Beach", "316", "Dogfish Head Brewings & Eats, the brewpub where the brewery began, with wood-fired pizzas.", None, None, [BREW], "dph"),
  ("Big Oyster Brewery", "Lewes", "1007", "A brewery with its own kitchen.", None, None, [BREW], "dph"),
  ("Thompson Island Brewing Company", "Rehoboth Beach", "30133", "A brewery restaurant, known for its Naptime Birria Burger.", None, None, [DINNER23, BREW], "dph"),
  ("Ocean View Brewing Company", "Ocean View", "85", "A brewery restaurant, known for its Naptime Burger.", None, None, [DINNER23, BREW], "dph"),
  ("First State Brewing Company", "Middletown", "109", "A brewery with a full kitchen (its scrapple cheesesteak is on the scrapple list).", None, None, [DINNER23], "dph"),
  ("Crooked Hammock Brewery", "Lewes", "36707", "A brewery and backyard restaurant.", None, None, [BREW], "dph"),
 ],
}
KIND = {"scrapple": "scrapple", "boardwalk": "boardwalk", "crab": "crab houses & seafood", "italian": "wilmington italian",
        "creamery": "creamery", "brewpub": "brewpub"}
EVERY = set()
JBF_2026 = "https://www.jamesbeard.org/stories/james-beard-award-semifinalists-2026"
JBF_2022 = "https://www.jamesbeard.org/stories/the-2022-james-beard-award-semifinalists"
PHILLY_2025 = "https://www.phillymag.com/foobooz/2025/01/22/2025-james-beard-award-semifinalists/"
DPM_KERN = "https://www.delawarepublic.org/show/the-green/2024-06-07/chef-matt-kern-of-one-coastal-discusses-being-delawares-first-ever-james-beard-finalist"
JBF = [
    ("La Fia Bistro", "Wilmington", "421", ["Best Chef: Mid-Atlantic semifinalist 2026 (Dwain Kalup)"], [JBF_2026]),
    ("Bardea Food & Drink", "Wilmington", "620", ["Best Chef: Mid-Atlantic semifinalist 2025 (Antimo DiMeo)", "Best Chef: Mid-Atlantic semifinalist 2022 (Antimo DiMeo)"],
     [PHILLY_2025, JBF_2022]),
    ("One Coastal", "Fenwick Island", "101", ["Best Chef: Mid-Atlantic finalist 2024 (Matthew Kern)"], [DPM_KERN]),
]
CLOSED = [
    {"name": "The House of William & Merry", "city": "Hockessin", "address": "1336 Old Lancaster Pike", "match_names": ["THE HOUSE OF WILLIAM AND MERRY"],
     "note": "Closed in July 2026 after about 15 years (James Beard Best Chef: Mid-Atlantic semifinalist 2022, Bill Hoffman).",
     "sources": ["https://whatnow.com/philadelphia/restaurants/15-year-old-delaware-restaurant-announces-permanent-closure/", JBF_2022]},
]


def find(name, town, num):
    k = norm(name)
    hits = [i for i, n in enumerate(C["name"]) if (town is None or (C["city"][i] is not None and M["cities"][C["city"][i]] == town))
            and (norm(n) == k or norm(n).startswith(k + " ") or k.startswith(norm(n) + " ") or norm(n).replace(" ", "") == k.replace(" ", ""))]
    if num:
        hits = [i for i in hits if (C["addr"][i] or "").split(" ")[0] == num]
    return hits


def evidence_ok(ev, srcs, i):
    if ev == "dated":
        return any(s in DATED for s in srcs)
    insp = INSP.get(i)   # "dph": a DPH inspection in 2025 or 2026
    return bool(insp) and (insp[4] or "") >= "2025-01-01"


leads, n_out = [], {}
for kind, rows in GUIDES.items():
    out = []
    for name, town, num, note, founded, fnote, srcs, ev in rows:
        hits = find(name, town, num)
        if len(hits) > 1 and name not in EVERY:
            lic = [i for i in hits if C["tier"][i] == 2]
            hits = lic if len(lic) == 1 else hits
        if not hits or (len(hits) > 1 and name not in EVERY):
            leads.append(f"- {kind}: {name} ({town}{', ' + num if num else ''}) — {len(hits)} matches in our data; not added"); continue
        for i in hits:
            if not evidence_ok(ev, srcs, i):
                leads.append(f"- {kind}: {name} ({town}) — no 2025-26 evidence it operates ({ev}); not added"); continue
            city = M["cities"][C["city"][i]]
            out.append({"name": C["name"][i], "address": C["addr"][i], "city": city, "zip": str(C["zip"][i]) if C["zip"][i] else None,
                        "kinds": [KIND[kind]], "dishes": [], "note": note, "founded": founded, "founded_note": fnote, "website": None,
                        "open": True, "evidence_date": "2025-26" if ev == "dated" else "2025-26 DPH inspection",
                        "sources": srcs + ([DPH] if ev == "dph" else []), "match_names": [name.upper()] if norm(name) != norm(C["name"][i]) else []})
    json.dump(out, open(f"{R}/app/{kind}.json", "w"), indent=1, ensure_ascii=False)
    n_out[kind] = len(out)
jb = []
for name, town, num, honors, src in JBF:
    hits = find(name, town, num)
    if len(hits) != 1:
        leads.append(f"- James Beard: {name} ({town}) — {len(hits)} matches; not added"); continue
    i = hits[0]
    if not evidence_ok("dph", [], i):
        leads.append(f"- James Beard: {name} ({town}) — no 2025-26 DPH inspection; not added"); continue
    jb.append({"name": C["name"][i], "address": C["addr"][i], "city": town, "zip": None, "honors": honors, "open": True,
               "sources": src + [DPH], "match_names": [name.upper()]})
json.dump(jb, open(f"{R}/jbf.json", "w"), indent=1, ensure_ascii=False)
json.dump(CLOSED, open(f"{R}/closed.json", "w"), indent=1, ensure_ascii=False)
open(f"{R}/app/LEADS.md", "w").write("# Delaware research leads (not yet verified)\n\nWritten by pipeline/build_research.py.\n\n" + "\n".join(leads) + """

## Not yet checked (first pass, 2026-10-27)
- Boardwalk: Thrasher's French Fries (three Rehoboth stands: 103 S Boardwalk, 7 and 26 Rehoboth Ave; Revenue licenses current, but no
  DPH record and no map listing, so it isn't in the data; Cape Gazette 2022 and the Visit Southern Delaware listing name it). Kohr Bros.
  Frozen Custard (Rehoboth, Bethany; DPH inspects its Bethany and Fenwick stands at other addresses than the listings), Obie's by the Sea
  (Rehoboth boardwalk), Nicola Pizza (now at Ocean One Plaza, Lewes, off the avenue), Dolle's and Fisher's Popcorn (candy and popcorn
  shops: stores). Need a 2025-26 page or the right DPH record for each.
- Crab houses: Fenwick Crab House (not in our data), Crabby Dick's (Rehoboth; Cape Gazette Apr 2025, but our data has only the Delaware City
  one), Claws Seafood House, Starboard Claw, Lestardo's, Sambo's Tavern, Boondocks (their Visit Delaware listings render no text for us:
  need another page naming them for crabs), No. 1 Fresh Steamed Crabs (WMDT Apr 2026, but DPH marks its record closed).
- Slippery dumplings: the Cape Gazette ties them to Sussex church suppers; Jimmy's Grille's Bridgeville location (chicken and dumplings)
  isn't in our data. No restaurant found yet: the guide stays off.
- Oldest: Kelly's Logan House (1864, Trolley Square; its listing text didn't render for us), Stockley Tavern (1948; the Cape Gazette page
  answered 403), Charcoal Pit (1956?), Deer Park Tavern (building 1851; the business is newer), Jessop's Tavern (building 1674, tavern
  since 1996), Mrs. Robino's (open since 1940 per the family; address continuity unchecked). The oldest list needs a source that says
  the place opened at this address.
- Peach pie (the state dessert): no restaurant page found; Fifer Orchards Farm Kitchen (Wyoming) and T.S. Smith's Orchard Point Market
  (Bridgeville) are farm markets.
- Capriotti's began in Wilmington in 1976 and is now a chain: brand facts only, no hand-checked location.
""")
print(n_out, "| James Beard:", len(jb), "| leads:", len(leads))
for l in leads:
    print(l)
