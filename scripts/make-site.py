"""Writes the public website in docs/ from the same data the app ships (data/app/places.json: the places and each one's detail, with
Revenue business licenses, phones, websites and DPH inspection histories).

Pages: the landing page; a statewide page for each hand-checked guide with at least four places (scrapple, Wilmington Italian,
farm creameries, brewpubs; the others once their research reaches four); James Beard honors; an explainer of the Division of Public
Health's inspection records (counts only, no place named); one page per town with enough hand-checked or honored places to say something
real, plus a cities index; the web app (/explore/); privacy; terms; 404; sitemap.xml, robots.txt, site.webmanifest and
playbook/site-numbers.json. Everything listed is hand-checked research or public records; nothing comes from Google, Yelp or any
ratings site, and nothing is ranked by ratings. Ported from oh-eats/scripts/make-site.py.

Rules the copy keeps (scripts/qa-site.py checks them):
- Every number is counted from the data here, never typed in. DPH's list includes establishments the map data doesn't, and not every
  establishment is a restaurant, so no sentence claims "every" or "all N" restaurants.
- "Checked" only for the hand-checked lists (`hc`, 2025-26 evidence for each place).
- Delaware has no official inspection grade, score or placard, and we compute none: the site shows the Food Code sections DPH cited at
  each place's latest routine inspection, with the date, and any later visit.
- The inspections page names no place at all and has no "most cited" list; no place is named in a title, description or lede for its
  inspections.
- Every page carries a hash-pinned Content-Security-Policy; inline scripts and styles are hashed after the page is final.

Usage (from de-eats/): .venv/bin/python scripts/make-site.py           (github.io address, BASE /delaware-eats)
                       DE_DOMAIN=delaware.eatsranked.com .venv/bin/python scripts/make-site.py   (once Nick's CNAME resolves)
Re-run it after every data rebuild, then check the pages with scripts/qa-site.py. Never hand-edit docs/*.html.
"""
import base64
import datetime as dt
import glob
import gzip
import hashlib
import html
import json
import math
import os
import re
import struct
import urllib.parse
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = f"{ROOT}/docs"
# Where the site lives. Until Nick's Cloudflare record (CNAME ohio -> nickstrom5.github.io, DNS only) resolves, GitHub Pages serves
# the project address. When `dig ohio.eatsranked.com` shows the CNAME, run with OH_DOMAIN=ohio.eatsranked.com and push: this
# writes docs/CNAME, and GitHub then forwards the old github.io links (the ones inside shipped app builds).
CUSTOM_DOMAIN = os.environ.get("DE_DOMAIN", "").strip().lower().removeprefix("https://").removeprefix("http://").strip("/")
REPO = "delaware-eats"
DOMAIN = f"https://{CUSTOM_DOMAIN}" if CUSTOM_DOMAIN else f"https://nickstrom5.github.io/{REPO}"
BASE = "" if CUSTOM_DOMAIN else f"/{REPO}"     # path prefix for root-relative links
BRAND = "Delaware Eats"
APP_NAME = "Delaware Eats: Restaurants"
TAGLINE = "scrapple, crabs & boardwalk"
EMAIL = "nick@eatsranked.com"   # Nick, 2026-10-12: the site's contact address (Cloudflare Email Routing)
PUBLISHED = "2026-10-27"        # the site's first publication (Article datePublished)
SITE_REV = "2026-10-27"         # the last change to this generator's own copy or code: bump it when you change the words
POLICY_UPDATED = "2026-10-27"   # privacy policy and terms: bump only when their text changes
PRIVACY_UPDATED = "2026-10-27"   # the privacy policy alone: the app’s data updates (OTA-DATA.md)
CHECKED = "fall 2026"
STORAGE_PREFIX = "deeats-"      # the web app's localStorage keys (other state sites share the nickstrom5.github.io origin)
# Delaware Eats is one of the Eats Ranked state sites: the hub (eatsranked.com) lists it as a subOrganization, and every page says so
# from this side too (the footer line and the Organization's parentOrganization), in Wisconsin's words.
HUB = {"@type": "Organization", "@id": "https://eatsranked.com/#organization", "name": "Eats Ranked", "url": "https://eatsranked.com/"}
ORG_ID = f"{DOMAIN}/#org"
# the site's Organization as other pages name it (author, publisher): the same @id as the full node on the landing page
ORG_REF = {"@type": "Organization", "@id": ORG_ID, "name": BRAND, "url": f"{DOMAIN}/",
           "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png", "width": 512, "height": 512}, "parentOrganization": HUB}

# ---------------------------------------------------------------- data: one file, the places and each one's detail
D = json.load(open(f"{ROOT}/data/app/places.json"))
assert D.get("generated"), "data/app/places.json has no 'generated' field: the pipeline hasn't finished writing it"
DETAIL_SRC = D.get("detail") or {}
assert DETAIL_SRC, "data/app/places.json has no detail"


def merged(r):
    """One place with its detail fields put back: the core's "in" is [routine count, routine date, last date, last count, last type];
    the detail's "in" is {n, h}."""
    det = DETAIL_SRC.get(r["id"]) or {}
    out = dict(r)
    ins = r.get("in")
    if isinstance(ins, list) and len(ins) >= 5:
        out["in"] = {"n_cited": ins[0], "d": ins[1], "ld": ins[2], "ln": ins[3], "lt": ins[4]}
    for k, v in det.items():
        if k == "in" and isinstance(v, dict):
            out["in"] = {**(out.get("in") or {}), **v}
        else:
            out[k] = v
    return out


RECS = [merged(r) for r in D["places"]]
TODAY = max(str(D.get("generated") or SITE_REV)[:10], SITE_REV)   # sitemap lastmod and dateModified move with the data or the copy
INS_THROUGH = (D.get("inspections_through") or {}).get("dph", "")
N_DPH = D.get("dph_live") or 0
N_REV = D.get("rev_licenses") or 0
CITIES, CUISINES, COUNTIES = D["cities"], D["cuisines"], D["counties"]
ITYPES = D.get("itypes") or ["Routine", "Follow-up", "Complaint"]
SECTIONS = D.get("sections") or {}
SCRAPPLE, BOARDWALK, CRAB, DUMPLINGS, ITALIAN, CREAMERY, BREWPUB, OLDEST = 1, 2, 4, 8, 16, 32, 64, 128
MI = ["", "MICHELIN Recommended", "Bib Gourmand", "1 MICHELIN Star", "2 MICHELIN Stars", "3 MICHELIN Stars"]   # Delaware: never set
DPH_URL = "https://data.delaware.gov/Health/Food-Establishment-Inspection-Violations/384s-wygj"
REV_URL = "https://data.delaware.gov/Licenses-and-Certifications/Delaware-Business-Licenses/5zy2-grhr"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
NUM_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def hdate(iso):
    """2026-09-24 -> September 24, 2026"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return f"{MONTHS[int(m[2]) - 1]} {int(m[3])}, {m[1]}" if m else str(iso or "")


def hmonth(iso):
    m = re.match(r"(\d{4})-(\d{2})", str(iso or ""))
    return f"{MONTHS[int(m[2]) - 1]} {m[1]}" if m else str(iso or "")


def plural(n, one, many=None):
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def words_num(n):
    return NUM_WORDS[n] if 0 <= n < len(NUM_WORDS) else f"{n:,}"


def safe_url(u):
    """Only http(s) links leave the site; a bare host ("example.com/menu") gets https://. Anything else is dropped."""
    u = str(u or "").strip()
    if re.fullmatch(r"https?://[^\s\"'<>\\]+", u, re.I):
        return u
    if re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}(?:[/?#][^\s\"'<>\\]*)?", u, re.I):
        return "https://" + u
    return ""


# Websites we must not link (pipeline/website_blocklist.json): hacked, expired or another business's site. A blocked link is
# dropped, never the place. qa-site.py fails if a blocked domain or URL appears anywhere in docs/.
BLOCKLIST = json.load(open(f"{ROOT}/pipeline/website_blocklist.json"))
for _b in BLOCKLIST:
    assert _b.get("match", "domain") in ("domain", "url") and (_b.get("url") or _b.get("domain")), f"bad blocklist entry {_b}"
BLOCKED_LINKS = []   # (place, link) pairs the blocklist dropped from this build


def url_key(u):
    """A URL compared without its scheme, a leading www., a trailing slash or letter case."""
    return re.sub(r"^(?:https?:)?//(?:www\.)?", "", str(u or "").strip().lower()).rstrip("/")


def blocked_site(u):
    host = (urllib.parse.urlsplit(u).hostname or "").rstrip(".").removeprefix("www.")
    for b in BLOCKLIST:
        if b.get("match", "domain") == "url":
            if url_key(u) == url_key(b.get("url") or b["domain"]):
                return b
        else:
            d = b["domain"].strip().lower().rstrip(".").removeprefix("www.")
            if host == d or host.endswith("." + d):
                return b
    return None


class P:
    """One place, with the same meaning the app gives each field (DelawareEats/Models/Place.swift)."""

    def __init__(self, r):
        self.r = r
        self.name = str(r["n"])
        self.city = CITIES[r["c"]] if r.get("c") is not None else ""
        self.county = COUNTIES[r["co"]] if r.get("co") is not None else None
        self.cuisine = CUISINES[r["cu"]] if r.get("cu") is not None else ""
        self.addr = (r.get("a") or "").strip().rstrip(",").strip()
        self.zip = str(r.get("z") or "")
        self.lat, self.lon = r.get("la"), r.get("lo")
        self.tags = r.get("g") or 0
        self.chain = (r.get("ch") or 0) >= 5
        self.venue = r.get("v") == 1
        self.ip = r.get("ip")
        self.founded = r.get("f") if isinstance(r.get("f"), int) else None
        self.fn = r.get("fn") or ""
        self.dishes = (r.get("dish") or "").replace("; ", ", ")
        self.season = r.get("seas") or ""
        self.note = r.get("note") or ""
        self.site = safe_url(r.get("w"))
        if self.site and blocked_site(self.site):
            BLOCKED_LINKS.append((self.name, self.site))
            self.site = ""   # the link goes, the place stays
        self.jbf = r.get("jbf") or ""
        self.h = r.get("h") or 0
        self.mi = r.get("mi") if r.get("mi") in range(1, len(MI)) else 0
        self.hc = r.get("hc") == 1   # hand-checked against a 2025-26 source; the only places the themed guides list
        self.lic = r.get("lic") or []   # the Revenue business license: [[source, license number, activity, valid through]]
        ins = r.get("in")
        # DPH's latest routine inspection (sections cited, date), and the latest visit of any type
        self.ins = ins if isinstance(ins, dict) and ins.get("ld") else None
        self.cited = self.ins.get("n_cited") if self.ins else None

    def featured_key(self):
        # the app's "Featured first": honored places, then documented founding year, then name
        return (-(self.ip if self.ip is not None else -1), self.founded or 9999, self.name.lower())

    def jb_label(self):
        return ("America's Classic" if self.h & 1 else "James Beard winner" if self.h & 2 else "James Beard finalist" if self.h & 4
                else "James Beard semifinalist" if self.h & 8 else None)

    def promo_ok(self):
        """A place named in a title, description, lede or other promotional spot: DPH publishes no grade, so this only keeps out a place
        DPH saw on a follow-up or complaint visit after its latest routine inspection (the record is still open, in a sense)."""
        return not self.ins or not self.ins.get("d") or self.ins.get("ld") <= self.ins.get("d")

    def in_guide(self, tag):
        return self.hc and bool(self.tags & tag)


PLACES = [P(r) for r in RECS]
REST = [p for p in PLACES if not p.venue]

ALL_GUIDES = [("scrapple", SCRAPPLE), ("italian", ITALIAN), ("creamery", CREAMERY), ("brewpub", BREWPUB), ("crab", CRAB), ("boardwalk", BOARDWALK),
              ("dumplings", DUMPLINGS)]
MIN_GUIDE = 4   # a guide gets its own page once its research has this many places (Idaho's rule); until then it's only in the web app
L_ALL = {k: sorted([p for p in REST if p.in_guide(t)], key=P.featured_key) for k, t in ALL_GUIDES}
GUIDE_TAGS = [(k, t) for k, t in ALL_GUIDES if len(L_ALL[k]) >= MIN_GUIDE]
L = {k: L_ALL[k] for k, _ in GUIDE_TAGS}
HON_L = sorted([p for p in REST if p.jbf], key=P.featured_key)
OLD_L = sorted([p for p in REST if p.founded and p.in_guide(OLDEST)], key=lambda p: (p.founded, p.name.lower()))
HAS_OLD = len(OLD_L) >= MIN_GUIDE
HC_ANY = [p for p in REST if p.hc and (p.tags & (SCRAPPLE | BOARDWALK | CRAB | DUMPLINGS | ITALIAN | CREAMERY | BREWPUB | OLDEST))]   # on a hand-checked guide
INS_L = [p for p in REST if p.ins and p.cited is not None]

# ---------------------------------------------------------------- regions: Delaware's three counties, north to south
REGION_ORDER = ["New Castle County", "Kent County", "Sussex County"]
REGION_NAME = {r: r for r in REGION_ORDER}
for p in PLACES:
    p.region = p.county if p.county in REGION_ORDER else None


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- html helpers
e = html.escape


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "").replace("&", "and")).strip("-")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def join_words(xs, conj="and"):
    xs = [x for x in xs if x]
    if len(xs) <= 1:
        return "".join(xs)
    return ", ".join(xs[:-1]) + f" {conj} " + xs[-1]


def fit(cands, lo, hi, what=""):
    seen = []
    # a description that misses the window by a few characters gets a fixed tail (state counts vary from build to build)
    more = [c.rstrip(".") + t for c in cands for t in (", with addresses and websites.", ". Free iPhone app coming soon.", ", with addresses.",
                                                         ". Free iPhone app.", ", with maps.")] if lo >= 100 else []
    for o in list(cands) + more:
        if lo <= len(o) <= hi:
            return o
        seen.append(o)
    raise ValueError(f"nothing fits {lo}-{hi} for {what}: {[(len(o), o) for o in seen[:12]]}")


# The app icon in miniature (scripts/make-brand.swift, same geometry): boardwalk fries in a paper cup on colonial blue.
LOGO = ('<svg viewBox="0 0 64 64" width="30" height="30" aria-hidden="true"><defs><clipPath id="lg-r"><rect width="64" height="64" rx="14"/></clipPath></defs>'
        '<g clip-path="url(#lg-r)"><rect width="64" height="64" fill="#1F3B6F"/>'
        '<rect x="15.74" y="19.2" width="4.99" height="18.88" rx="2.5" fill="#F2C14E"/><rect x="21.22" y="12.8" width="4.99" height="25.28" rx="2.5" fill="#F7D77F"/><rect x="26.69" y="8.96" width="4.99" height="29.12" rx="2.5" fill="#F2C14E"/><rect x="32.16" y="13.44" width="4.99" height="24.64" rx="2.5" fill="#F7D77F"/><rect x="37.63" y="10.24" width="4.99" height="27.84" rx="2.5" fill="#F2C14E"/><rect x="43.1" y="17.28" width="4.99" height="20.8" rx="2.5" fill="#F7D77F"/>'
        '<path d="M22.4 54.72L41.6 54.72L44.8 31.68L19.2 31.68Z" fill="#FBF6EC"/><path d="M21.25 40.32L42.75 40.32L42.18 47.04L21.82 47.04Z" fill="#F4A7A3"/></g></svg>')
