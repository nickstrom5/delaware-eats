# Delaware Eats (de-eats) — notes for Claude Code sessions

Started 2026-10-27 from `../state-prompts/DELAWARE_PROMPT.md` and `../STATE_EATS_PLAYBOOK.md` (read both). Pipeline, app, site and QA ported
from `../oh-eats/`; `tracking_params.py`, `injection.py`, `link_blocklist.py` are the shared copies (same as fl-eats and co-eats); the
website blocklist is the union of every state's (886). Never modify another state's folder (Pennsylvania and Maryland's neighbors are
other sessions'). Guideline 4.3(a): share no places or copy with other states.

- Brand (Nick, 2026-10-27, `playbook/05-naming.md`): "Delaware Eats: Restaurants", Home Screen "Delaware Eats", subtitle "Scrapple, Crabs &
  Boardwalk"; icon = boardwalk fries in an unbranded paper cup on colonial blue #1F3B6F (`scripts/make-brand.swift`, passes
  `../state-prompts/icon-style/check.swift`); palette colonial blue #1F3B6F + buff #E3C79A (fill only) + peach blossom #F4A7A3 (fill
  only; deep peach #B4544E for pins); header = the Twelve-Mile Circle arc. Bundle id com.delawareeats.ios; site delaware.eatsranked.com
  (until Nick's CNAME: nickstrom5.github.io/delaware-eats). No OABCC alcohol-list email for now (draft in `playbook/records-requests.md`).
- Leaderboard: private artifact (link in `LOCAL.md`), `site/` (git-ignored) from `scripts/make-leaderboard.py` (template
  `../wi-eats/site/index.html`); republish with `delaware.json`, `de_detail.json`, `de_shapes.json`. Uses Google 2021 ratings, labeled.

## Sources (details, terms, calibration: `playbook/12-sources.md`)
- **DPH inspections** (data.delaware.gov 384s-wygj, Public Domain, weekly, two-year window): one row per Food Code section cited; DPH
  inspects every Delaware restaurant. No grade, score, placard or priority flag: we show sections cited, never a grade, never "critical".
  Names are "DBA - legal entity - #store" cut at 50 characters (`official.dph_name`); "(Closed)" marks a closure, and a DPH closure
  outranks a valid Revenue license (Iron Hill). Records through = fetch minus 7 days (`official.DPH_THROUGH`); future-dated rows dropped.
  DPH-only additions need an inspection after `official.DPH_STALE` (18 months).
- **Revenue licenses** (5zy2-grhr, Public Domain, daily): RETAILER  RESTAURANT; trade name shown, legal name never; points are zip
  centroids, so re-placed on Overture address points / Census geocoder. A license confirms a business, not that it's open.
- Not available: alcohol (OABCC has no public list), property values. No MICHELIN (no Bib filter). James Beard: La Fia (2026),
  Bardea (2022, 2025), One Coastal (finalist 2024); House of William & Merry closed July 2026.
- Calibration statewide vs DPH: Meta + Google-open 75.7%, Meta-only 39.5%, Foursquare-only 10.4%; app Meta ≥0.95 73.3%.

## Rebuild
```bash
.venv/bin/python pipeline/fetch_overture.py && .venv/bin/python pipeline/fetch_extras.py && .venv/bin/python pipeline/fetch_official.py
cd pipeline && ../.venv/bin/python geocode_official.py && ../.venv/bin/python geocode_census.py && ../.venv/bin/python listings.py \
  && ../.venv/bin/python calibrate.py && ../.venv/bin/python delaware.py && ../.venv/bin/python build_research.py \
  && ../.venv/bin/python delaware.py && DE_APP=1 ../.venv/bin/python delaware.py && cd ..
cp data/app/places.json DelawareEats/Resources/ && .venv/bin/python scripts/make-leaderboard.py
.venv/bin/python scripts/make-site.py && .venv/bin/python scripts/make-listing.py && .venv/bin/python scripts/qa-site.py \
  && .venv/bin/python scripts/publish_app_data.py
```
`official.py` reads the newest dated files in `data/raw/official/` (each fetch is a snapshot; DPH's window rolls). Website links:
`cd pipeline && CHECK_WORKERS=8 ../.venv/bin/python check_websites.py [--retry-transient]` (run in the background; back up
`data/de/website_check.json` before stopping one). Research: `pipeline/build_research.py` (evidence = a dated 2025-26 page or a 2025-26
DPH inspection; leads in `data/research/app/LEADS.md`). Most Delaware papers robots-block ClaudeBot (see 12-sources.md).

## App (`DelawareEats/`, SwiftUI, iOS 18+, XcodeGen)
- One data file: `Resources/places.json` holds the places and each one's detail ("detail"); OTA layout `.single`
  (`Services/AppDataLayout.swift`); `DataUpdates.swift` and `DataUpdatesTests.swift` are the shared copies (never edit).
- Share sends `explore/#p=<id>` (SHARE-LINK.md); `Links.onWeb` = `!isVenue`.
- Tests: `xcodegen generate`, then `xcodebuild test-without-building ... -only-testing:DelawareEatsTests` (47 pass 2026-10-28 on the iPad, 46 on the iPhone before the official-record test; ShareLinkTests
  need docs/data from make-site.py). NoGoogleDataTests scan every bundled key for google|rating|review|gmap|price|in21|closed21.
- UI tests (`-only-testing:DelawareEatsUITests`, signed, not `CODE_SIGNING_ALLOWED=NO`): 2026-10-28 on iOS 27.0, iPhone 17 Pro Max 6/6
  and iPad Pro 13" (M5) 6/6 (launch 4.9 s and 4.7 s). Under heavy load the iPad map never idles, and the 5-second
  "outside Delaware" flash can pass between steps: rerun that test alone on a quiet Mac. Tabs go through `tab()` (TabBar, else label + SF Symbol: iOS 27.1's iPhone
  Duo floats them in a rail), map layer chips through `layerChip()` (the row is wider than an iPhone; XCUITest throws on an off-screen
  chip's hittability). `testLaunchIsQuick` can fail just under its load gate (7.0 s at load 15.7): rerun it alone on a quiet Mac
  (4.9 s). A failing run starts `simctl diagnose` with a 600 s timeout: kill only ours (by its `--udid`).
- Screenshots (2026-10-28, iOS 27.0): `scripts/capture-screenshots.sh <udid> [screens]` (Debug build, `-screenshot <name>`;
  `OUT=$PWD/playbook/app-store/raw/<iphone|ipad> SLEEP=14` for the App Store set), then `scripts/appstore-screenshots.py` frames
  `playbook/app-store/iphone` (8, 1320×2868) and `ipad` (6, 2064×2752). The landing page uses `docs/screenshots` via
  `scripts/site-images.sh`, then make-site.py. Simulators are created for a run and deleted after it (none kept; `.simulators` empty).
  One simulator at a time; check `ps -u $(id -u) | wc -l` first.
- Listing: `scripts/make-listing.py` (after make-site.py) writes `playbook/06-app-store-listing.md`, `13-app-review-reply.md` and
  `app-store/listing.json` from `site-numbers.json`; `testBundledData` checks the two searches the reply promises.
- Both installed Xcodes are 27.1 (27A9269 beta, 27A9275): confirm a public release before any archive.

## Outward actions need Nick's explicit yes, every time
Public repo, pushes, Pages, App Store Connect, uploads, records requests, emails. Never submit for review. Support: nick@eatsranked.com.
Public commits use 329204362+nickstrom5@users.noreply.github.com. Keep `scripts/make-leaderboard.py`, `site/` and `data/` out of the
public repo.
