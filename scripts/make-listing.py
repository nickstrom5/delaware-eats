#!/usr/bin/env python3
"""Writes the App Store listing and the App Review reply from the build's own counts (playbook/site-numbers.json, which
scripts/make-site.py rewrites on every run), so the copy never drifts from the data. Modeled on wa-eats/playbook/06 and 13.

Usage (from de-eats/): .venv/bin/python scripts/make-listing.py   (after make-site.py)
Writes playbook/06-app-store-listing.md, playbook/13-app-review-reply.md and playbook/app-store/listing.json (what
../scripts/asc_listing.py uploads once Nick creates the App Store Connect record and its FOLDERS line is added).
Checks before writing anything: Apple's length limits, no keyword repeating a name/subtitle word, no "best"/"top"/"#1", no price
claim outside the description's plain "free guide", the reply under 4,000 characters.
"""
import json, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
N = json.load(open(os.path.join(ROOT, "playbook", "site-numbers.json")))
R, T, INS, LIC, HON = N["restaurants"], N["towns"], N["inspection_records"], N["on_an_official_list"], N["honors"]
G = {k[6:]: v for k, v in N.items() if k.startswith("guide_") and isinstance(v, int)}
FLOOR = R // 1000 * 1000   # "2,000+": promo text and What's New outlive small data changes
SITE = "https://delaware.eatsranked.com/"   # until the CNAME resolves: https://nickstrom5.github.io/delaware-eats/

NAME = "Delaware Eats: Restaurants"
SUB = "Scrapple, Crabs & Boardwalk"
# no word from the name or subtitle and no trademarks; towns are the biggest search win (rotate after a month of App Store Connect
# search-term data)
KW = "wilmington,rehoboth,lewes,dover,newark,dewey,bethany,fenwick,middletown,brewpub,ice cream,food guide"
PROMO = (f"Scrapple breakfasts, crab houses, farm creameries and brewpubs, checked by hand, plus {FLOOR:,}+ restaurants from "
         f"Wilmington to Fenwick Island.")
WHATS_NEW = (f"First release: scrapple, crab houses, Wilmington Italian, farm creameries, brewpubs and {FLOOR:,}+ Delaware restaurants "
             f"with their state inspection records.")

DESC = f"""Where to eat in the First State, from scrapple at breakfast to a tray of steamed crabs near the beach.

Delaware Eats is a free guide to {R:,} Delaware restaurants, cafés, bars and bakeries in {T} towns across New Castle, Kent and Sussex counties, from Wilmington and Newark to Dover, Lewes and Rehoboth Beach. The guides below were checked by hand, and {LIC:,} places are on the state's own inspection or business-license records. No account, no ads.

DELAWARE GUIDES
• Scrapple Breakfasts: diners, taverns and a sausage house that put scrapple on the plate.
• Crab Houses & Seafood: steamed crabs, crab cakes and the shore's seafood spots.
• Wilmington Italian: family Italian kitchens in and around Wilmington.
• Farm Creameries: ice cream made on working dairy farms.
• Brewpubs and Boardwalk Classics, plus {HON} James Beard Award semifinalists and finalists.
• Health Inspections: the Delaware Division of Public Health's own records for {INS:,} places. Each one shows how many Food Code sections were cited at its latest routine inspection, its visits from the past two years by date, and the sections by name. DPH gives no grade, and the app adds none.

FINDING A PLACE
• Sort by distance from you, or browse each guide on the map.
• Search by name, town, street or dish, like "italian wilmington" or "scrapple smyrna".
• Filter by town or cuisine, or hide chains.
• Save places on your device, and find guide places from iPhone search.

LIVE DETAILS FROM APPLE MAPS
"Ratings, hours & photos" on any place opens Apple Maps' own place card with today's hours, photos, ratings and directions.

WHERE THE DATA COMES FROM
Each guide place was checked by hand in October 2026: a dated 2025 or 2026 story, festival or tourism page names it for the food, or a 2025 or 2026 state inspection shows it's operating. The full list comes from Overture Maps open data, matched to the Division of Public Health's inspection records and the Division of Revenue's restaurant licenses. Website links are checked before release. Nothing is ranked by star ratings.

PRIVATE BY DESIGN
No account, no tracking, no ads. If you share your location, it only sorts lists on your device. Saved places never leave it.

Restaurants open and close, so check before you go. Found a mistake? Email nick@eatsranked.com.

An independent app, not affiliated with any restaurant, chain or government agency (including the State of Delaware, the Delaware Division of Public Health and the Delaware Division of Revenue), or with the James Beard Foundation. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Place data from Overture Maps Foundation (CDLA Permissive 2.0) and others; sources and licenses are on the About tab."""