FAVICON = "data:image/svg+xml," + LOGO.replace('width="30" height="30" ', "").replace(' aria-hidden="true"', "").replace("<svg ", "<svg xmlns='http://www.w3.org/2000/svg' ").replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")

# Nick's palette (2026-10-27): colonial blue and buff, the state colors. Blue #1f3b6f for text, headings and accents (10.9:1 on white),
# buff #e3c79a only as a fill under blue text (6.7:1), never as text on white; link blue #33558f; peach blossom #f4a7a3 for one dot on the
# header arc. The header element is the Twelve-Mile Circle, the arc of the northern border. Lettering: condensed heavy system faces for
# headings, the system monospaced face for numbers; no web fonts are loaded (the CSP allows only this site).
CSS = """
  :root {
    --bg: #f7f4ee; --surface: #fff; --surface2: #eee6d8; --rule: #e4ddd0;
    --ink: #13213d; --ink2: #1f3b6f; --muted: #56607a;
    --accent: #1f3b6f; --accent2: #33558f; --on-accent: #fff; --orange: #e3c79a; --on-orange: #1f3b6f; --lime: #e3c79a; --soft: #f5ebd9; --limesoft: #f5ebd9;
    --focus: #33558f;
    --radius: 16px;
    --display: "Avenir Next Condensed", "Helvetica Neue Condensed", "Roboto Condensed", "Arial Narrow", system-ui, sans-serif;
    --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0f1a30; --surface: #17243f; --surface2: #1f2f50; --rule: #2d3f63; --ink: #eef2f9; --ink2: #d6deec; --muted: #a9b6cc; --accent: #e3c79a; --accent2: #f0dcb8; --on-accent: #0f1a30; --focus: #e3c79a; }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  @media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
  a { color: var(--accent); text-underline-offset: 2px; }
  a:focus-visible, summary:focus-visible, button:focus-visible, select:focus-visible, input:focus-visible, [tabindex]:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; border-radius: 6px; }
  .skip { position: absolute; left: -9999px; top: 0; background: var(--orange); color: var(--on-orange); padding: 10px 14px; font-weight: 700; z-index: 10; }
  .skip:focus { left: 8px; top: 8px; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 20px; }
  header.site { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 0 14px; }
  .arc { position: relative; height: 18px; margin: 0 0 4px; overflow: hidden; }
  .arc::before { content: ""; position: absolute; left: -2%; right: -2%; top: 6px; height: 120px; border-top: 6px solid #e3c79a; border-radius: 50% 50% 0 0 / 22px 22px 0 0; }
  .arc::after { content: ""; position: absolute; right: 10px; top: 9px; width: 9px; height: 9px; border-radius: 50%; background: #f4a7a3; }
  .logo { display: flex; align-items: center; gap: 10px; font: 800 24px/1 var(--display); text-transform: uppercase; letter-spacing: .01em; color: var(--accent); text-decoration: none; }
  .logo svg { flex: 0 0 auto; border-radius: 7px; }
  header.site nav { display: flex; flex-wrap: wrap; gap: 4px 16px; justify-content: flex-end; }
  header.site nav a { color: var(--ink2); text-decoration: none; font-size: 15px; }
  header.site nav a:hover { color: var(--accent); text-decoration: underline; }
  h1, h2 { font-family: var(--display); font-weight: 800; color: var(--accent); letter-spacing: -.005em; }
  h1 { font-size: clamp(40px, 8.5vw, 64px); line-height: .95; margin: 0 0 18px; text-transform: uppercase; overflow-wrap: break-word; text-shadow: 3px 3px 0 var(--orange); }
  .kicker { font: 600 13px/1.4 var(--mono); letter-spacing: .04em; text-transform: uppercase; color: var(--accent); margin: 0 0 12px; }
  .kicker::before { content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--orange); margin: 0 8px 1px 0; }
  h2 { font-size: 34px; line-height: 1.02; margin: 0 0 10px; text-transform: uppercase; }
  h3 { font-size: 18px; margin: 0; line-height: 1.3; }
  .lede { font-size: 19px; color: var(--ink2); margin: 0 0 26px; }
  .hero { padding: 44px 0 28px; }
  section { padding: 36px 0; border-top: 1px solid var(--rule); }
  section.hero { border: 0; }
  .sub { color: var(--ink2); margin: 0 0 22px; }
  .cta-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  .btn { display: inline-flex; align-items: center; gap: 10px; background: var(--orange); color: var(--on-orange); font-weight: 700; padding: 14px 20px; border-radius: 14px; text-decoration: none; font-size: 17px; }
  .btn-ghost { background: transparent; color: var(--accent); border: 2px solid var(--accent); }
  .pill { font-size: 14px; color: var(--muted); }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 28px 0 0; padding: 0; list-style: none; }
  .stats li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px; }
  .stats b { display: block; font: 600 28px/1 var(--mono); color: var(--accent); }
  .stats span { font-size: 14px; color: var(--muted); }
  .steps { display: grid; gap: 12px; list-style: none; margin: 0; padding: 0; }
  .step { display: flex; gap: 14px; background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .step .n { flex: 0 0 32px; height: 32px; border-radius: 50%; background: var(--orange); color: var(--on-orange); font-weight: 800; display: grid; place-items: center; }
  .step p { margin: 4px 0 0; color: var(--ink2); }
  .shots { display: flex; gap: 14px; overflow-x: auto; margin: 0 -20px; padding: 4px 20px 14px; scroll-snap-type: x proximity; list-style: none; }
  .shots li { flex: 0 0 auto; width: 210px; scroll-snap-align: start; }
  .shots img { display: block; width: 210px; height: auto; border-radius: 24px; border: 1px solid var(--rule); background: var(--surface2); }
  .shots p { font-size: 14px; color: var(--muted); margin: 8px 2px 0; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card { background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .card h3 { font: 800 21px/1.1 var(--display); text-transform: uppercase; letter-spacing: .01em; }
  a.card.gc { display: flex; flex-direction: column; gap: 6px; border: 0; border-radius: 18px; min-height: 150px; }
  a.card.gc b { font: 600 32px/1 var(--mono); margin-bottom: auto; }
  a.card.gc p, a.card.gc h3 { color: inherit; }
  a.card.gc p { opacity: .92; }
  a.card.gc.gc-scrapple, a.card.gc.gc-italian, a.card.gc.gc-creamery, a.card.gc.gc-brewpub, a.card.gc.gc-crab, a.card.gc.gc-boardwalk, a.card.gc.gc-dumplings { background: #e3c79a; color: #1f3b6f; }
  a.card.gc.gc-oldest, a.card.gc.gc-honors { background: #1f3b6f; color: #fff; }
  .card p { margin: 6px 0 0; color: var(--ink2); }
  a.card { display: block; text-decoration: none; color: var(--ink); }
  a.card:hover h3 { text-decoration: underline; color: var(--accent); }
  .cities { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; margin: 0; }
  .cities a { display: inline-block; padding: 8px 12px; border-radius: 999px; border: 1px solid var(--rule); background: var(--surface); text-decoration: none; color: var(--ink); font-size: 15px; }
  .cities a:hover { border-color: var(--accent); }
  .cities a[aria-current] { border-color: var(--accent); font-weight: 700; }
  details { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 2px 18px; margin-bottom: 10px; }
  summary { cursor: pointer; padding: 14px 0; font-weight: 600; list-style: none; display: flex; justify-content: space-between; gap: 12px; }
  summary::-webkit-details-marker { display: none; }
  summary::after { content: "+"; color: var(--accent); font-weight: 800; }
  details[open] summary::after { content: "\\2013"; }
  details p { margin: 0 0 16px; color: var(--ink2); }
  .final { text-align: center; }
  .final .cta-row { justify-content: center; }
  nav.crumbs { font-size: 14px; color: var(--muted); padding: 16px 0 0; }
  nav.crumbs ol { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
  nav.crumbs li + li::before { content: "/"; margin-right: 6px; color: var(--rule); }
  nav.crumbs a { color: var(--muted); }
  .places { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }
  .places li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px 16px; min-width: 0; overflow-wrap: anywhere; scroll-margin-top: 12px; }
  .places li:target { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent); }
  .places .where { margin: 2px 0 0; font-size: 15px; color: var(--muted); }
  .places .facts { margin: 8px 0 0; font-size: 15px; color: var(--ink2); }
  .places .facts b { color: var(--ink); font-weight: 600; }
  .places .note { margin: 6px 0 0; font-size: 15px; color: var(--ink2); }
  .places .fine { margin: 6px 0 0; }
  .places .link { font-size: 14px; margin: 6px 0 0; }
  .tag { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; background: var(--lime); color: #1f3b6f; border-radius: 6px; padding: 1px 6px; margin: 0 4px 2px 0; }
  .tag-mi { background: #b4544e; color: #fff; }
  .tag-jb { background: #1f3b6f; color: #fff; }
  .tag-plain { background: var(--soft); color: #1f3b6f; }
  .toc { columns: 2; padding-left: 20px; margin: 0; }
  table { border-collapse: collapse; width: 100%; font-size: 15px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--rule); vertical-align: top; }
  td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
  .tbl { overflow-x: auto; }
  .res { display: inline-block; font: 800 12px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .04em; text-transform: uppercase; padding: 2px 6px; border-radius: 6px; }
  .res-n { background: #eee6d8; color: #1f3b6f; }
  .groups { list-style: none; padding: 0; margin: 0 0 18px; display: grid; gap: 12px; }
  .groups > li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px 16px; }
  .groups ul { margin: 8px 0 0; padding-left: 20px; color: var(--ink2); font-size: 15px; }
  .groups .count { margin: 8px 0 0; font-weight: 600; }
  .fine { font-size: 14px; color: var(--muted); }
  .legal h2 { font-size: 26px; margin-top: 28px; }
  .legal p, .legal li { color: var(--ink2); }
  footer { padding: 32px 0 56px; color: var(--muted); font-size: 14px; border-top: 1px solid var(--rule); margin-top: 20px; }
  footer nav { display: flex; flex-wrap: wrap; gap: 8px 16px; }
  footer a { color: var(--muted); }
  footer p { margin: 12px 0 0; }
  @media (max-width: 600px) {
    .grid2 { grid-template-columns: 1fr; }
    .stats { grid-template-columns: 1fr 1fr; }
    .toc { columns: 1; }
    .toc a { display: inline-block; padding: 3px 0; }
    header.site { flex-direction: column; align-items: flex-start; }
    header.site nav { justify-content: flex-start; }
    header.site nav a, footer nav a, nav.crumbs a { display: inline-block; padding: 10px 0; }
    footer nav { gap: 0 18px; }
    th, td { padding: 8px 4px; font-size: 14px; }
    .tbl th, .tbl td { padding: 8px 3px; font-size: 13px; }
    .res { font-size: 11px; letter-spacing: .02em; padding: 2px 4px; }
    nav.crumbs ol { align-items: center; }
  }
"""


def jsonld(obj):
    big = obj.get("@type") == "ItemList"
    raw = json.dumps(obj, ensure_ascii=False, indent=None if big else 1, separators=(",", ":") if big else None)
    return '<script type="application/ld+json">\n' + raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026") + "\n</script>"


def crumbs(trail):
    """trail: [(name, url)] ending with the current page."""
    items = "".join(f'<li><a href="{u}">{e(n)}</a></li>' if i < len(trail) - 1 else f'<li aria-current="page">{e(n)}</li>'
                    for i, (n, u) in enumerate(trail))
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(trail)]}
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{items}</ol></nav>', ld


def store_button(label="Ask for early access"):
    # A plain mailto button until launch: no Apple logo (Apple's marketing rules allow it only in the official badge). When
    # APP_STORE_URL is set in page() below, swap this for Apple's "Download on the App Store" badge artwork. Only Nick's internal
    # TestFlight group exists (2026-10-13): the mailto asks, and no page copy promises an invite or a link.
    return (f'<a class="btn store-btn" href="mailto:{EMAIL}?subject=Delaware%20Eats%20early%20access&amp;body=Send%20me%20the%20TestFlight%20link.">'
            f'<span class="store-label">{label}</span></a>')


STORE_NOTE = "The free Delaware Eats app for iPhone and iPad is on its way to the App Store."


