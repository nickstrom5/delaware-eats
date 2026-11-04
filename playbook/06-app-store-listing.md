# App Store listing (ASO)

Written by `scripts/make-listing.py` from `site-numbers.json` (2026-10-28); re-run it after every data refresh, never hand-edit.
The machine copy is `app-store/listing.json` (read by `../scripts/asc_listing.py` once Nick creates the App Store Connect record and
adds `"com.delawareeats.ios": "de-eats"` to its FOLDERS). The URLs assume delaware.eatsranked.com is live; until Nick's CNAME
resolves, use https://nickstrom5.github.io/delaware-eats/.

## Name (30 max)
`Delaware Eats: Restaurants` (26)

## Subtitle (30 max)
`Scrapple, Crabs & Boardwalk` (27)

Together they index: delaware, eats, restaurants, scrapple, crabs, boardwalk. Home Screen name: Delaware Eats.

## Keywords (100 max)
`wilmington,rehoboth,lewes,dover,newark,dewey,bethany,fenwick,middletown,brewpub,ice cream,food guide` (100)

- No word repeats the name or subtitle; no trademarks (no Dogfish Head, Grotto, Thrasher's, Capriotti's, Wawa or "Blue Hens"), no "best", "top" or "#1".
- Towns are the biggest win; Milford, Seaford, Smyrna, Milton and Hockessin didn't fit. Rotate them in after a month of App Store Connect
  search-term data. Apple's public search can't be used for this research (itunes.apple.com's robots.txt blocks Claude).

## Promotional text (170 max, editable any time without review)
`Scrapple breakfasts, crab houses, farm creameries and brewpubs, checked by hand, plus 2,000+ restaurants from Wilmington to Fenwick Island.` (139)

## Description (2726 of 4,000)
```
Where to eat in the First State, from scrapple at breakfast to a tray of steamed crabs near the beach.

Delaware Eats is a free guide to 2,879 Delaware restaurants, cafés, bars and bakeries in 64 towns across New Castle, Kent and Sussex counties, from Wilmington and Newark to Dover, Lewes and Rehoboth Beach. The guides below were checked by hand, and 2,391 places are on the state's own inspection or business-license records. No account, no ads.

DELAWARE GUIDES
• Scrapple Breakfasts: diners, taverns and a sausage house that put scrapple on the plate.
• Crab Houses & Seafood: steamed crabs, crab cakes and the shore's seafood spots.
• Wilmington Italian: family Italian kitchens in and around Wilmington.
• Farm Creameries: ice cream made on working dairy farms.
• Brewpubs and Boardwalk Classics, plus 3 James Beard Award semifinalists and finalists.
• Health Inspections: the Delaware Division of Public Health's own records for 2,053 places. Each one shows how many Food Code sections were cited at its latest routine inspection, its visits from the past two years by date, and the sections by name. DPH gives no grade, and the app adds none.

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

An independent app, not affiliated with any restaurant, chain or government agency (including the State of Delaware, the Delaware Division of Public Health and the Delaware Division of Revenue), or with the James Beard Foundation. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Place data from Overture Maps Foundation (CDLA Permissive 2.0) and others; sources and licenses are on the About tab.
```

## What's New (1.0)
`First release: scrapple, crab houses, Wilmington Italian, farm creameries, brewpubs and 2,000+ Delaware restaurants with their state inspection records.`

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