REPLY = f"""Thank you. Here is the information requested. A screen recording from an iPhone running the latest iOS is attached. It starts at launch and shows the full flow.

1. Screen recording: attached. There is no account, login, user-generated content or paid content.

2. Purpose and audience: Delaware Eats is a free guide to restaurants in Delaware. It centers on the state's own food: scrapple breakfasts, crab houses, Wilmington's Italian kitchens, farm creameries and brewpubs, each place checked by hand in October 2026 against a 2025 or 2026 source. It also lists {R:,} restaurants, cafés and bars in all three counties, matched to the Delaware Division of Public Health's food inspection records and the Division of Revenue's restaurant licenses. It is for Delaware residents and beach visitors deciding where to eat, with no ads, account or tracking.

3. How to use it (no login, no setup, no sample files needed):
- Home → Scrapple Breakfasts (or Crab Houses & Seafood, Wilmington Italian, Farm Creameries, Brewpubs, James Beard Honors, Health Inspections, Near Me) → tap any place.
- On a place, "Ratings, hours & photos" opens Apple Maps' own place card through MapKit. Directions, Call and Website are below it, then the place's state inspection visits.
- Search from the Home search box by name, town, street or dish ("italian wilmington", "scrapple smyrna").
- The Map tab shows each guide as pins. "My location" and the Nearest sort use location only if allowed, on the device.
- The heart saves a place on the device, under the Saved tab. The About tab lists the data sources, licenses and the independence statement.
- On iPad, a sidebar replaces the tabs; a place opens in the right-hand column.
- Location: outside Delaware (where App Review usually is), the map says so and stays on Delaware, and distance sorting still works from where you are.
- "Delaware Eats" is the short Home Screen name of "Delaware Eats: Restaurants".

4. External services and data:
- Apple MapKit: maps, local search to find a place's Apple Maps listing, and Apple's place card for live hours, photos and ratings.
- Core Location: optional, on-device only, for distance sorting.
- Core Spotlight: on-device indexing so places appear in iPhone search.
- No backend, accounts, analytics, advertising, payments or AI services. The restaurant data is bundled in the app; the app may download a newer copy of the same data file from the website below.
- Bundled data sources: Overture Maps Foundation open place data (CDLA Permissive 2.0, with Foursquare-sourced records under Apache 2.0 and AllThePlaces under CC0; license texts are in the app); the Delaware Division of Public Health's food establishment inspection records and the Division of Revenue's business licenses (data.delaware.gov, public domain); James Beard Foundation award records (facts only); and our own research of public websites and local news.
- The website with the privacy policy and support page is static and hosted on GitHub Pages: {SITE}

5. Regional differences: none. The content covers Delaware; the app is offered in the United States and works the same everywhere.

6. Regulated or protected material: the app is not in a regulated industry and includes no protected third-party material. The data is open-licensed or public record, with attribution and licenses on the About tab. Ratings, hours and photos appear only inside Apple's own place card through MapKit; the app stores no ratings or reviews. Inspection records are the Division of Public Health's own, labeled and dated; DPH issues no grades and the app computes none. Every website link was checked before release, and adult venues are excluded. The app is independent and not affiliated with any restaurant, agency or the James Beard Foundation.

Support: nick@eatsranked.com"""

# ---------------- checks (nothing is written unless all pass)
problems = []
for label, text, limit in (("name", NAME, 30), ("subtitle", SUB, 30), ("keywords", KW, 100), ("promotional text", PROMO, 170),
                           ("What's New", WHATS_NEW, 4000), ("description", DESC, 4000), ("review notes", REPLY, 4000)):
    if len(text) > limit:
        problems.append(f"{label}: {len(text)} characters, limit {limit}")
title_words = set(re.findall(r"[a-z]+", (NAME + " " + SUB).lower()))
for kw in KW.split(","):
    if kw != kw.strip() or not kw:
        problems.append(f"keyword {kw!r}: no spaces around commas, no empty entries")
    if set(kw.split()) & title_words:
        problems.append(f"keyword {kw!r} repeats a word from the name or subtitle")
for text, label in ((KW, "keywords"), (PROMO, "promotional text"), (SUB, "subtitle"), (WHATS_NEW, "What's New")):
    for bad in (r"\bbest\b", r"\btop\b", r"#1", r"\bfree\b", r"\bevery\b"):
        if re.search(bad, text, re.I):
            problems.append(f"{label}: contains {bad!r}")
if re.search(r"\bevery (?:restaurant|place)\b|\ball [\d,]+ ", DESC + REPLY, re.I):
    problems.append("description/reply: an 'every restaurant' or 'all N' claim the data can't back")
if problems:
    sys.exit("not written:\n  " + "\n  ".join(problems))

listing = {"bundleId": "com.delawareeats.ios", "name": NAME, "subtitle": SUB, "privacyPolicyUrl": SITE + "privacy.html",
           "primaryCategory": "FOOD_AND_DRINK", "secondaryCategory": "TRAVEL", "description": DESC, "keywords": KW,
           "promotionalText": PROMO, "supportUrl": SITE, "marketingUrl": SITE, "reviewNotes": REPLY}