def sha256_src(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() + "'"


def csp_for(doc):
    """A strict policy for one finished page: only its own inline <script>/<style> blocks (by hash), same-origin data and images."""
    scripts = re.findall(r"<script>(.*?)</script>", doc, re.S)          # executable inline scripts (JSON-LD blocks are data, not run)
    styles = re.findall(r"<style>(.*?)</style>", doc, re.S)
    return ("default-src 'none'; "
            f"script-src {' '.join(sha256_src(s) for s in scripts) or chr(39) + 'none' + chr(39)}; "
            f"style-src {' '.join(sha256_src(s) for s in styles) or chr(39) + 'none' + chr(39)}; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'none'")


CSP_SLOT = "__CSP__"
written, noindexed = [], []
NAV = [("/delaware-scrapple.html", "Scrapple"), ("/wilmington-italian.html", "Italian"), ("/delaware-farm-creameries.html", "Creameries"),
       ("/cities/", "Cities"), ("/explore/", "Search")]


def page(path, title, desc, body, lds=(), robots="index,follow,max-image-preview:large", og_alt=None, extra_css="", og_type="article"):
    assert 50 <= len(title) <= 60 or path == "404.html", (path, len(title), title)
    assert 140 <= len(desc) <= 160 or path == "404.html", (path, len(desc), desc)
    assert body.count("<h1") == 1, path
    assert 'style="' not in body, f"{path}: inline style attributes break the CSP"
    url = DOMAIN + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))
    indexed = "noindex" not in robots
    if not any("parentOrganization" in json.dumps(x) for x in lds):   # every page names its publisher and the Eats Ranked parent
        lds = list(lds) + [{"@context": "https://schema.org", **ORG_REF}]
    og_alt = og_alt or f"{BRAND}: {TAGLINE}. Delaware restaurants, with hand-checked scrapple, crab houses and boardwalk standbys."
    ld = "\n".join(jsonld(x) for x in lds)
    canon = f'<link rel="canonical" href="{url}">\n' if indexed else ""
    og_url = f'<meta property="og:url" content="{url}">\n' if indexed else ""
    nav = "\n".join(f'      <a href="{u}">{t}</a>' for u, t in NAV)
    doc = f"""<!DOCTYPE html>
<html lang="en" data-base="{BASE}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{CSP_SLOT}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{canon}<meta name="robots" content="{robots}">
<meta name="theme-color" content="#1f3b6f">
<!-- Smart App Banner: once the App Store Connect record exists, replace APP_ID with the numeric Apple ID and uncomment.
<meta name="apple-itunes-app" content="app-id=APP_ID">
-->
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
{og_url}<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:locale" content="en_US">
<meta property="og:image" content="{DOMAIN}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{DOMAIN}/og.png">
<link rel="icon" type="image/svg+xml" href="{FAVICON}">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<style>{CSS}{extra_css}</style>
{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap">
  <header class="site">
    <a class="logo" href="/" aria-label="{BRAND} home">{LOGO}{BRAND}</a>
    <nav aria-label="Main">
{nav}
    </nav>
  </header>
  <div class="arc" aria-hidden="true"></div>
{body}
  <footer>
    <nav aria-label="Footer">
      <a href="/">{BRAND} app</a>
      <a href="/explore/">Search Delaware restaurants</a>
{chr(10).join(f'      <a href="{u}">{e(t)}</a>' for u, t in GUIDE_LINKS)}
      <a href="/cities/">Cities and towns</a>
      <a href="/privacy.html">Privacy policy</a>
      <a href="/terms.html">Terms of use</a>
      <a href="mailto:{EMAIL}">Email us</a>
    </nav>
    <p>{SOURCES_LINE}</p>
    <p>© 2026 {BRAND}. Part of <a href="{HUB['url']}" rel="noopener">Eats Ranked</a>, restaurant apps state by state.</p>
    <p>Created by <a href="https://work-with-nick.com/" rel="author">Nick Soderstrom</a>.</p>
  </footer>
</div>
<script>
  // Once the App Store listing exists, paste its URL here (looks like https://apps.apple.com/app/id123456789).
  // Every button switches from "Ask for early access" to "Download on the App Store" automatically (then use Apple's badge artwork,
  // see store_button() in scripts/make-site.py). Also fill in the apple-itunes-app meta tag in <head> on every page, and put the
  // MobileApplication "offers" back in the landing page's JSON-LD (re-run scripts/make-site.py after editing it there).
  var APP_STORE_URL = "";
  if (APP_STORE_URL) {{
    document.querySelectorAll(".store-btn").forEach(function (b) {{ b.href = APP_STORE_URL; b.rel = "noopener"; }});
    document.querySelectorAll(".store-label").forEach(function (l) {{ l.textContent = "Download on the App Store"; }});
    document.querySelectorAll(".store-note").forEach(function (n) {{ n.textContent = "Free for iPhone and iPad."; }});
  }}
</script>
</body>
</html>
"""
    if BASE:   # served under /delaware-eats/: every root-relative link and asset gets the prefix
        doc = re.sub(r'(href|src|srcset)="/', rf'\1="{BASE}/', doc)
    doc = doc.replace(CSP_SLOT, csp_for(doc), 1)   # hashed last, over the exact bytes the browser will see
    os.makedirs(os.path.dirname(f"{DOCS}/{path}"), exist_ok=True)
    open(f"{DOCS}/{path}", "w").write(doc)
    (written if indexed else noindexed).append(path)
    return path


class Anchors:
    """Gives each place an id (name-zip) the first time it appears on a page, so ItemList items can point to page#id."""
    RESERVED = {"main", "about", "list", "honors", "oldest", "inspections", "cuisines", "more", "towns", "how", "what", "guides", "cities",
                "faq", "download", "screens", "pricing", "privacy", "groups", "counties", "lookup", "closures", "tiers", "lg-r", "lg-f", "lg-p",
                "cities-list", "inspections-col"} | {k for k, _ in ALL_GUIDES}

    def __init__(self, page_url):
        self.page_url, self.used, self.of = page_url, set(self.RESERVED), {}

    def take(self, p):
        if id(p) in self.of:
            return None
        base = slug(p.name + (" " + p.zip if p.zip else "")) or "place"
        a, n = base, 2
        while a in self.used:
            a, n = f"{base}-{n}", n + 1
        self.used.add(a)
        self.of[id(p)] = a
        return a

    def url(self, p):
        return f"{self.page_url}#{self.of[id(p)]}"


CHIPS = [(SCRAPPLE, "Scrapple"), (ITALIAN, "Wilmington Italian"), (CREAMERY, "Farm creamery"), (BREWPUB, "Brewpub"),
         (CRAB, "Crab house & seafood"), (BOARDWALK, "Boardwalk classic"), (DUMPLINGS, "Slippery dumplings")]


def place_item(p, anchors=None, show_fn=False, honors=False):
    facts = []
    if p.dishes:
        facts.append(f"<b>On the menu:</b> {e(p.dishes)}")
    if p.founded:
        facts.append(f"<b>Since</b> {e(str(p.founded))}")
    if p.season:
        facts.append(f"<b>Season:</b> {e(p.season)}")
    kinds = []
    if p.mi:
        kinds.append(('<span class="tag tag-mi">', e(MI[p.mi])))
    if p.jb_label():
        kinds.append(('<span class="tag tag-jb">', e(p.jb_label())))
    if p.hc:
        kinds += [('<span class="tag">', k) for t, k in CHIPS if p.tags & t]
    where = ", ".join(x for x in (p.addr, p.city) if x)
    aid = anchors.take(p) if anchors else None
    out = [f'<li id="{e(aid)}">' if aid else "<li>", f"<h3>{e(p.name)}</h3>", f'<p class="where">{e(where)}</p>']
    if kinds or facts:
        out.append('<p class="facts">' + "".join(f"{tag}{k}</span>" for tag, k in kinds) + (" " + " · ".join(facts) if facts else "") + "</p>")
    if p.note:
        out.append(f'<p class="note">{e(p.note)}</p>')
    if show_fn and p.fn:
        out.append(f'<p class="fine">{e(p.fn)}</p>')
    if honors and p.jbf:   # restaurateur-level honors have no chip, so say what the honor is
        out.append('<p class="fine">' + e("; ".join("James Beard: " + x for x in p.jbf.split("; "))) + "</p>")
    if p.site:
        host = re.sub(r"^https?://(www\.)?", "", p.site, flags=re.I).split("/")[0]
        out.append(f'<p class="link"><a href="{e(p.site)}" rel="noopener nofollow">{e(host)}</a></p>')
    out.append("</li>")
    return "".join(out)


def restaurant_ld(p, item_url):
    addr = {"@type": "PostalAddress"}
    if p.addr:
        addr["streetAddress"] = p.addr
    if p.city:
        addr["addressLocality"] = p.city
    addr["addressRegion"] = "DE"
    if p.zip:
        addr["postalCode"] = p.zip
    addr["addressCountry"] = "US"
    x = {"@type": "Restaurant", "name": p.name, "url": item_url, "address": addr}
    if p.lat is not None and p.lon is not None:
        x["geo"] = {"@type": "GeoCoordinates", "latitude": p.lat, "longitude": p.lon}
    if p.site:
        x["sameAs"] = p.site
    if p.founded:
        x["foundingDate"] = str(p.founded)
    if p.cuisine and p.cuisine not in ("Other", "Restaurant", "American & Other"):
        x["servesCuisine"] = p.cuisine
    return x


def item_list(name, places, url, anchors):
    """An all-on-one-page list: each item's url is its anchor on this page; the restaurant's own site goes in sameAs."""
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "url": url, "numberOfItems": len(places),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": restaurant_ld(p, anchors.url(p))} for i, p in enumerate(places)]}


def article_ld(url, headline, desc):
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "description": desc,
            "datePublished": PUBLISHED, "dateModified": TODAY, "inLanguage": "en", "mainEntityOfPage": url,
            "image": f"{DOMAIN}/og.png", "author": ORG_REF, "publisher": ORG_REF}


# ---------------------------------------------------------------- counts shared by several pages
N_REST = len(REST)
N_TOWNS = len({p.city for p in REST if p.city})
N_COUNTIES = len({p.county for p in REST if p.county})
N_OFFICIAL = sum(1 for p in REST if p.r.get("t") == 2)
N_HC = len(HC_ANY)
N_JBF = sum(1 for p in HON_L if p.jbf)
N_CLASSICS = sum(1 for p in HON_L if p.h & 1)
INS_N = len(INS_L)
CITED_N = Counter(min(p.cited, 10) for p in INS_L)   # sections cited at the latest routine inspection (10 = 10 or more)
INS_PATH = "delaware-restaurant-inspections.html"
HON_PATH = "delaware-james-beard-restaurants.html"
OLD_PATH = "delaware-oldest-restaurants.html"
GUIDE_PATH = {"scrapple": "delaware-scrapple.html", "italian": "wilmington-italian.html", "creamery": "delaware-farm-creameries.html",
              "brewpub": "delaware-brewpubs.html", "crab": "delaware-crab-houses.html", "boardwalk": "rehoboth-boardwalk-classics.html",
              "dumplings": "sussex-slippery-dumplings.html"}
GUIDE_NAME = {"scrapple": "Scrapple", "italian": "Wilmington Italian", "creamery": "Farm creameries", "brewpub": "Brewpubs",
              "crab": "Crab houses & seafood", "boardwalk": "Boardwalk classics", "dumplings": "Slippery dumplings"}
GUIDE_LINKS = ([("/" + GUIDE_PATH[k], GUIDE_NAME[k]) for k, _ in GUIDE_TAGS]
               + ([("/" + OLD_PATH, "Oldest restaurants")] if HAS_OLD else [])
               + [("/" + HON_PATH, "James Beard honors"), ("/" + INS_PATH, "Health inspections")])
for _k in ("scrapple", "italian", "creamery"):   # the header nav links these three pages
    assert _k in L, f"the {_k} guide has fewer than {MIN_GUIDE} places: fix NAV"
INS_DATE = hdate(INS_THROUGH)

SOURCES_LINE = (f"Place data: hand-checked research by {BRAND} ({CHECKED}); inspection records from the Delaware Division of Public Health, "
                "Office of Food Protection (Food Establishment Inspection Violations, data.delaware.gov, public domain) and business licenses from "
                "the Delaware Division of Revenue (Delaware Business Licenses, data.delaware.gov, public domain); Overture Maps Foundation places "
                "(CDLA Permissive 2.0); map outlines © Overture Maps Foundation and OpenStreetMap contributors (ODbL). Not affiliated with or "
                "endorsed by the State of Delaware, the Division of Public Health, the Division of Revenue, any restaurant or chain, or the James "
                "Beard Foundation. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Places open and "
                "close, so check before you go.")


def by_region(places, key=lambda p: (p.city, p.name.lower())):
    groups = defaultdict(list)
    for p in places:
        groups[p.region or "Elsewhere"].append(p)
    order = REGION_ORDER + ["Elsewhere"]
    return [(REGION_NAME.get(r, "Elsewhere in Delaware"), sorted(groups[r], key=key)) for r in order if groups.get(r)]


def region_sections(places, noun, plural_noun, anchors, **item_kw):
    toc = '<ul class="toc">' + "".join(f'<li><a href="#{slug(r)}">{e(r)}</a> ({len(ps)})</li>' for r, ps in by_region(places)) + "</ul>"
    secs = []
    for r, ps in by_region(places):
        anchors.used.update({slug(r), "h-" + slug(r)})
        secs.append(f'<section id="{slug(r)}" aria-labelledby="h-{slug(r)}"><h2 id="h-{slug(r)}">{e(r)}</h2>'
                    f'<p class="sub">{plural(len(ps), noun, plural_noun)}, by town.</p><ol class="places">'
                    + "".join(place_item(p, anchors, **item_kw) for p in ps) + "</ol></section>")
    return toc, "\n".join(secs)


# ---------------------------------------------------------------- city pages: which towns get one
CITY_WANTED = ["Wilmington", "Newark", "Dover", "Lewes", "Rehoboth Beach", "Middletown", "Milford", "Smyrna", "Georgetown", "Bethany Beach",
               "Dewey Beach", "Fenwick Island", "Hockessin", "Seaford", "New Castle", "Milton"]
MIN_LISTED = 5   # hand-checked, honored or oldest places in the town itself: fewer, and the town gets no page yet


def town_listed(c):
    return [p for p in REST if p.city == c and ((p.hc and p.tags) or p.mi or p.jbf)]


CITY_PAGES = [c for c in CITY_WANTED if any(p.city == c and p.lat is not None for p in REST) and len(town_listed(c)) >= MIN_LISTED]
CITY_SKIPPED = {c: len(town_listed(c)) for c in CITY_WANTED if c not in CITY_PAGES}


def city_url(c):
    return f"/cities/{slug(c)}.html"


def city_links(current=None):
    return '<ul class="cities">' + "".join(f'<li><a href="{city_url(c)}"{" aria-current=" + chr(34) + "page" + chr(34) if c == current else ""}>{e(c)}</a></li>'
                                           for c in CITY_PAGES) + "</ul>"


def other_guides(skip):
    return "Other guides: " + ", ".join(f'<a href="{u}">{e(t)}</a>' for u, t in GUIDE_LINKS if u != skip) + "."


