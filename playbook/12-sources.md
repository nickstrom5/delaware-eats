# Delaware: sources and calibration (checked 2026-10-27)

Every host was robots-checked before its first request (`pipeline/check_sources.py`, RFC 9309 matcher; cache in
`data/research/source_hosts.json`). Nothing here was scraped from a page that blocks us.

## Official records

| Source | What we use | Terms | Cadence | Size on 2026-10-27 | Notes |
|---|---|---|---|---|---|
| DPH Office of Food Protection, "Food Establishment Inspection Violations", data.delaware.gov **384s-wygj** (`https://data.delaware.gov/resource/384s-wygj.json`; page https://data.delaware.gov/Health/Food-Establishment-Inspection-Violations/384s-wygj returns 200) | Every inspection in the past two years: establishment name, street address, town, zip, date, type, Food Code section and its title; Socrata's point for the address | Public Domain (dataset metadata; attribution "Department of Health and Social Services, Division of Public Health, Office of Food Protection") | Weekly ("Frequency of publishing: Weekly"); rows updated 2026-10-23 | 33,519 rows; 3,732 establishments (name + address + zip); 9,199 inspections (7,773 Routine, 1,194 Follow-up, 232 Complaint); 942 inspections cited nothing | See "Reading the DPH feed" below |
| Division of Revenue, "Delaware Business Licenses", data.delaware.gov **5zy2-grhr** | Business activity "RETAILER  RESTAURANT" (two spaces): trade name, license number, valid from/to, address | Public Domain (attribution "Department of Finance, Division of Revenue") | Daily; rows updated 2026-10-27 | 2,566 restaurant licenses; 2,531 with a Delaware address | Current licenses only. The legal name is never shown. Its points are zip centroids (the geocode reads Address 2, mostly empty), so licenses are placed again on Overture address points (2,201 by zip, 23 by town) or the US Census batch geocoder (177); 194 records stay unplaced (mostly mailing addresses). A license runs up to 3 years, so it confirms a business, not that it's open. |

**No local health departments.** DPH inspects every food establishment statewide, Wilmington included (DPH: "permits to over 3,300
food establishments"). Delaware has **no official grade, score or placard**: the feed has no score, result or priority field, DPH's own
2019 report form lists a score as optional, and nothing describes a posted placard. DPH's FAQ and report pages are on dhss.delaware.gov,
which answers our checker with a bot check (2026-10-27), so they were not read directly; the old report listing
(dhss.delaware.gov/dph/hsp/feir.html) now redirects there. The app and site link the dataset page as the official record.
**We compute no grade.** A place shows its latest routine inspection (date, number of Food Code sections cited), anything after it, and
its whole history with each section's number and title.

### Reading the DPH feed
- One row per Food Code section cited at one inspection; an inspection with nothing cited is one row with no code. An inspection is
  its (establishment, date, type). `vio_desc` is the section's title ("6-501.111 Controlling Pests"), not what the inspector saw: we never
  turn a title into a finding ("evidence of pests"), and we count sections, never "critical" ones (the feed has no priority flag).
- Records through **2026-10-20** (`official.DPH_THROUGH`): the fetch date minus 7 days; the feed's last real day was 10/21, and 10 rows
  are dated 2026-11-18 and 2026-12-03 (future dates), all dropped. The window rolls (it began 2024-10-14 on this fetch, 2024-09-17 in
  September), so `fetch_official.py` snapshots each fetch by date.
- Names: 858 of 3,553 read "DBA - legal entity - #store", cut at 50 characters; we show only the DBA (`official.dph_name`), or the
  second part when the first is a company ("Sussex Concessions LLC - Coastal Kitchen at Bear T"). 234 names end in "(Closed)" (also
  "(CLOSED)", "-(Closed)", cut-off "(Clos"): DPH's closure. DPH's export also lost accents and apostrophes ("Arenas Caf  5 Points",
  "DominickG  s Pizza"): repaired to "Café" and "'s". Suffixes "(MOB)" (mobile units), "(CWOP)", "(Trailer)", "(Truck)" mark non-restaurants.
- Schools, hospitals, churches, day cares, store counters (Weis's Snowfox sushi) and grocery and convenience stores are in the feed;
  `official.OTHER` and `official.RETAIL` keep them off the restaurant list.
- A "(Closed)" DPH record outranks a valid license: Iron Hill's three brewpubs are DPH-closed (2025) while their Revenue licenses run into
  2026-27. A listing whose only DPH record at its street number is closed, with no live DPH record of the same name there, is dropped
  (87 on the first build) unless hand-checked open. 249 DPH records are closed; their share in the beach towns (10.8%) is below those
  towns' share of all records (13.2%), so "(Closed)" isn't a winter marker. 25 closed records sit beside a live record of the same name
  at the same address (new owner, new record).
- Routine inspections come every 3 to 10 months (gap median 189 days, 90th percentile 398). An establishment uninspected for 18 months
  (before 2025-04-20) can't by itself add a place (`official.DPH_STALE`).
- Not double-counted: 9ubi-inbe, uedd-ty44, hze2-h54j and a2rb-t3ci are charts or filtered views of 384s-wygj.

## Not usable
- **Alcohol.** OABCC (oabcc.delaware.gov, robots-usable) publishes no licensee list or search; its Facts & Figures page offers an active
  list on request by email. That email needs Nick's yes (not sent). Revenue's "RETAILER  ALCOHOL - ON/OFF PREMISE" activities (75 / 333)
  are tax categories, not liquor licenses. The app shows "—" for alcohol.
- **Property values.** FirstMap's Delaware State Parcels 2.0 has PIN, acres and county only; New Castle County's parcels have owner names
  and no values; assessments are search-only. No building-value board.
- **Historical licenses** (khpy-2pnr) end in 2018: not used.

## Map listings and the 2021 snapshot
- **Overture Maps places, release 2026-10-21.0** (CDLA-Permissive-2.0 / Apache-2.0, Foursquare NOTICE): 4,575 eating and drinking
  listings with region DE; 172 marked permanently closed. Out of state: a point inside Maryland, Pennsylvania or New Jersey land
  (Overture division areas) is dropped however close to the line (Delmar's Maryland half, Ocean City at Fenwick Island).
- **Overture address points** (same release): 562,288 in Delaware, used to place records.
- **Divisions:** Overture's division areas for the state and county outlines (the app ships the simplified outline only; attribution in About).
- **UCSD Google Local 2021** (`meta-Delaware.json.gz`, mcauleylab.ucsd.edu): ratings, reviews, price and 2021 closures for the **web
  leaderboard only, never the app**. 2,708 food listings (269 closed by 2021); 2,087 Overture listings matched.

## Calibration (map listings vs DPH's live establishments, `data/de/calibration.json`)
Delaware's statewide inspection list makes this the first state calibrated statewide, not in one or two cities. Listings that pass the
first cleaning (4,483), matched to DPH establishments inspected in the window and not marked closed (3,374 with a point):

| Kind of listing | Statewide | New Castle | Kent | Sussex | vs Revenue licenses |
|---|---|---|---|---|---|
| Meta + open in Google 2021 | 75.7% of 1,520 | 76.7% of 850 | 80.9% of 230 | 71.1% of 440 | 55.5% |
| Meta only | 39.5% of 1,416 | 41.4% | 49.5% | 32.4% | 29.7% |
| Brand feed only | 37.5% of 64 | 21.6% | 70.6% | 40.0% | 23.4% |
| Foursquare only | 10.4% of 268 | 10.0% | 17.9% | 8.6% | 10.1% |
| BrightQuery only | 15.6% of 418 | 15.3% | 22.6% | 11.7% | 11.7% |
| Microsoft only | 30.6% of 144 | 31.2% | 37.5% | 20.8% | 16.0% |
| Foursquare/BrightQuery/Microsoft + Google 2021 | 27.3% of 384 | 29.2% | 22.7% | 26.3% | 22.7% |
| Google 2021 says closed | 9.0% of 100 | | | | |
| Overture says closed | 4.6% of 151 | | | | |

App grouping (no Google data): Meta confidence ≥ 0.95: 73.3% of 1,908; 0.90–0.95: 47.9% of 491; below: 14.9% of 550; brand feed 40.8%
of 71; BrightQuery ≥ 0.95: 24.8% of 379; other sources 16.7% of 918.
Coverage the other way: open map listings hold **67.8% of DPH's 2,717 restaurant-like establishments** (New Castle 66.7%, Kent 67.2%,
Sussex 70.7%); inspected restaurants among the rest are added from DPH's list (320 on the first web build).
Sussex runs lowest: Meta-only listings there match 32%, the beach towns' seasonal stands and beach-block shops.
These are lower bounds: a place under a company's or an older name on its DPH record counts as a miss, and a bar serving no food may hold
no food permit.

**Keep rule** (the family's, from the numbers above): official match, hand-checked, Meta ≥ 0.95, Meta ≥ 0.90 with a website, or a brand
feed (app); web adds the Google 2021 two-source rule. Dropped: Foursquare, BrightQuery and Microsoft listings with no official match.

## Counts (first web build, 2026-10-27)
3,269 restaurants (3,417 places with non-restaurants) in 66 towns: 2,390 matched to DPH or a Revenue license, 234 in two sources, 645
listing only. BLS QCEW counts 2,368 private eating and drinking establishments with employees (NAICS 722, 2024), so the web list is
larger: it holds owner-run places with no payroll, and seasonal beach stands.

## Honors
- **MICHELIN:** no Delaware guide and no Delaware restaurant (the Northeast Cities guide covers Boston, Philadelphia, New York, Chicago and
  DC; the 2025 selection was the latest found on 2026-10-27). The Quoin (Wilmington) holds a MICHELIN Key as a hotel: no restaurant board.
  Angelo's (Philadelphia Bib Gourmand) has a stall in Wilmington's DE.CO food hall: the honor stays with the Philadelphia restaurant.
  guide.michelin.com answers our checker with a bot check: re-check after the 2026 Northeast release by hand. No Bib Gourmand filter.
- **James Beard** (jamesbeard.org, robots-usable): La Fia (Dwain Kalup, Best Chef: Mid-Atlantic semifinalist 2026, jamesbeard.org);
  Bardea Food & Drink (Antimo DiMeo, semifinalist 2022 and 2025: jamesbeard.org 2022 list, phillymag.com 2025 list); One Coastal
  (Matthew Kern, Best Chef: Mid-Atlantic finalist 2024: delawarepublic.org). The House of William & Merry (Bill Hoffman, semifinalist
  2022) closed in July 2026 (whatnow.com). Person awards badge no restaurant: Sam Calagione (Dogfish Head; Outstanding Wine, Spirits or
  Beer Professional 2017) and Matt Haley (Humanitarian of the Year 2014). No America's Classics.

## Research hosts (robots check, 2026-10-27)
Usable: capegazette.com, delawarepublic.org, wboc.com, wmdt.com, visitdelaware.com, phillymag.com, whatnow.com, jamesbeard.org,
data.delaware.gov. Blocked for ClaudeBot: delawareonline.com, delawarelive.com, townsquaredelaware.com, wdel.com, coastalpoint.com,
delawarebusinesstimes.com; bot check: dhss.delaware.gov, guide.michelin.com. Expect short guides (the 4-place rule applies).