os.makedirs(os.path.join(ROOT, "playbook", "app-store"), exist_ok=True)
json.dump(listing, open(os.path.join(ROOT, "playbook", "app-store", "listing.json"), "w"), indent=1, ensure_ascii=False)

open(os.path.join(ROOT, "playbook", "06-app-store-listing.md"), "w").write(f"""# App Store listing (ASO)

Written by `scripts/make-listing.py` from `site-numbers.json` ({N['generated']}); re-run it after every data refresh, never hand-edit.
The machine copy is `app-store/listing.json` (read by `../scripts/asc_listing.py` once Nick creates the App Store Connect record and
adds `"com.delawareeats.ios": "de-eats"` to its FOLDERS). The URLs assume delaware.eatsranked.com is live; until Nick's CNAME
resolves, use https://nickstrom5.github.io/delaware-eats/.

## Name (30 max)
`{NAME}` ({len(NAME)})

## Subtitle (30 max)
`{SUB}` ({len(SUB)})

Together they index: delaware, eats, restaurants, scrapple, crabs, boardwalk. Home Screen name: Delaware Eats.

## Keywords (100 max)
`{KW}` ({len(KW)})

- No word repeats the name or subtitle; no trademarks (no Dogfish Head, Grotto, Thrasher's, Capriotti's, Wawa or "Blue Hens"), no "best", "top" or "#1".
- Towns are the biggest win; Milford, Seaford, Smyrna, Milton and Hockessin didn't fit. Rotate them in after a month of App Store Connect
  search-term data. Apple's public search can't be used for this research (itunes.apple.com's robots.txt blocks Claude).

## Promotional text (170 max, editable any time without review)
`{PROMO}` ({len(PROMO)})

## Description ({len(DESC)} of 4,000)
```
{DESC}
```

## What's New (1.0)
`{WHATS_NEW}`

## Screenshots
Framed by `scripts/appstore-screenshots.py`: `app-store/iphone/` (8, 1320x2868, the 6.9" slot) and `app-store/ipad/` (6, 2064x2752, the
13" slot). Upload one file at a time in file order and check the order after a reload. No inspections board and no place whose latest
DPH visit was a follow-up or complaint visit appears in any image (a unit test checks the picks). Captured 2026-10-28 on iOS 27.0
simulators (iPhone 17 Pro Max, iPad Pro 13-inch M5) with `scripts/capture-screenshots.sh`; raw captures in `app-store/raw/`.

## Category and age rating
Primary Food & Drink, secondary Travel. Age rating: alcohol references "Infrequent" (bars, taverns) → 13+; everything else None/No.
Pricing $0.00, available in the United States. Content rights: yes, third-party content, with the rights (open data, public records,
Apple's place card). Untick "Sign-in required".

## App Review
Reply and recording script: `13-app-review-reply.md`. Put the reply in App Review Information → Notes from the start.
""")

open(os.path.join(ROOT, "playbook", "13-app-review-reply.md"), "w").write(f"""# App Review: prepared before submitting (Guideline 2.1 "Information Needed")

Written by `scripts/make-listing.py` ({N['generated']}). Wisconsin's new-developer review asked for a screen recording from a physical
device, starting at launch, plus answers to six questions; Delaware Eats should expect the same. Put the reply below in **App Review
Information → Notes** from the start ({len(REPLY):,} of 4,000 characters), and record the video before submitting. If Apple raises
Guideline 4.3(a), answer with Delaware's own guides and sources (scrapple, crab houses, Wilmington Italian, farm creameries, the
Division of Public Health's statewide inspection records and the Division of Revenue's licenses); never compare with the other state
apps in the Notes.

## Screen recording (Nick, on his iPhone, latest iOS, 60–120 seconds, no sound)

Install from TestFlight first (the internal tester's email must be the Apple ID under Settings › your name › Media & Purchases on the
phone, or TestFlight says "not available"). Record with Control Center → Screen Recording:

1. Start on the Home Screen and tap **Delaware Eats**. The recording must begin with the launch.
2. Home: scroll the cards a little.
3. Tap **Scrapple Breakfasts**, then **Helen's Sausage House**.
4. Tap **Ratings, hours & photos**; Apple's place card opens. Close it, then scroll to the Division of Public Health inspection section.
5. Tap the **heart** (Save), then go back to Home.
6. Tap the search box and type `italian wilmington`. Open one result.
7. Tap the **Map** tab, then **Crab houses**, then a pin and its name.
8. Tap the **Saved** tab, where the saved place shows. Then tap **About** and scroll to the sources.

## Reply text

```
{REPLY}
```
""")
print(f"wrote listing.json, 06-app-store-listing.md, 13-app-review-reply.md | keywords {len(KW)}/100, promo {len(PROMO)}/170, "
      f"description {len(DESC):,}/4,000, reply {len(REPLY):,}/4,000")