def guide_page(path, h1, kicker, title_opts, desc_opts, lede, about_html, places, noun, plural_noun, list_name, region=True, **item_kw):
    url = f"{DOMAIN}/{path}"
    # counts are small or large enough that the written lengths can miss the 140-160 window: each option also gets fixed tails
    tails = (", with addresses and websites.", ", with each place's address and website.", ". Free iPhone app coming soon.", ", with addresses.",
             ". Free iPhone app.", ", with maps.")
    desc_opts = list(desc_opts) + [d.rstrip(".") + t for d in desc_opts for t in tails]
    title_opts = list(title_opts) + [t + f" | {BRAND}" for t in title_opts if BRAND not in t]
    title, desc = fit(title_opts, 50, 60, path + " title"), fit(desc_opts, 140, 160, path + " description")
    nav, bc = crumbs([("Home", "/"), (h1, "/" + path)])
    anchors = Anchors(url)
    if region:
        toc, secs = region_sections(places, noun, plural_noun, anchors, **item_kw)
        jump = f"<h2>Jump to a region</h2>\n    {toc}"
    else:
        secs = (f'<section id="list" aria-labelledby="h-list"><h2 id="h-list">Oldest first</h2><ol class="places">'
                f'{"".join(place_item(p, anchors, **item_kw) for p in places)}</ol></section>')
        jump = ""
    body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{kicker}</p>
    <h1>{e(h1)}</h1>
    <p class="lede">{lede}</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">{STORE_NOTE}</span></div>
  </section>
  <section id="about">
    {about_html}
    <p class="fine">{other_guides("/" + path)} City pages: {", ".join(f'<a href="{city_url(c)}">{e(c)}</a>' for c in CITY_PAGES)}.</p>
    {jump}
  </section>
{secs}
  </main>"""
    page(path, title, desc, body, [article_ld(url, h1, desc), bc, item_list(list_name, places, url, anchors)])


def towns_text(places, k):
    return join_words([t for t, _ in Counter(p.city for p in places).most_common(k)])


def towns_counts(places, k=8):
    return ", ".join(f"{t} ({n})" for t, n in Counter(p.city for p in places).most_common(k))


def top_dishes(places, k=6, skip=()):
    c = Counter()
    for p in places:
        # sorted: a set's order changes from run to run, and ties in most_common() would reorder the copy on every rebuild
        for d in sorted({x.strip().lower() for x in re.split(r"[;,]", p.r.get("dish") or "") if x.strip()}):
            if d not in skip:
                c[d] += 1
    return ", ".join(f"{d} ({n})" for d, n in c.most_common(k) if n > 1)


HOW_BUILT = ("Our method: a place made the list only if a page names it for this food (the Cape Gazette, Delaware's or Greater "
             "Wilmington's tourism office, or the place's own site) and something from 2025 or 2026 shows it's open: a dated page, or a "
             "2025–26 inspection by the Division of Public Health. Its street address had to match our records. Review sites played no part, "
             "and places run by county and town rather than by anybody's score. Hours change, so check before you go.")
APP_LINE = (f"On your phone, {BRAND} orders this list by how far each place is from you, and a tap opens Apple Maps' live card with "
            "hours, photos and directions.")


def checked_kicker():
    return f"{BRAND} · checked by hand, {CHECKED}"


def seasonal_line(places):
    n = sum(1 for p in places if p.season)
    return f" {plural(n, 'place')} on this list {'notes a season' if n == 1 else 'note a season'}; seasonal is not closed." if n else ""


# ---------------------------------------------------------------- the themed guides
assert all(len(v) > 1 for v in L.values()), "the guide copy writes plural nouns"


def guide(k, h1, titles, descs, lede, about, list_name, noun="place"):
    G = L[k]
    plural_noun = noun[:-1] + "ies" if noun.endswith("y") and noun[-2] not in "aeiou" else noun + "s"
    guide_page(GUIDE_PATH[k], h1, checked_kicker(), titles, descs, lede, about + f"""
    <h2>The list at a glance</h2>
    <p>Towns with the most: {e(towns_counts(G))}.{(" The dishes we found most often: " + e(top_dishes(G)) + ".") if top_dishes(G) else ""}</p>
    <p>{HOW_BUILT}</p>
    <p>{APP_LINE}</p>""", G, noun, plural_noun, list_name)


GUIDE_DEFS = {
    "scrapple": ("Where to eat scrapple in Delaware",
                 [lambda n: f"Where to Eat Scrapple in Delaware: {n} Checked Places", lambda n: f"Delaware Scrapple: {n} Hand-Checked Places | {BRAND}"],
                 [lambda n: f"{plural(n, 'Delaware place')} serving scrapple, the fried pork-and-cornmeal breakfast slice, each checked in {CHECKED} against a 2025–26 source, by county.",
                  lambda n: f"Scrapple in Delaware: {plural(n, 'diner, tavern and brunch spot')} that put it on the plate, each checked in {CHECKED} against a 2025–26 source."],
                 lambda n: f"{plural(n, 'place')} serving scrapple, Delaware's breakfast meat, from a Smyrna sausage house to Wilmington brunch menus, each checked in {CHECKED} against a 2025–26 source.",
                 """<h2>Pork, cornmeal and a hot griddle</h2>
    <p>Scrapple is pork scraps and trimmings cooked down with cornmeal and spices, set in a loaf, sliced thin and fried crisp. Sussex County is home to RAPA Scrapple in Bridgeville, and Bridgeville's Apple-Scrapple Festival celebrates it every October. Breakfast is its natural home, but brunch kitchens now put it in cheesesteaks, Benedicts and bao buns.</p>""",
                 "Where to eat scrapple in Delaware", "place"),
    "italian": ("Wilmington Italian",
                [lambda n: f"Wilmington Italian Restaurants: {n} Checked Places", lambda n: f"Italian in Wilmington: {n} Checked Places"],
                [lambda n: f"{plural(n, 'Wilmington place')} for red-sauce dining rooms and Tuscan cooking, from Little Italy to Trolley Square, each checked in {CHECKED} against a 2025–26 source.",
                 lambda n: f"Wilmington Italian: {plural(n, 'restaurant')} in and around Little Italy, each checked in {CHECKED} against a 2025–26 source."],
                lambda n: f"{plural(n, 'place')} for Wilmington's Italian table, from Little Italy's dining rooms to Trolley Square, each checked in {CHECKED} against a 2025–26 source.",
                """<h2>Little Italy and beyond</h2>
    <p>Wilmington's Little Italy grew up around St. Anthony of Padua on the city's west side, and its family restaurants still draw diners from across the region. Wilmington is also where Capriotti's sandwich shops began, in 1976; its branches are in the web search, while this list holds places we checked by hand.</p>""",
                "Wilmington Italian", "place"),
    "creamery": ("Delaware farm creameries",
                 [lambda n: f"Delaware Farm Creameries: {n} Checked Ice Cream Stops", lambda n: f"Farm Creameries in Delaware: {n} Checked | {BRAND}"],
                 [lambda n: f"{plural(n, 'Delaware creamery', 'Delaware creameries')} scooping ice cream made from their own farms' milk, from Hockessin to Lewes, each checked in {CHECKED} against a 2025–26 source.",
                  lambda n: f"Farm ice cream in Delaware: {plural(n, 'creamery', 'creameries')} on dairy farms and at the university farm, each checked in {CHECKED} against a 2025–26 source."],
                 lambda n: f"{plural(n, 'creamery', 'creameries')} scooping ice cream made from their own farms' milk, each checked in {CHECKED} against a 2025–26 source.",
                 """<h2>From the farm's own herd</h2>
    <p>Delaware's farm creameries make their ice cream where the milk comes from: a family farm in Hockessin, dairy farms in Lewes and Bridgeville, and the University of Delaware's own farm in Newark, whose seasonal 1st State Cobbler is peach, the state's fruit. Several close for the winter or keep short hours off season.</p>""",
                 "Delaware farm creameries", "creamery"),
    "brewpub": ("Delaware brewpubs",
                [lambda n: f"Delaware Brewpubs: {n} Breweries With a Kitchen | {BRAND}", lambda n: f"Brewpubs in Delaware: {n} Hand-Checked | {BRAND}"],
                [lambda n: f"{plural(n, 'Delaware brewery')} that pour their own beer with a full kitchen, from Rehoboth and Lewes to Middletown, each checked in {CHECKED} against a 2025–26 source.",
                 lambda n: f"Delaware brewpubs: {plural(n, 'brewery')} serving their own beer with food, each checked in {CHECKED} against a 2025–26 source, by county."],
                lambda n: f"{plural(n, 'brewery')} that pour their own beer alongside a full kitchen, each checked in {CHECKED} against a 2025–26 source.",
                """<h2>Beer with dinner</h2>
    <p>Delaware's brewing scene took off at the beach: Dogfish Head opened its Rehoboth Beach brewpub in 1995, and the coast now has a cluster of breweries with kitchens. This list keeps to places with a full menu, not taprooms that rely on food trucks.</p>""",
                "Delaware brewpubs", "brewery"),
    "crab": ("Delaware crab houses & seafood",
             [lambda n: f"Delaware Crab Houses & Seafood: {n} Checked Places | {BRAND}"],
             [lambda n: f"{plural(n, 'Delaware place')} for steamed crabs, crab cakes and oysters, each checked in {CHECKED} against a 2025–26 source, by county and town."],
             lambda n: f"{plural(n, 'place')} for steamed blue crabs, crab cakes and oysters, each checked in {CHECKED} against a 2025–26 source.",
             """<h2>Crabs by the dozen</h2>
    <p>Blue crabs from the Delaware Bay and the Inland Bays, steamed with seasoning and cracked at paper-covered tables. Prices and supply move with the season.</p>""",
             "Delaware crab houses and seafood", "place"),
    "boardwalk": ("Boardwalk classics",
                  [lambda n: f"Rehoboth Boardwalk Classics: {n} Checked Places | {BRAND}"],
                  [lambda n: f"{plural(n, 'boardwalk standby', 'boardwalk standbys')} in Rehoboth, Dewey and Bethany for pizza by the slice, fries and frozen custard, each checked in {CHECKED}."],
                  lambda n: f"{plural(n, 'boardwalk standby', 'boardwalk standbys')} at Delaware's beaches, each checked in {CHECKED} against a 2025–26 source.",
                  """<h2>On the boards</h2>
    <p>Pizza by the slice, fries doused in malt vinegar and frozen custard at walk-up windows along Rehoboth's boardwalk and the Dewey and Bethany beach blocks. Most keep summer hours.</p>""",
                  "Delaware boardwalk classics", "place"),
    "dumplings": ("Chicken & slippery dumplings",
                  [lambda n: f"Chicken & Slippery Dumplings in Delaware: {n} Places"],
                  [lambda n: f"{plural(n, 'Delaware place')} for chicken and slippery dumplings, Sussex County's church-supper dish, each checked in {CHECKED} against a 2025–26 source."],
                  lambda n: f"{plural(n, 'place')} for chicken and slippery dumplings, each checked in {CHECKED} against a 2025–26 source.",
                  """<h2>Sussex County's dish</h2>
    <p>Slippery dumplings are flat squares of rolled dough cooked in chicken broth, served with stewed chicken: a Sussex County church-supper standby.</p>""",
                  "Chicken and slippery dumplings", "place"),
}
for k, _ in GUIDE_TAGS:
    h1, titles, descs, lede, about, list_name, noun = GUIDE_DEFS[k]
    n = len(L[k])
    guide(k, h1, [t(n) for t in titles], [d(n) for d in descs], lede(n), about, list_name, noun)

# ---------------------------------------------------------------- James Beard (Delaware has no MICHELIN Guide)
guide_page(HON_PATH, "Delaware James Beard restaurants", f"{BRAND} · honors current as of {CHECKED}",
           [f"Delaware James Beard Restaurants & Chefs | {BRAND}", "James Beard Award Restaurants in Delaware | " + BRAND],
           [f"{plural(len(HON_L), 'Delaware restaurant')} whose chefs the James Beard Foundation named for Best Chef: Mid-Atlantic, with the year of each honor, by county and town.",
            f"{plural(len(HON_L), 'Delaware restaurant')} with a James Beard Best Chef: Mid-Atlantic finalist or semifinalist in the kitchen, from Wilmington to Fenwick Island."],
           f"{plural(len(HON_L), 'Delaware restaurant')} whose chefs the James Beard Foundation named for Best Chef: Mid-Atlantic, each with the year. Delaware has no MICHELIN Guide.",
           f"""<h2>What counts as an honor here</h2>
    <p>One source, reported as facts rather than scores: the James Beard Foundation's Restaurant and Chef Awards (semifinalists, finalists and winners, each labeled as exactly that, with its year). A person award that went to a brewer or a humanitarian isn't a restaurant's honor, so it isn't here. Reader polls, "best of" roundups and review-site stars don't count, and there's no MICHELIN Guide for Delaware.</p>
    <p class="fine">James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with it.</p>""",
           HON_L, "restaurant", "restaurants", "Delaware James Beard restaurants", honors=True)

# ---------------------------------------------------------------- oldest
if HAS_OLD:
    oldest_named = next((p for p in OLD_L if p.promo_ok()), None)
    assert all(p.founded <= 1960 for p in OLD_L), "the oldest-places copy says 'since 1960 or earlier'"
    from_line = f" The oldest, {e(oldest_named.name)} in {e(oldest_named.city)}, goes back to {oldest_named.founded}." if oldest_named else ""
    guide_page(OLD_PATH, "Delaware's oldest restaurants", checked_kicker(),
               [f"Delaware's Oldest Restaurants: {len(OLD_L)} Places, Oldest First", f"Oldest Restaurants in Delaware: {len(OLD_L)} Places | {BRAND}"],
               [f"{plural(len(OLD_L), 'Delaware restaurant')} open at the same address since 1960 or earlier, oldest first, each with a note on what its founding year rests on."],
               f"Taverns and restaurants that have fed Delaware from the same address since 1960 or before: {plural(len(OLD_L), 'place')} in all, oldest first.{from_line}",
               """<h2>Which year counts</h2>
    <p>We count from the year a place opened at its current address, going by the place's own history or a published one.</p>""",
               OLD_L, "place", "places", "Delaware's oldest restaurants", region=False, show_fn=True)

# ---------------------------------------------------------------- the inspections explainer (counts only: no place is named here)
url = f"{DOMAIN}/{INS_PATH}"
n_ins = len(INS_L)
nav, bc = crumbs([("Home", "/"), ("Health inspections", "/" + INS_PATH)])
title = fit(["Delaware Restaurant Inspections, Explained | Delaware Eats", "Delaware Restaurant Inspections: What DPH Publishes"], 50, 60, "inspections title")
desc = fit([f"How Delaware's Division of Public Health inspects restaurants, what its published records show, and the latest routine inspection for {n_ins:,} places we list.",
            f"Delaware's Division of Public Health inspects every restaurant. What its records show, and the latest routine inspection for {n_ins:,} places."],
           140, 160, "inspections description")
zero, low, mid, high = (sum(v for k, v in CITED_N.items() if lo <= k <= hi) for lo, hi in ((0, 0), (1, 2), (3, 5), (6, 99)))
sec_top = Counter(c for p in INS_L for c in (p.r.get("in") or {}).get("h", [[None, None, None, []]])[0][3]).most_common(5)
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} guide · state records</p>
    <h1>Delaware restaurant inspections, explained</h1>
    <p class="lede">The Division of Public Health's Office of Food Protection inspects every food establishment in Delaware, Wilmington's included: the state has no local health departments. It publishes each inspection of the past two years, and Delaware has no restaurant grade, score or placard. Here is what the records show, and where the {n_ins:,} places in our data stood at their latest routine inspection.</p>
  </section>
  <section id="groups">
    <h2>What DPH publishes</h2>
    <p class="sub">For each inspection: the date, the type (routine, follow-up or complaint) and each section of the Delaware Food Code the inspector cited, by number and title. We show those words and numbers and compute no grade of our own. DPH doesn't say which citations were priority items, so we count every section the same.</p>
    <ul class="groups">
      <li><h3>Sections cited at the latest routine inspection</h3><p>For the {n_ins:,} places we list with a routine inspection in the past two years, through {e(INS_DATE)}:</p>
        <ul><li><span class="res res-n">Nothing cited</span> {plural(zero, "place")}</li><li><span class="res res-n">1 or 2 sections</span> {plural(low, "place")}</li>
        <li><span class="res res-n">3 to 5 sections</span> {plural(mid, "place")}</li><li><span class="res res-n">6 or more</span> {plural(high, "place")}</li></ul>
        <p class="count"><a href="{e(DPH_URL)}" rel="noopener">DPH's records on data.delaware.gov</a>.</p></li>
      <li><h3>The sections cited most often</h3><p>A section's title names the rule that was cited, not what the inspector saw: "Controlling Pests" covers a missing log as well as a pest. At these places' latest inspections, the most cited were:</p>
        <ul>{"".join(f"<li>{e(c)} {e(SECTIONS.get(c, ''))} ({plural(n, 'place')})</li>" for c, n in sec_top)}</ul></li>
    </ul>
    <p>One inspection is a snapshot of one day. Many citations are corrected during the visit, and a follow-up checks the rest; the app and web search show any later follow-up or complaint visit beside the routine one. We don't list places by their counts here.</p>
  </section>
  <section id="lookup">
    <h2>Look a place up</h2>
    <p>Search a restaurant in the <a href="/explore/">{BRAND} web app</a> for its latest routine inspection, every inspection in the past two years with the sections cited, and its Delaware business license. DPH marks an establishment it has closed, and we leave those places out even when a business license is still valid.</p>
    <p class="fine">{other_guides("/" + INS_PATH)}</p>
  </section>
  </main>"""
page(INS_PATH, title, desc, body, [article_ld(url, "Delaware restaurant inspections, explained", desc), bc])

# ---------------------------------------------------------------- city pages
city_stats = {}
SEC_DEFS = [  # key, long title phrase, short title phrase, h1 phrase, description phrase builder (guides with a page only)
    d for d in [
    ("scrapple", "Scrapple", "Scrapple", "scrapple", lambda n: plural(n, "place for scrapple", "places for scrapple")),
    ("italian", "Italian", "Italian", "Italian", lambda n: plural(n, "Italian place")),
    ("creamery", "Farm Creameries", "Ice Cream", "farm creameries", lambda n: plural(n, "farm creamery", "farm creameries")),
    ("brewpub", "Brewpubs", "Brewpubs", "brewpubs", lambda n: plural(n, "brewpub")),
    ("crab", "Crab Houses", "Crabs", "crab houses and seafood", lambda n: plural(n, "crab house or seafood place", "crab houses and seafood places")),
    ("boardwalk", "Boardwalk Classics", "Boardwalk", "boardwalk classics", lambda n: plural(n, "boardwalk standby", "boardwalk standbys")),
    ("dumplings", "Slippery Dumplings", "Dumplings", "slippery dumplings", lambda n: plural(n, "place for slippery dumplings", "places for slippery dumplings")),
    ] if d[0] in L]
SEC_ORDER = [k for k, *_ in SEC_DEFS] + ["hon", "oldest"]
CITY_INFO = {}
for c in CITY_PAGES:
    here = [p for p in REST if p.city == c]
    info = {k: sorted([p for p in L[k] if p.city == c], key=P.featured_key) for k, _ in GUIDE_TAGS}
    info["hon"] = sorted([p for p in HON_L if p.city == c], key=P.featured_key)
    info["oldest"] = [p for p in OLD_L if p.city == c] if HAS_OLD else []
    info["insp"] = Counter(min(p.cited, 6) for p in INS_L if p.city == c)
    info["n_ins"] = sum(1 for p in INS_L if p.city == c)
    info["cuis"] = Counter(p.cuisine for p in here if p.cuisine and p.cuisine not in ("Other", "American & Other")).most_common(10)
    info["n_town"] = len(here)
    listed, seen = [], set()
    for k in SEC_ORDER:
        for p in info[k]:
            if id(p) not in seen:
                seen.add(id(p)); listed.append(p)
    info["listed"] = listed
    CITY_INFO[c] = info
    city_stats[c] = {"restaurants": len(here), "listed": len(listed), **{k: len(info[k]) for k in SEC_ORDER},
                     "inspection_results": info["n_ins"], "inspection_bands": dict(info["insp"])}


def city_sections(info):
    """The sections a city page has, biggest first: (key, long, short, h1 phrase, description phrase)."""
    out = [(k, lt, st, h1p, dp(len(info[k]))) for k, lt, st, h1p, dp in SEC_DEFS if info[k]]
    if info["hon"]:
        out.append(("hon", "James Beard", "James Beard", "James Beard honorees", plural(len(info["hon"]), "James Beard honoree")))
    if info["oldest"]:
        k_old = len(info["oldest"])   # "1 of Delaware's oldest restaurants", not "the oldest restaurants" (one place isn't the town's all)
        out.append(("oldest", "Oldest Restaurants", "Oldest Places", "oldest restaurants",
                    f"1 of Delaware's oldest restaurants (from {info['oldest'][0].founded})" if k_old == 1
                    else f"{k_old} of Delaware's oldest restaurants (back to {info['oldest'][0].founded})"))
    return sorted(out, key=lambda s: (-len(info[s[0]]), SEC_ORDER.index(s[0])))


def tjoin(xs):
    if len(xs) == 1:
        return xs[0]
    conj = " and " if any("&" in x for x in xs) else " & "
    return ", ".join(xs[:-1]) + conj + xs[-1]


def city_title(c, secs):
    cands = []
    for k in range(min(len(secs), 3), 0, -1):
        for col in (1, 2):
            J = tjoin([s[col] for s in secs[:k]])
            # "<town> restaurants" is what people search, so those forms come first
            forms = ([f"{c} Restaurants: {J}", f"{c}, DE Restaurants: {J}", f"{c} Restaurants: {J} | {BRAND}", f"{c}, Delaware Restaurants: {J}"]
                     if "Restaurant" not in J else [])
            forms += [f"{c} {J} | {BRAND}", f"{c}, DE {J} | {BRAND}", f"{c}, Delaware {J}", f"{c}, DE {J}", f"{c} {J}"]
            if "Restaurant" not in J:
                forms += [f"{c}, Delaware Restaurants: {J} | {BRAND}", f"{c}, DE Restaurants: {J} | {BRAND}"]
            if "Restaurant" not in J:
                forms += [f"{c} {J} & Restaurants", f"{c} {J} & Restaurants | {BRAND}", f"{c}, Delaware {J} & Restaurants"]
            cands += forms
    cands += [f"{c} Restaurants: What {c} Eats | {BRAND}", f"{c}, Delaware Restaurants by Kind | {BRAND}", f"{c}, DE Restaurants, Cafés & Bars | {BRAND}",
              f"{c}, Delaware Restaurants, Cafés and Bars", f"{c} Restaurants, Cafés & Bars | {BRAND}", f"{c}, Delaware: Restaurants, Cafés & More | {BRAND}",
              f"{c}, DE: Restaurants, Cafés & Bakeries | {BRAND}"]
    return fit(cands, 50, 60, c + " title")


def city_desc(c, info, secs):
    n_town = info["n_town"]
    leads = [f"In {c}, Delaware", f"{c}, Delaware", f"{c}, DE"]
    tails = [f". Search {n_town:,} {c} restaurants, cafés and bars", f". Search {n_town:,} local places to eat",
             f", plus {n_town:,} local places to eat on a searchable map", f", plus {n_town:,} more local places to eat", ""]
    extras = ["", f" Checked in {CHECKED}.", " Free iPhone app coming soon.", f" Checked in {CHECKED}. Free iPhone app coming soon."]

    def gen():
        for k in range(len(secs), 0, -1):
            J = join_words([s[4] for s in secs[:k]])
            for lead in leads:
                for tail in tails:
                    for x in extras:
                        yield f"{lead}: {J}{tail}.{x}"
    return fit(list(dict.fromkeys(s.replace("..", ".") for s in gen())), 140, 160, c + " description")


SEC_HEAD = {"scrapple": ("Scrapple", "scrapple"), "italian": ("Italian", "italian"), "creamery": ("Farm creameries", "creamery"),
            "brewpub": ("Brewpubs", "brewpub"), "crab": ("Crab houses & seafood", "crab"), "boardwalk": ("Boardwalk classics", "boardwalk"),
            "dumplings": ("Slippery dumplings", "dumplings")}
GUIDE_COUNT_NOUN = {"scrapple": "places for scrapple", "italian": "Wilmington Italian places", "creamery": "farm creameries",
                    "brewpub": "Delaware brewpubs", "crab": "crab houses and seafood places", "boardwalk": "boardwalk standbys",
                    "dumplings": "places for slippery dumplings"}
SINGULAR = {"places for scrapple": "place for scrapple", "Wilmington Italian places": "Wilmington Italian place",
            "farm creameries": "farm creamery", "crab houses and seafood places": "crab house or seafood place",
            "places for slippery dumplings": "place for slippery dumplings"}

for c in CITY_PAGES:
    info = CITY_INFO[c]
    path = f"cities/{slug(c)}.html"
    url = DOMAIN + "/" + path
    anchors = Anchors(url)
    secs = city_sections(info)
    title = city_title(c, secs)
    desc = city_desc(c, info, secs)
    k = 3
    while k > 1 and len(join_words([s[3] for s in secs[:k]])) > 48:   # a heading, not the whole table of contents
        k -= 1
    h1_bits = [s[3] for s in secs[:k]]
    h1 = f"{c} restaurants" + (": " + join_words(h1_bits + (["more"] if len(secs) > k else [])) if secs else "")
    nav, bc = crumbs([("Home", "/"), ("Cities", "/cities/"), (c, "/" + path)])
    counts = [s[4] for s in secs]
    n_hc = sum(1 for p in info["listed"] if p.hc and p.tags)
    lede = (f"What {e(c)} has on our lists: {e(join_words(counts))}. "
            + (f"Each hand-checked place had a 2025 or 2026 source when we looked in {CHECKED}. " if n_hc else "")
            + f"In all, {BRAND} maps {info['n_town']:,} restaurants, cafés, bars and bakeries in {e(c)}, nearest first on your phone.")
    parts = [f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} · {e(c)}, Delaware</p>
    <h1>{e(h1)}</h1>
    <p class="lede">{lede}</p>
    <div class="cta-row">{store_button()}<span class="pill store-note">{STORE_NOTE}</span></div>
  </section>"""]
    for s in secs:
        key = s[0]
        if key in SEC_HEAD:
            head, gk = SEC_HEAD[key]
            parts.append(f'<section id="{key}" aria-labelledby="h-{key}"><h2 id="h-{key}">{e(head)} in {e(c)}</h2><p class="sub">Each one checked in {CHECKED} against a 2025–26 source. For all of Delaware: <a href="/{GUIDE_PATH[gk]}">{plural(len(L[gk]), SINGULAR.get(GUIDE_COUNT_NOUN[gk], GUIDE_COUNT_NOUN[gk][:-1]), GUIDE_COUNT_NOUN[gk])}</a>.</p><ol class="places">'
                         + "".join(place_item(p, anchors) for p in info[key]) + "</ol></section>")
        elif key == "hon":
            parts.append(f'<section id="honors" aria-labelledby="h-honors"><h2 id="h-honors">James Beard honorees in {e(c)}</h2><p class="sub">Restaurants named by the James Beard Foundation, reported as facts rather than scores. Across Delaware: <a href="/{HON_PATH}">{plural(len(HON_L), "Delaware James Beard restaurant")}</a>.</p><ol class="places">'
                         + "".join(place_item(p, anchors, honors=True) for p in info["hon"]) + "</ol></section>")
        elif key == "oldest":
            parts.append(f'<section id="oldest" aria-labelledby="h-oldest"><h2 id="h-oldest">Oldest restaurants in {e(c)}</h2><p class="sub">In business at this address since 1960 or before, going by the place itself or a published history, listed from the oldest. Each note gives the source of the year. Across Delaware: <a href="/{OLD_PATH}">Delaware\'s oldest restaurants</a>.</p><ol class="places">'
                         + "".join(place_item(p, anchors, show_fn=True) for p in info["oldest"]) + "</ol></section>")
    here_ins = [p for p in INS_L if p.city == c]   # DPH's records: sections cited at the latest routine inspection, never a grade
    if here_ins:
        ig = Counter(min(p.cited, 6) for p in here_ins)
        bits = join_words([f"nothing cited ({ig.get(0, 0):,})", f"1 or 2 sections ({ig.get(1, 0) + ig.get(2, 0):,})",
                           f"3 to 5 ({ig.get(3, 0) + ig.get(4, 0) + ig.get(5, 0):,})", f"6 or more ({ig.get(6, 0):,})"])
        what = (f"The Division of Public Health inspected {plural(len(here_ins), 'place')} we list in {e(c)} on a routine visit in the past two years. "
                f"Food Code sections cited at the latest routine inspection: {e(bits)}. Records through {e(INS_DATE)}. Each place's inspections are in the "
                f'<a href="/explore/#g=inspections&amp;town={e(urllib.parse.quote(c))}">web search</a>')
        parts.append(f'<section id="inspections" aria-labelledby="h-inspections"><h2 id="h-inspections">Inspections in {e(c)}</h2><p class="sub">{what}; '
                     f'what they mean: <a href="/{INS_PATH}">Delaware restaurant inspections, explained</a>. Delaware has no restaurant grade, and we add none.</p></section>')
    if info["cuis"]:
        rows = "".join(f'<tr><td>{e(k)}</td><td class="n">{n:,}</td></tr>' for k, n in info["cuis"])
        parts.append(f'<section id="cuisines" aria-labelledby="h-cuisines"><h2 id="h-cuisines">What {e(c)} eats</h2><p class="sub">Kinds of food among the {info["n_town"]:,} places we list in {e(c)}, counted from open map data{" and the state\'s inspection and license lists" if any(p.city == c and p.r.get("t") == 2 for p in REST) else ""}.</p><table><thead><tr><th scope="col">Kind of place</th><th scope="col" class="n">Places</th></tr></thead><tbody>{rows}</tbody></table></section>')
    parts.append(f'<section id="more" aria-labelledby="h-more"><h2 id="h-more">Other Delaware towns with a page</h2>{city_links(current=c)}<p class="fine"><a href="/cities/">The cities and towns index</a></p></section>\n  </main>')
    lds = [article_ld(url, h1, desc), bc]
    if info["listed"]:
        lds.append(item_list(f"{c}: " + join_words([s[3] for s in secs]), info["listed"], url, anchors))
    page(path, title, desc, "\n".join(parts), lds)


# ---------------------------------------------------------------- cities index
url = f"{DOMAIN}/cities/"
nav, bc = crumbs([("Home", "/"), ("Cities", "/cities/")])
cards = []
for c in CITY_PAGES:
    info = CITY_INFO[c]
    bits = [f"{s[3]} ({len(info[s[0]])})" for s in city_sections(info)]
    line = (join_words(bits) + ". " if bits else "") + f"{info['n_town']:,} places to eat in all."
    cards.append(f'<a class="card" href="{city_url(c)}"><h3>{e(c)}</h3><p>{e(line[0].upper() + line[1:])}</p></a>')
first, last = CITY_PAGES[:2], CITY_PAGES[-2:]
title = fit([f"Delaware Cities & Towns: Restaurant Guides | {BRAND}", f"Delaware Town Restaurant Guides: {plural(len(CITY_PAGES), 'Town')} | {BRAND}",
             f"Delaware Towns: Scrapple, Crabs & Restaurant Guides"], 50, 60, "cities title")
desc = fit([f"Restaurant guides for {plural(len(CITY_PAGES), 'Delaware city and town', 'Delaware cities and towns')}: scrapple, Italian, brewpubs, crab houses and James Beard honors.",
            f"Town-by-town Delaware restaurant guides for {plural(len(CITY_PAGES), 'town')}: scrapple, brewpubs, farm creameries, crab houses and James Beard honors, hand-checked."],
           140, 160, "cities description")
skipped_line = (f" Other towns get a page once they have at least {MIN_LISTED} hand-checked or honored places; until then, "
                f'<a href="/explore/">search them</a>.')
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND} · cities and towns</p>
    <h1>Delaware cities and towns</h1>
    <p class="lede">A page for Delaware towns that have enough hand-checked or honored places to say something real: the scrapple, brewpubs, creameries and James Beard honorees that are actually there, and the Division of Public Health's inspection records for each town.{skipped_line}</p>
  </section>
  <section id="cities-list">
    <h2>Pick a town</h2>
    <div class="grid2">{"".join(cards)}</div>
  </section>
  </main>"""
page("cities/index.html", title, desc, body, [bc], og_type="website")

# ---------------------------------------------------------------- web app (docs/explore/): data split + page
# The web app lists restaurants only (the venues the app hides by default, such as stadium stands and gas-station counters, stay out).
# Three kinds of file, to keep the first load small for ~25,000 places:
# - core.json: the list, search and map columns. Places are ordered by region, county, town, zip and street, so neighbouring rows
#   share their town, zip and street words and gzip well; coordinates are integer steps of 0.0001° from the previous row ("dla"/"dlo"),
#   and the latest inspection is [city, result, priority count] plus a day number from 2000-01-01 ("idn").
# - ids.json: each place's stable id (the app's id), in core order. Fetched right after the list renders; saved places and shared
#   #p= links wait for it.
# - detail-<county>.json: phones, websites, notes, licenses and inspection histories, keyed by core index, one file per county
#   (Franklin's is the biggest), fetched when someone opens (or points at) a place there.
os.makedirs(f"{DOCS}/data", exist_ok=True)
DFILES = [slug(c) for c in COUNTIES] + ["other"]   # detail file per county index; "other" for a place with no county
CAL = {a: {"groups": {g: {"n": v.get("n"), "official": v.get("official")} for g, v in (c.get("groups") or {}).items()}}
       for a, c in (D.get("calibration") or {}).items() if isinstance(c, dict)}
DAY0 = "2000-01-01"


def day_num(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    return (dt.date(int(m[1]), int(m[2]), int(m[3])) - dt.date(2000, 1, 1)).days if m else None


def street_key(a):
    m = re.match(r"\s*(\d+)\s*(.*)", a or "")
    return (m[2].lower(), int(m[1]) if len(m[1]) < 9 else 0) if m else ((a or "").lower(), 0)


def web_order(p):
    rg = REGION_ORDER.index(p.region) if p.region else len(REGION_ORDER)
    return (rg, p.county or "", p.city or "", p.zip, street_key(p.addr), p.name.lower(), p.r["id"])


WEB = sorted(REST, key=web_order)
CORE_KEYS = ["n", "c", "co", "cu", "t", "s", "a", "z", "b", "ch", "g", "hc", "ip", "f", "h", "dish", "liq"]
cols = {k: [] for k in CORE_KEYS + ["dla", "dlo", "jb", "icn", "idn", "ild", "iln", "ilt"]}
ids, shards = [], defaultdict(dict)
prev = [0, 0]
for i, p in enumerate(WEB):
    r = p.r
    ids.append(r["id"])
    for k in CORE_KEYS:
        v = r.get(k)
        if k == "a" and v:
            v = p.addr
        cols[k].append(v)
    for k, j, v in (("dla", 0, p.lat), ("dlo", 1, p.lon)):
        if v is None:
            cols[k].append(None)
        else:
            q = round(v * 10000)
            cols[k].append(q - prev[j])
            prev[j] = q
    dk = r["co"] if r.get("co") is not None else len(COUNTIES)   # the detail file this place's extras go in
    if r.get("co") is None:
        cols["co"][-1] = len(COUNTIES)
    cols["jb"].append(1 if r.get("jbf") else None)
    ins = p.ins or {}
    cols["icn"].append(ins.get("n_cited"))          # Food Code sections cited at the latest routine inspection
    cols["idn"].append(day_num(ins.get("d")))       # its date
    cols["ild"].append(day_num(ins.get("ld")))      # the latest inspection of any type
    cols["iln"].append(ins.get("ln") if ins else None)
    cols["ilt"].append(ins.get("lt") if ins else None)
    d = {k: r[k] for k in ("ph", "note", "seas", "fn", "jbf", "lic") if r.get(k)}
    if p.site:
        d["w"] = p.site
    if ins.get("h"):
        d["in"] = {"n": ins.get("n"), "h": ins["h"]}
    if d:
        shards[dk][str(i)] = d
assert len(set(ids)) == len(ids), "place ids must be unique (saved places and #p= links use them)"
for f in glob.glob(f"{DOCS}/data/detail*.json"):   # files from an older layout or a region that emptied
    os.remove(f)
# columns that are mostly empty (hand-checked and honored facts) go as [[index, value], ...] instead of 25,000 nulls
sparse = {k: [[i, v] for i, v in enumerate(cols.pop(k)) if v is not None]
          for k in list(cols) if sum(v is not None for v in cols[k]) < len(WEB) * 0.05}
core = {"generated": D["generated"], "inspections_through": INS_THROUGH,
        "guides": [k for k, _ in ALL_GUIDES if L_ALL[k]], "day0": DAY0, "n": len(WEB), "cities": CITIES, "cuisines": CUISINES, "counties": COUNTIES + ["Delaware"],
        "brands": D["brands"], "srcs": D["srcs"], "itypes": ITYPES, "sections": SECTIONS, "calibration": CAL, "cols": cols, "sparse": sparse,
        "dfiles": [f if dk in shards else None for dk, f in enumerate(DFILES)]}   # null: that county has no extras, so no file
assert all("," not in x for x in ids)
# ids and details are keyed by row, so a file from one build must never meet another build's core.json (a browser cache can outlive a
# deploy by GitHub's 10 minutes): every file carries the build's version, the page fetches with ?v=, and the web app refuses a mismatch
DATA_VER = hashlib.sha256(json.dumps([core, ids, shards], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
DETAIL_FILES = {}
for dk, d in sorted(shards.items()):
    fn = f"detail-{DFILES[dk]}.json"
    json.dump({"_v": DATA_VER, **d}, open(f"{DOCS}/data/{fn}", "w"), separators=(",", ":"), ensure_ascii=False)
    DETAIL_FILES[fn] = len(d)
json.dump({"ver": DATA_VER, **core}, open(f"{DOCS}/data/core.json", "w"), separators=(",", ":"), ensure_ascii=False)
json.dump({"v": DATA_VER, "ids": ",".join(ids)}, open(f"{DOCS}/data/ids.json", "w"), separators=(",", ":"))   # one string: smaller than an array
json.dump(json.load(open(f"{ROOT}/data/app/de_shapes.json")), open(f"{DOCS}/data/de_shapes.json", "w"), separators=(",", ":"))
for f in glob.glob(f"{DOCS}/data/oh_shapes.json"):
    os.remove(f)


def sizes(path):
    raw = open(path, "rb").read()
    return len(raw), len(gzip.compress(raw, 9))


SIZES = {os.path.relpath(f, DOCS): sizes(f) for f in sorted(glob.glob(f"{DOCS}/data/*.json"))}

EXPLORE_CSS = """
  [hidden] { display: none !important; }
  .ex-hero { padding: 28px 0 8px; }
  .ex-hero h1 { font-size: clamp(30px, 6vw, 44px); }
  .ex-controls { background: var(--bg); padding: 10px 0 8px; border-bottom: 1px solid var(--rule); }
  .ex-guides { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; }
  @media (min-width: 601px) { .ex-guides { flex-wrap: wrap; overflow: visible; } }
  @media (max-width: 600px) { .ex-guides { padding-right: 32px; -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); mask-image: linear-gradient(to right, #000 calc(100% - 32px), transparent); } }
  .ex-guides button, .ex-view button, .ex-small { flex: 0 0 auto; border: 1px solid var(--rule); background: var(--surface); color: var(--accent); border-radius: 999px; padding: 7px 12px; font: 600 14px/1.2 system-ui, sans-serif; font-family: inherit; cursor: pointer; }
  .ex-guides button[aria-pressed="true"], .ex-view button[aria-pressed="true"] { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
  .ex-row1 { display: flex; gap: 8px; align-items: center; }
  .ex-row1 input[type=search] { flex: 1; min-width: 0; font: 16px/1.3 system-ui, sans-serif; font-family: inherit; padding: 10px 12px; border: 2px solid var(--accent); border-radius: 12px; background: var(--surface); color: var(--ink); }
  .ex-row2 { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; font-size: 14px; }
  .ex-row2 select { font: 14px system-ui, sans-serif; font-family: inherit; padding: 6px 8px; border: 1px solid var(--rule); border-radius: 8px; background: var(--surface); color: var(--ink); max-width: 46vw; }
  .ex-view { margin-left: auto; display: flex; gap: 4px; }
  #ex-count { margin: 8px 0 0; font-size: 14px; color: var(--muted); }
  #ex-sub { margin: 4px 0 0; font-size: 14px; color: var(--ink2); }
  #ex-locmsg { font-size: 13px; color: var(--muted); margin: 4px 0 0; }
  .ex-list { list-style: none; padding: 0; margin: 10px 0; }
  .ex-list li + li { border-top: 1px solid var(--rule); }
  .ex-row { width: 100%; display: flex; gap: 12px; align-items: center; text-align: left; background: none; border: 0; padding: 12px 4px; cursor: pointer; color: var(--ink); font: inherit; }
  .ex-row:hover { background: var(--surface2); }
  .ex-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; overflow-wrap: anywhere; }
  .ex-main b { font-weight: 650; }
  .ex-town { font-size: 14px; color: var(--muted); }
  .tag-dash { background: transparent; color: var(--muted); border: 1px dashed var(--rule); }
  .ex-metric { text-align: right; display: flex; flex-direction: column; align-items: flex-end; max-width: 46%; }
  .ex-metric b { font: 800 22px/1 var(--display); color: var(--accent); }
  .ex-metric small { font-size: 11px; color: var(--muted); }
  .ex-rank { flex: 0 0 34px; height: 34px; display: grid; place-items: center; font: 800 20px var(--display); color: var(--accent); border-radius: 8px; }
  .ex-rank.top { background: var(--orange); color: var(--on-orange); }
  .ex-empty { padding: 24px 4px; color: var(--muted); }
  #ex-more { display: block; margin: 8px auto 24px; }
  #ex-mapwrap { position: relative; height: min(78vh, 820px); margin: 10px 0 20px; border: 1px solid var(--rule); border-radius: 16px; overflow: hidden; background: #f7f4ee; }
  #ex-map { width: 100%; height: 100%; display: block; touch-action: none; cursor: grab; }
  .ex-zoom { position: absolute; right: 10px; top: 10px; display: flex; flex-direction: column; gap: 6px; }
  .ex-zoom button { width: 44px; height: 44px; border-radius: 10px; border: 1px solid #e4ddd0; background: #fff; color: #1f3b6f; font: 700 22px/1 system-ui, sans-serif; cursor: pointer; }
  #ex-maphint { position: absolute; left: 10px; top: 10px; margin: 0; font-size: 13px; background: #fff; padding: 3px 8px; border-radius: 999px; color: #1f3b6f; pointer-events: none; }
  #ex-mapattr { position: absolute; right: 0; bottom: 0; margin: 0; font-size: 11px; background: rgba(255,255,255,.85); padding: 2px 6px; border-radius: 6px 0 0 0; color: #1f3b6f; pointer-events: none; }
  .ex-panel { position: fixed; z-index: 20; right: 0; top: 0; bottom: 0; width: min(440px, 100%); overflow-y: auto; background: var(--surface); border-left: 1px solid var(--rule); box-shadow: -8px 0 24px rgba(0,0,0,.12); padding: 18px 20px 40px; }
  @media (max-width: 600px) { .ex-panel { top: auto; height: 86vh; border-left: 0; border-top: 4px solid var(--orange); border-radius: 18px 18px 0 0; } }
  .ex-close { position: sticky; top: 0; float: right; width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--rule); background: var(--surface); font-size: 24px; line-height: 1; cursor: pointer; color: var(--ink); }
  .ex-kicker { margin: 0; font-size: 12px; font-weight: 700; letter-spacing: .1em; color: var(--accent2); }
  .ex-panel h2 { font-size: 34px; margin: 4px 0 6px; text-transform: uppercase; overflow-wrap: anywhere; }
  .ex-addr, .ex-dist { margin: 0 0 4px; color: var(--ink2); font-size: 15px; }
  .ex-actions { margin: 14px 0 8px; display: grid; gap: 8px; }
  .ex-apple { justify-content: center; }
  .ex-act-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .ex-act-row a, .ex-act-row button { flex: 1; min-width: 88px; text-align: center; padding: 10px; border: 1px solid var(--rule); border-radius: 12px; text-decoration: none; color: var(--accent); font: 600 14px system-ui, sans-serif; font-family: inherit; background: var(--surface); cursor: pointer; }
  .ex-act-row button[aria-pressed="true"] { background: var(--soft); color: #1f3b6f; }
  .ex-sec { margin-top: 18px; }
  .ex-sec h3 { font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--rule); padding-bottom: 6px; margin-bottom: 8px; }
  .ex-sec p, .ex-sec li { font-size: 15px; color: var(--ink2); margin: 6px 0; }
  .ex-sec ul { padding-left: 18px; }
  .ex-kv { display: flex; justify-content: space-between; gap: 12px; font-size: 15px; padding: 3px 0; }
  .ex-kv span { color: var(--ink2); flex: 0 0 auto; max-width: 40%; }
  .ex-kv b { text-align: right; overflow-wrap: anywhere; }
  .ex-fine { font-size: 13px !important; color: var(--muted) !important; }
  .ex-result { display: flex; align-items: center; gap: 10px; font-weight: 600; flex-wrap: wrap; }
  .ex-app { margin-top: 22px; font-size: 14px; color: var(--muted); }
  body.ex-open { overflow: hidden; }
  .ex-backdrop { position: fixed; inset: 0; z-index: 19; background: rgba(19, 33, 61, .32); }
  /* phones: 16px or more in the search box and the selects, or iOS Safari zooms the page when one gets focus */
  @media (max-width: 600px) { .ex-row1 input[type=search], .ex-row2 select { font-size: 16px; } }
  /* the sort's longest choice ("Fewest sections cited") at 16px: wider than 46vw, so on phones it may use the row */
  @media (max-width: 600px) { #ex-sort { max-width: calc(100vw - 100px); } }
  .ex-res { display: inline-block; font: 800 12px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .04em; text-transform: uppercase; padding: 3px 8px; border-radius: 6px; text-align: center; }
  .ex-res-n, .ex-res-x { background: var(--surface2); color: var(--ink2); }
"""
url = f"{DOMAIN}/explore/"
N_HC_GUIDES = len(HC_ANY)
title = fit(["Delaware Restaurant Search: Map, Scrapple & Inspections", "Search Delaware Restaurants: Map, Guides & Inspections"], 50, 60, "explore title")
desc = fit([f"Look up {N_REST:,} Delaware restaurants by name, town, street, zip or dish, map {N_HC_GUIDES} hand-checked places and see each one's DPH inspections.",
            f"Search {N_REST:,} Delaware restaurants by name, town, street or dish, map {N_HC_GUIDES} hand-checked places, and see Division of Public Health inspections.",
            f"Search {N_REST:,} Delaware restaurants by name, town or dish, browse {N_HC_GUIDES} hand-checked places on a map and see state inspection records."],
           140, 160, "explore description")
nav, bc = crumbs([("Home", "/"), ("Search", "/explore/")])
WEB_GUIDES = [(k, t) for k, t in (("scrapple", "Scrapple"), ("italian", "Wilmington Italian"), ("creamery", "Farm creameries"),
                                   ("brewpub", "Brewpubs"), ("crab", "Crab houses & seafood"), ("boardwalk", "Boardwalk classics"),
                                   ("dumplings", "Slippery dumplings")) if L_ALL[k]]
guide_buttons = "".join(f'<button type="button" data-g="{k}" aria-pressed="false">{e(t)}</button>' for k, t in
                        WEB_GUIDES + [("honors", "James Beard"), ("oldest", "Oldest"), ("inspections", "Inspections"),
                                      ("all", "All restaurants"), ("saved", "Saved")])
explore_js = open(f"{ROOT}/scripts/explore.js").read()
JS_KEYS = sorted(set(re.findall(r'store\.set\("([a-z]+)"', explore_js)))   # the keys the web app writes, each under STORAGE_PREFIX
assert JS_KEYS and "localStorage.setItem(PREFIX + k" in explore_js and len(re.findall(r"localStorage\.setItem", explore_js)) == 1
assert "</script" not in explore_js.lower()
assert f'"{STORAGE_PREFIX}"' in explore_js, "explore.js must keep its localStorage keys under " + STORAGE_PREFIX
body = f"""{nav}
  <main id="main">
  <section class="ex-hero">
    <p class="kicker">{BRAND} · on the web</p>
    <h1>Search Delaware restaurants</h1>
    <p class="sub">Pick a list, or type a name, a town, a street or a dish. Behind the search: {N_REST:,} Delaware restaurants, cafés, bars and bakeries; {N_HC_GUIDES} hand-checked places on the scrapple, Wilmington Italian, creamery, brewpub and other food lists; {len(HON_L)} James Beard honorees; Delaware restaurant business licenses; and the Division of Public Health's inspection records. It's the data the iPhone and iPad app will ship with, and what you save stays in this browser.</p>
  </section>
  <p id="ex-loading" hidden>Loading the restaurant list…</p>
  <noscript><p>The search needs JavaScript. The guides work without it: <a href="/{GUIDE_PATH['scrapple']}">scrapple</a>, <a href="/{GUIDE_PATH['italian']}">Wilmington Italian</a>, <a href="/{GUIDE_PATH['creamery']}">farm creameries</a>, <a href="/{INS_PATH}">inspections explained</a>.</p></noscript>
  <div id="ex-app" hidden data-ver="{DATA_VER}">
    <div class="ex-controls">
      <div class="ex-guides" role="group" aria-label="Guides">{guide_buttons}</div>
      <div class="ex-row1">
        <label class="skip" for="ex-q">Search</label>
        <input id="ex-q" type="search" placeholder="Name, town, street or dish" autocomplete="off" enterkeyhint="search">
        <button type="button" id="ex-locate" class="ex-small">Near me</button>
      </div>
      <div class="ex-row2">
        <label>Sort <select id="ex-sort" aria-label="Sort"></select></label>
        <select id="ex-town" aria-label="Town"></select>
        <select id="ex-cuisine" aria-label="Kind of place"></select>
        <label><input type="checkbox" id="ex-chains"> Hide chains</label>
        <button type="button" id="ex-clear" class="ex-small" hidden>Clear filters</button>
        <div class="ex-view" role="group" aria-label="View"><button type="button" data-v="list" aria-pressed="true">List</button><button type="button" data-v="map" aria-pressed="false">Map</button></div>
      </div>
      <p id="ex-sub"></p>
      <p id="ex-count" aria-live="polite"></p>
      <p id="ex-locmsg"></p>
    </div>
    <div id="ex-listwrap"><ol id="ex-list" class="ex-list"></ol><button type="button" id="ex-more" class="ex-small" hidden></button></div>
    <div id="ex-mapwrap" hidden>
      <canvas id="ex-map" aria-label="Map of Delaware with a dot for each place in the list. The list view has the same places."></canvas>
      <div class="ex-zoom"><button type="button" id="ex-zin" aria-label="Zoom in">+</button><button type="button" id="ex-zout" aria-label="Zoom out">−</button></div>
      <p id="ex-maphint"></p>
      <p id="ex-mapattr">Outlines © Overture Maps Foundation, OpenStreetMap contributors</p>
    </div>
  </div>
  <div id="ex-backdrop" class="ex-backdrop" hidden></div>
  <aside id="ex-panel" class="ex-panel" hidden aria-labelledby="ex-pname"></aside>
  </main>
<script>
{explore_js}
</script>"""
webapp_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{BRAND} web app", "url": url,
             "applicationCategory": "TravelApplication", "operatingSystem": "Any", "browserRequirements": "Requires JavaScript",
             "description": desc, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
             "publisher": ORG_REF}
page("explore/index.html", title, desc, body, [webapp_ld, bc], extra_css=EXPLORE_CSS, og_type="website")

# ---------------------------------------------------------------- landing page
# alt text says what each capture shows (docs/screenshots, made by scripts/capture-screenshots.sh; copies by scripts/site-images.sh)
shots = [("home", "The Delaware Eats home screen: a search box and guide cards for Scrapple Breakfasts, Boardwalk Classics, Crab Houses & Seafood and Wilmington Italian, each with its count of places.", "A guide for each Delaware craving."),
         ("scrapple", "The hand-checked scrapple list in Delaware Eats, nearest first, with each place's town, kind and distance.", "Scrapple, nearest first."),
         ("detail", "Helen's Sausage House in Delaware Eats: its address, the scrapple tag, a button for Apple Maps' ratings, hours and photos, Directions and Call buttons, a small map and the hand-checked note.", "A place's page: the note, the inspections."),
         ("map", "The Delaware Eats map around Rehoboth Beach, with pins for hand-checked places and layer buttons for Delaware picks, crab houses, inspections, honors and everything.", "The map, by guide."),
         ("honors", "The James Beard honors list in Delaware Eats, with each place's town, kind and honor.", "James Beard honorees.")]
shot_html = []
for i, (name, alt, cap) in enumerate(shots):
    png = f"{DOCS}/img/screen-{name}.png"
    if not os.path.exists(png):
        continue
    w, h = png_size(png)
    lazy = ' loading="lazy"'   # the section sits below the fold at every width
    webp = os.path.exists(f"{DOCS}/img/screen-{name}.webp")
    src = (f'<source srcset="/img/screen-{name}.webp" type="image/webp">' if webp else "")
    shot_html.append(f'<li><picture>{src}<img src="/img/screen-{name}.png" alt="{e(alt)}" width="{w}" height="{h}"{lazy} decoding="async"></picture><p>{e(cap)}</p></li>')

SCRAP_L = L["scrapple"]
faq = [
    ("Is Delaware Eats free?", "Completely: no price, no ads, no in-app purchases and no account to create. It's an iPhone and iPad app on its way to the App Store, with no Android version yet; until it's out, the web search here works in any browser."),
    ("Where do the lists come from?", f"Two kinds of source. The scrapple, Wilmington Italian, creamery, brewpub and other food lists are our own research from {CHECKED}: a page that names each place for the food (the Cape Gazette, Delaware's or Greater Wilmington's tourism office, or the place's own site), and something from 2025 or 2026 that shows it's open. The wider directory of {N_REST:,} restaurants starts from Overture Maps' open place data, keeps the kinds of listing that proved reliable against the Division of Public Health's statewide list of inspected establishments, and adds inspected restaurants from that list."),
    ("Where can I get scrapple?", f"Our scrapple list has {len(SCRAP_L)} hand-checked places, from a Smyrna sausage house to Wilmington and Newark brunch menus. In the web search, the scrapple list puts the nearest first once you share your location."),
    ("How do I check a Delaware restaurant's inspection?", "Delaware has no restaurant grade, score or placard. The Division of Public Health inspects every restaurant in the state and publishes each inspection of the past two years: the date, the type and the Food Code sections cited. For each place, the app and this site show the latest routine inspection with the number of sections cited, any later follow-up, and the full list. We compute no grade."),
    ("Does it show ratings and reviews?", "Not from us. Tapping a place opens Apple Maps' own card inside the app, with Apple's current ratings, hours, photos and directions. None of our lists is sorted by anyone's rating."),
    ("Does it need my location?", "No. Location only matters for putting the nearest places first. If you share it, it stays on your iPhone or iPad and never reaches us, and the app works fine without it. On this website, Near me reads your location inside your browser and nowhere else."),
    ("A place has closed, or something's wrong. How do I tell you?", f"Write to {EMAIL} with the place's name, its town and what changed. Corrections ship with the next data update."),
]
faq_html = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "@id": f"{DOMAIN}/#faq",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
app_ld = {"@context": "https://schema.org", "@graph": [
    # No "offers" until the app is on the App Store (put it back with the listing URL: price 0, USD).
    {"@type": "MobileApplication", "@id": f"{DOMAIN}/#app", "name": APP_NAME,
     "alternateName": ["Delaware Eats", "DE Eats", "Delaware Eats: Scrapple, Crabs & Boardwalk"],
     "description": f"A free guide to {N_REST:,} Delaware restaurants, with hand-checked lists of {join_words([GUIDE_NAME[k].lower().replace('wilmington', 'Wilmington') for k in L_ALL if L_ALL[k]])}, {len(HON_L)} James Beard honorees, and the Division of Public Health's inspection records. Sort by distance, open Apple Maps' live place card for hours and photos, and save places for your next trip.",
     "url": f"{DOMAIN}/", "image": f"{DOMAIN}/og.png", "operatingSystem": "iOS, iPadOS", "applicationCategory": "TravelApplication",
     "applicationSubCategory": "Food & Drink", "inLanguage": "en", "publisher": {"@id": ORG_ID}},
    {"@type": "Organization", "@id": ORG_ID, "name": BRAND, "url": f"{DOMAIN}/",
     "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png", "width": 512, "height": 512}, "email": EMAIL,
     "contactPoint": {"@type": "ContactPoint", "contactType": "customer support", "email": EMAIL, "availableLanguage": "en"},
     # the Eats Ranked hub lists this site as a subOrganization; say so from this side too
     "parentOrganization": HUB},
    {"@type": "WebSite", "@id": f"{DOMAIN}/#website", "name": BRAND, "alternateName": ["DE Eats", "Delaware Eats app"], "url": f"{DOMAIN}/",
     "inLanguage": "en", "publisher": {"@id": ORG_ID}}]}
if shot_html:
    app_ld["@graph"][0]["screenshot"] = f"{DOMAIN}/img/screen-{next(n for n, *_ in shots if os.path.exists(f'{DOCS}/img/screen-{n}.png'))}.png"
title = fit(["Delaware Eats: Scrapple, Crabs & Delaware Restaurant App", "Delaware Eats: Scrapple, Crab Houses & Restaurant Guide"], 50, 60, "landing title")
desc = fit([f"Scrapple, crab houses, brewpubs and Wilmington Italian: a free iPhone and iPad guide to {N_REST:,} Delaware restaurants, with state inspections.",
            f"A free iPhone and iPad guide to {N_REST:,} Delaware restaurants, with hand-checked scrapple, brewpubs and creameries, and state inspection records.",
            f"Free iPhone and iPad guide to {N_REST:,} Delaware restaurants: hand-checked scrapple, brewpubs and Wilmington Italian, plus James Beard honorees."],
           140, 160, "landing description")
city_cards = "".join(f'<li><a href="{city_url(c)}">{e(c)}</a></li>' for c in CITY_PAGES)
screens = f"""
  <section id="screens">
    <h2>Inside the app</h2>
    <ul class="shots" tabindex="0" aria-label="Delaware Eats app screenshots">
      {"".join(shot_html)}
    </ul>
  </section>""" if shot_html else ""
guide_cards = "".join(f'<a class="card gc gc-{k}" href="/{GUIDE_PATH[k]}"><b>{len(L[k])}</b><h3>{e(GUIDE_NAME[k])}</h3><p>{plural(len(L[k]), "hand-checked place")}{line}.</p></a>'
                      for k, line in (("scrapple", ", diners to brunch"), ("italian", " in and around Little Italy"), ("creamery", " on dairy farms"),
                                      ("brewpub", " with a kitchen"), ("crab", " by the dozen"), ("boardwalk", " on the boards"),
                                      ("dumplings", " in Sussex County")) if k in L)
body = f"""  <main id="main">
  <section class="hero">
    <p class="kicker">{BRAND}: {TAGLINE} for iPhone and iPad</p>
    <h1>Delaware restaurants, scrapple to crabs</h1>
    <p class="lede">Looking for scrapple with your eggs in Smyrna, a red-sauce dinner in Wilmington's Little Italy, a brewpub at the beach or a cone at a dairy farm? {BRAND} starts with lists we checked place by place, adds James Beard honorees and the Division of Public Health's own inspection records, and maps {N_REST:,} restaurants, cafés, bars and bakeries in {N_TOWNS:,} Delaware towns.</p>
    <div class="cta-row">{store_button()}<a class="btn btn-ghost" href="/explore/">Search on the web</a><span class="pill store-note">No charge, no ads, no sign-in. The App Store release is on its way.</span></div>
    <ul class="stats" aria-label="What's in the app">
      <li><b>{N_HC_GUIDES}</b><span>hand-checked places</span></li>
      <li><b>{len(HON_L)}</b><span>James Beard honorees</span></li>
      <li><b>{len(INS_L):,}</b><span>with a state inspection record</span></li>
      <li><b>{N_REST:,}</b><span>restaurants</span></li>
    </ul>
  </section>

  <section id="what">
    <h2>Built around how Delaware eats</h2>
    <p class="sub">Star ratings won't tell you who still fries scrapple for breakfast, or which brewery pours its own beer with dinner. {BRAND} is organized the way people here eat: {e(join_words([GUIDE_NAME[k].lower().replace("wilmington", "Wilmington") for k in L]))}, each place checked in {CHECKED} against a 2025–26 source. Every listed restaurant the state inspected shows the Division of Public Health's own record, never a grade from us, and Apple Maps' live card supplies ratings, hours and photos.</p>
  </section>

  <section id="how">
    <h2>How it works</h2>
    <ol class="steps">
      <li class="step"><div class="n" aria-hidden="true">1</div><div><h3>Start with a craving.</h3><p>{e(join_words([GUIDE_NAME[k] for k in L] + ["James Beard Honors", "Health Inspections"], "or"))}. Or type a name, a town, a street or a dish to search the {N_REST:,} we list.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">2</div><div><h3>Find the closest one.</h3><p>Put the nearest first, narrow it to one town or one kind of food, or pan the map from Claymont to Fenwick Island.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">3</div><div><h3>Head out.</h3><p>Check today's hours and photos on Apple Maps' card, call ahead, get directions, or save the place for your next beach weekend.</p></div></li>
    </ol>
  </section>
{screens}
  <section id="guides">
    <h2>Delaware food guides</h2>
    <p class="sub">Each of the app's lists with at least four places has its own page here, free to read.</p>
    <div class="grid2">
      {guide_cards}
      {f'<a class="card gc gc-oldest" href="/{OLD_PATH}"><b>{len(OLD_L)}</b><h3>Delaware&#39;s oldest restaurants</h3><p>{plural(len(OLD_L), "place")} open at the same address since 1960 or earlier.</p></a>' if HAS_OLD else ""}
      <a class="card gc gc-honors" href="/{HON_PATH}"><b>{len(HON_L)}</b><h3>James Beard honors</h3><p>{plural(len(HON_L), "honored Delaware restaurant")}.</p></a>
      <a class="card" href="/{INS_PATH}"><h3>Delaware restaurant inspections, explained</h3><p>What the Division of Public Health publishes, and the latest routine inspection for {plural(len(INS_L), "place")}.</p></a>
    </div>
  </section>

  <section id="cities">
    <h2>Scrapple, crabs and more by town</h2>
    <p class="sub">The towns with enough hand-checked or honored places for a page of their own. The <a href="/cities/">cities and towns index</a> sums up what's on each.</p>
    <ul class="cities">{city_cards}</ul>
  </section>

  <section id="pricing">
    <h2>Free, with no catch</h2>
    <p class="sub">The app costs nothing, shows no ads and sells nothing inside, and there's no account to make. The lists ship inside the app, so they open right away and keep working when the signal drops out on Route 1 in August.</p>
  </section>

  <section id="privacy">
    <h2>What stays on your phone</h2>
    <p class="sub">{BRAND} collects nothing about you: no sign-in, no analytics, no ads. Location, if you turn it on, only puts the nearest places first, and your saved places are kept on the phone or iPad. The website has no cookies and no trackers. <a href="/privacy.html">The privacy policy</a> has the details.</p>
  </section>

  <section id="faq">
    <h2>Questions</h2>
    {faq_html}
  </section>

  <section id="download" class="final">
    <h2>Find your next scrapple breakfast</h2>
    <p class="sub">The iPhone and iPad app is almost here, and it's free. Ask for early access.</p>
    <div class="cta-row">{store_button()}</div>
  </section>
  </main>"""
page("index.html", title, desc, body, [app_ld, faq_ld], og_type="website")

# ---------------------------------------------------------------- privacy and terms
nav, bc = crumbs([("Home", "/"), ("Privacy policy", "/privacy.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Privacy policy</h1>
    <p class="lede">Short version: the {BRAND} app collects nothing about you, and this website doesn't track you. Last updated {PRIVACY_UPDATED}.</p>
  </section>
  <section>
    <h2>The app</h2>
    <ul>
      <li><b>No account, no analytics, no ads.</b> The app has no sign-in, no advertising and no analytics or crash-reporting code. We receive no data from it.</li>
      <li><b>Location.</b> If you allow it, your location is used on your device to sort places by distance and show where you are on the map. It is never sent to us. You can turn it off in Settings at any time.</li>
      <li><b>Saved places and filters</b> are stored only on your device and are deleted when you delete the app.</li>
      <li><b>Apple Maps.</b> When you open a place's ratings, hours and photos, or ask for directions, the app asks Apple Maps for that place. Apple handles that request under <a href="https://www.apple.com/legal/privacy/" rel="noopener">Apple's privacy policy</a>, as it does for any app that shows a map.</li>
      <li><b>Data updates.</b> When you open the app, it checks this website for newer restaurant data, at most once a day (or an hour later if a check didn't go through), and downloads it when there is some. These requests carry no location or identifiers. GitHub, which hosts this site, may keep standard server logs of them, as it does for any visit here.</li>
      <li><b>Spotlight.</b> The app adds its hand-checked and honored places to your device's search index so you can find them from Spotlight. That index stays on your device.</li>
      <li><b>Calls, websites and email</b> you start from a place open in the Phone app, your browser or Mail, and are handled by them.</li>
    </ul>
    <p>When the app is on the App Store, its privacy label will be "Data Not Collected".</p>
    <h2>This website</h2>
    <p>The site is static pages hosted on GitHub Pages. It sets no cookies and loads no analytics, fonts or scripts from anyone else.</p>
    <ul>
      <li><b>Saved places and your last guide.</b> The search page (<a href="/explore/">/explore/</a>) keeps the places you save and the last guide you opened in your browser's local storage, on this device only, under the keys {join_words([f"<code>{STORAGE_PREFIX}{k}</code>" for k in JS_KEYS])}. Nothing is sent to us. Clearing this site's data in your browser removes them.</li>
      <li><b>Location.</b> If you tap Near me or choose the Nearest sort, your browser asks whether to share your location. If you allow it, the location is used only inside your browser to sort places by distance and is never sent to us or anyone else.</li>
    </ul>
    <p>GitHub may keep standard server logs, such as IP addresses, for security; see <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">GitHub's privacy statement</a>.</p>
    <h2>Email</h2>
    <p>If you email us, we use your message and address only to reply and to fix the listing you told us about. We don't add you to a mailing list or share your address. Mail to {EMAIL} reaches our inbox through Cloudflare Email Routing; see <a href="https://www.cloudflare.com/privacypolicy/" rel="noopener">Cloudflare's privacy policy</a>.</p>
    <h2>Children</h2>
    <p>The app collects no personal information from anyone, including children.</p>
    <h2>Changes and contact</h2>
    <p>If this policy changes, the new version will be posted here with a new date. Questions: <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
  </section>
  </main>"""
page("privacy.html", "Delaware Eats Privacy Policy: No Tracking, No Accounts",
     fit(["How Delaware Eats treats your data: the iPhone app collects none, your location and saved places stay on your device, and this site uses no cookies.",
          "How Delaware Eats treats your data: the app collects none, your location and saved places stay on your device, and this site has no cookies or trackers."], 140, 160),
     body, [bc])

nav, bc = crumbs([("Home", "/"), ("Terms of use", "/terms.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Terms of use</h1>
    <p class="lede">The plain-language terms for the {BRAND} app and this website. Last updated {POLICY_UPDATED}.</p>
  </section>
  <section>
    <h2>What the app is</h2>
    <p>{BRAND} is a free guide to restaurants in Delaware. It is provided as is, for personal use, without charge and without warranties of any kind.</p>
    <h2>Check before you go</h2>
    <p>Restaurants open, close, change their hours and change their menus, and many beach-town places and creameries close for the winter or keep short hours. Dishes and founding years are what each place or a named source said when we checked in {CHECKED}. We work to keep the lists right, but we can't promise that any listing is current or complete. Call the restaurant before you make the trip.</p>
    <h2>Inspection results and public records</h2>
    <p>The app and this site show the Delaware Division of Public Health's inspection records as it publishes them: each inspection's date and type and the Food Code sections cited, with the number cited at a place's latest routine inspection. Delaware has no restaurant grade, score or placard, and we compute none. An inspection is a snapshot of one day. Business licenses come from the Delaware Division of Revenue; a license shows a business is licensed, not that it's open. The agencies provide their data as is and make no warranty of its accuracy or completeness. For official records, ask the agency itself: DPH's Office of Food Protection is at 302-744-4546.</p>
    <h2>Other people's content</h2>
    <p>Ratings, reviews, hours and photos in each place card come from Apple Maps and are Apple's and its providers', under Apple's terms. Restaurant names and trademarks belong to their owners. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. {BRAND} is not affiliated with any restaurant, chain, award body or government agency.</p>
    <h2>Data sources and licenses</h2>
    <ul>
      <li>Delaware Department of Health and Social Services, Division of Public Health, Office of Food Protection, Food Establishment Inspection Violations (data.delaware.gov), public domain, modified for use here.</li>
      <li>Delaware Department of Finance, Division of Revenue, Delaware Business Licenses (data.delaware.gov), public domain; owners' legal names are not shown.</li>
      <li>Overture Maps Foundation places data, under the Community Data License Agreement, Permissive 2.0, including data from Meta, Microsoft, DAC, BrightQuery, AllThePlaces (CC0 1.0) and Foursquare (Apache 2.0).</li>
      <li>Overture Maps Foundation divisions, used for the state and county outlines on the map, under the Open Database License: © OpenStreetMap contributors, Overture Maps Foundation.</li>
      <li>The James Beard Foundation's Restaurant and Chef Awards (semifinalists and finalists): honors reported as facts.</li>
      <li>The scrapple, Wilmington Italian, farm creamery, brewpub, crab house, boardwalk and other food lists, and founding years: our own research, with a source recorded for every place.</li>
    </ul>
    <h2>Corrections</h2>
    <p>If a listing is wrong, or you own a restaurant and want something fixed, email <a href="mailto:{EMAIL}">{EMAIL}</a>. We fix mistakes in the next update.</p>
    <h2>Liability</h2>
    <p>To the extent the law allows, we are not liable for any loss arising from use of the app or site, including a wasted drive to a closed restaurant.</p>
    <h2>Changes</h2>
    <p>We may update these terms; the current version and its date are always on this page. See also the <a href="/privacy.html">privacy policy</a>.</p>
  </section>
  </main>"""
page("terms.html", "Delaware Eats Terms of Use: A Free Guide, Provided As Is",
     fit(["The terms for Delaware Eats and this site: a free guide provided as is, public records shown as the agencies published them, and how to report a mistake.",
          "The terms for Delaware Eats and this website: a free guide provided as is, state records shown as published, and how to report a mistake to us."], 140, 160),
     body, [bc])

body = f"""  <main id="main">
  <section class="hero">
    <h1>Page not found</h1>
    <p class="lede">No page lives at this address. Head back to the <a href="/">{BRAND} home page</a>, the <a href="/{GUIDE_PATH['scrapple']}">scrapple list</a> or the <a href="/explore/">Delaware restaurant search</a>.</p>
  </section>
  </main>"""
page("404.html", f"Not found: {BRAND}", "No page lives at this address.", body, robots="noindex,follow")
noindexed.remove("404.html")


# ---------------------------------------------------------------- plumbing
for f in os.listdir(f"{DOCS}/cities"):   # a city the data lost: drop its old page instead of leaving it live and stale
    if f.endswith(".html") and f"cities/{f}" not in written + noindexed:
        os.remove(f"{DOCS}/cities/{f}")
        print("removed stale", f"cities/{f}")
urls = ["" if w == "index.html" else w.replace("index.html", "") for w in written]
urls.sort(key=lambda u: (u != "", u.startswith("cities/"), u))
open(f"{DOCS}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                       + "".join(f"  <url><loc>{DOMAIN}/{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(f"{DOCS}/robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")
json.dump({"name": BRAND, "short_name": "Delaware Eats", "description": f"{TAGLINE[0].upper() + TAGLINE[1:]}: a guide to {N_REST:,} Delaware restaurants.",
           "start_url": f"{BASE}/", "display": "browser", "background_color": "#f7f4ee", "theme_color": "#1f3b6f",
           "icons": [{"src": f"{BASE}/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": f"{BASE}/icon-512.png", "sizes": "512x512", "type": "image/png"}]},
          open(f"{DOCS}/site.webmanifest", "w"), indent=2)
if CUSTOM_DOMAIN:
    open(f"{DOCS}/CNAME", "w").write(CUSTOM_DOMAIN + "\n")
elif os.path.exists(f"{DOCS}/CNAME"):
    os.remove(f"{DOCS}/CNAME")   # no custom domain yet: GitHub serves the project address
open(f"{DOCS}/.nojekyll", "w").write("")
os.makedirs(f"{ROOT}/playbook", exist_ok=True)
json.dump({"generated": TODAY, "domain": DOMAIN, "restaurants": N_REST, "places_incl_hidden": len(PLACES), "towns": N_TOWNS, "counties": N_COUNTIES,
           "on_an_official_list": N_OFFICIAL, "dph_live": N_DPH, "rev_licenses": N_REV, "hand_checked_on_a_guide": N_HC,
           **{"guide_" + k: len(v) for k, v in L_ALL.items()}, "guide_pages": list(L), "oldest": len(OLD_L), "honors": len(HON_L), "james_beard": N_JBF,
           "inspection_records": len(INS_L), "sections_cited_latest_routine": {str(k): v for k, v in sorted(CITED_N.items())}, "inspections_through": INS_THROUGH,
           "city_pages": city_stats, "cities_without_a_page": CITY_SKIPPED, "noindex_pages": noindexed,
           "web_app_data_bytes": {k: {"raw": r, "gzip": g} for k, (r, g) in SIZES.items()}},
          open(f"{ROOT}/playbook/site-numbers.json", "w"), indent=1, ensure_ascii=False)
print("wrote", len(written) + len(noindexed) + 1, "pages:", ", ".join(written))
if noindexed:
    print("noindex:", ", ".join(noindexed))
print(f"restaurants {N_REST:,} in {N_TOWNS} towns | official {N_OFFICIAL:,} | hand-checked on a guide {N_HC} | "
      + " | ".join(f"{k} {len(v)}" for k, v in L_ALL.items()) + f" | oldest {len(OLD_L)} | honors {len(HON_L)} | DPH inspection records {len(INS_L):,}")
print("city pages:", ", ".join(CITY_PAGES), "| no page (listed places):", CITY_SKIPPED)
print(f"website blocklist: {len(BLOCKLIST)} entries, {len(BLOCKED_LINKS)} links dropped:", "; ".join(f"{n} {u}" for n, u in BLOCKED_LINKS) or "none")
for k, (r, g) in SIZES.items():
    print(f"  {k}: {r / 1024:,.0f} KB raw, {g / 1024:,.0f} KB gzip")
