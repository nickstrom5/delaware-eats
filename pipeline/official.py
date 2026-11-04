"""Official records for Delaware -> one table of inspected and licensed food businesses.

The Division of Public Health's Office of Food Protection inspects every food establishment in the state (Delaware has no local health
departments; Wilmington's restaurants are DPH's too). Two state datasets on data.delaware.gov (see playbook/12-sources.md):
- "dph": "Food Establishment Inspection Violations" (384s-wygj, Public Domain, weekly, the past two years): one row per Food Code section
         cited at one inspection, or one row with no code for an inspection that cited nothing. No permit number, score, grade or
         priority flag. Establishments are its distinct (name, street address, zip) triples. Names read "DBA - legal entity - #store",
         cut at 50 characters; a closed one ends in "(Closed)".
- "rev": Division of Revenue "Delaware Business Licenses" (5zy2-grhr, Public Domain, daily, current licenses only), the "RETAILER
         RESTAURANT" business activity: trade name, legal name (never shown), license number, valid from/to and an address that can be a
         mailing one. Its points are zip-code centroids (the geocode uses Address 2, which is mostly empty): placed again here.

load() returns: jur, lic (our id), name, keys (name keys), addr, city, zip, num, street, lat, lon, kind, active, ltype, status.
kind: restaurant | bar | brewery | retail | venue | food | other.
"""
import os, re, json, glob, hashlib
import numpy as np, pandas as pd
from common import norm_name, RAW, name_sim, _stems, GENERIC, canon_city

OFF = os.path.join(RAW, "official")
DIRS = {"N": "N", "S": "S", "E": "E", "W": "W", "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}
TYPES = set("ST STREET AVE AV AVENUE BLVD BOULEVARD RD ROAD DR DRIVE LN LANE CT COURT PL PLACE PKWY PARKWAY TER TRL TRAIL WAY HWY CIR "
            "CIRCLE PLZ SQ MALL BND PASS XING RUN ROW WALK RDG LOOP FWY FREEWAY EXPY EXPRESSWAY PIKE".split())


def road(a):
    """One spelling for numbered roads: 'STATE ROUTE 1' = 'SR 1' = 'RT 1' = 'ROUTE 1' = 'DE-1' = 'DELAWARE 1'; 'US HIGHWAY 13' = 'US-13' =
    'US 13'; 'INTERSTATE 95' = 'I-95' = 'I 95'. Delaware has no county or township road numbers in addresses."""
    a = re.sub(r"(\d)\s*&\s*(\d)", r"\1-\2", a.upper())
    a = re.sub(r"\b(US|SR|DE|I)-(\w)", r"\1 \2", a)
    a = re.sub(r"\b(?:INTERSTATE(?: HIGHWAY| HWY)?|IH|I H)\s*(?=\d)", "I ", a)
    a = re.sub(r"\b(?:US|U S)\s+(?:HIGHWAY|HWY|ROUTE|RTE|RT)\b", "US", a)
    a = re.sub(r"\b(?:STATE (?:ROUTE|RTE|RT|HIGHWAY|HWY|ROAD|RD)|ST (?:ROUTE|RTE|RT)|DELAWARE (?:ROUTE|HIGHWAY|HWY|STATE ROUTE)|DE|DELAWARE|SR|ST RT|"
               r"ROUTE|RTE|RT)\b(?=\s*\d)", "SR", a)
    a = re.sub(r"\bHIGHWAY\b", "HWY", a)
    return re.sub(r"\b(US|SR|HWY|I) (\w+)\s*-\s*\w+", r"\1 \2", a)


ORD = {"FIRST": "1ST", "SECOND": "2ND", "THIRD": "3RD", "FOURTH": "4TH", "FIFTH": "5TH", "SIXTH": "6TH", "SEVENTH": "7TH",
       "EIGHTH": "8TH", "NINTH": "9TH", "TENTH": "10TH", "ELEVENTH": "11TH", "TWELFTH": "12TH"}


def street_key(a):
    """'2505 Monroe St' -> ('2505', 'MONROE'); '1000 OSAGE STREET' -> ('1000', 'OSAGE'); 'E Jefferson Ave' keeps 'JEFFERSON'."""
    if not isinstance(a, str):
        return None, None
    a = re.sub(r"[.,#]", " ", road(a))
    m = re.match(r"^\s*(\d+)[A-Z]?(?:\s*-\s*\d+[A-Z]?)?\s+(.*)$", a)
    if not m:
        return None, None
    words = [w for w in m.group(2).split() if w]
    # a unit letter between the number and the street ("50 C Wilmington Ave", DPH's way of writing unit C) isn't the street's name;
    # "100 A St" keeps its A (what's left would be only a street type)
    if len(words) > 2 and len(words[0]) == 1 and words[0] not in DIRS and words[1] not in TYPES:
        words = words[1:]
    if len(words) > 1 and words[0] in DIRS:
        words = words[1:]
    core = []
    for w in words:
        if w in TYPES and core:
            break
        core.append(w)
    core = [ORD.get(w, w) for w in core]
    return m.group(1), " ".join(core[:3]) or None


def street_compat(a, b):
    """Same street, or one is a whole-word prefix of the other (a record that truncates "1206 CENTAUR" = Centaur Village Dr)."""
    if not isinstance(a, str) or not isinstance(b, str) or not a or not b:
        return False
    return a == b or a.startswith(b + " ") or b.startswith(a + " ")


def street_nums(a):
    """'157-159 W Main St' -> {'157', '159'}; '2505 Monroe St' -> {'2505'}."""
    if not isinstance(a, str):
        return set()
    a = road(a)
    m = re.match(r"^\s*(\d+)[A-Z]?(?:\s*-\s*(\d+)[A-Z]?)?\s", a.upper() + " ")
    if not m:
        return set()
    lo = int(m.group(1)); hi = int(m.group(2)) if m.group(2) else lo
    if hi < lo:   # "1500-02"
        hi = int(str(lo)[: len(str(lo)) - len(m.group(2))] + m.group(2)) if m.group(2) else lo
    return {str(x) for x in range(lo, hi + 1, 2 if (hi - lo) % 2 == 0 else 1)} if 0 <= hi - lo <= 12 else {str(lo)}


def _names(*vals):
    out = []
    for v in vals:
        if not isinstance(v, str):
            continue
        v = re.sub(r"\s*\((?:MOBILE|MOBILE UNIT|COMMISSARY|CATERING|SPECIAL EVENT|SPEC EVENT|TEMP(?:ORARY)? EVENT|CP|INSIDE [^)]*)\)\s*$", "", v, flags=re.I)
        for part in re.split(r"\s*/\s*|\s+\bdba\b\s+|\s+&\s+(?=[A-Z][a-z])|\s*\(\s*|\s*\)\s*", v, flags=re.I):
            k = norm_name(re.sub(r"\b(?:LLC|INC|CORP|CORPORATION|LTD|CO)\b\.?", "", part, flags=re.I))
            if k and k not in out:
                out.append(k)
    return out


DPH_DATE = "2026-10-27"   # DPH inspections fetched (rows updated 2026-10-23; weekly)
REV_DATE = "2026-10-27"   # Revenue business licenses fetched (daily)
# Records through: the fetch date minus 7 days (the feed is weekly: 10/21 was its last day with rows, and 14 rows are dated Nov-Dec 2026,
# which are future dates, not inspections)
DPH_THROUGH = "2026-10-20"
# DPH inspects most places every 3 to 10 months (routine gaps: median 189 days, 90th percentile 398, measured 2026-10-27): an establishment
# with no inspection in the 18 months before DPH_THROUGH is out of DPH's rotation, so it can't stand alone as proof a place is open
DPH_STALE = "2025-04-20"


def _zip(z):
    z = re.sub(r"\D", "", str(z or ""))
    return z[:5] if len(z) >= 5 else ""


# school, hospital and institutional kitchens: never a restaurant, whatever else the name says. DPH also inspects mobile units (MOB),
# cottage and home kitchens (CWOP), and temporary stands under their own names.
OTHER = re.compile(r"\((?:MOB|MOBILE|CWOP|CWO|FE|TRAILER|TRUCK|CART|TEMP|COMMISSARY|CATERING|SPECIAL EVENT)\b|\b(?:SCHOOLS?|ELEMENTARY|ELEM|"
                   r"MIDDLE SCHOOL|HIGH SCHOOL|INTERMEDIATE|ACADEMY|PRESCHOOL|PRE SCHOOL|CHILDCARE|CHILD CARE|CHILD DEVELOPMENT|DAYCARE|"
                   r"DAY CARE|HEAD ?START|EARLY LEARNING|LEARNING CENTER|KINDERCARE|SCHOOL DIST\w*|HOSPITAL|DIETARY|NURSING|SENIOR|"
                   r"ASSISTED LIVING|REHABILITATION|PSYCHIATRIC|CORRECTIONAL|PRISON|DETENTION|YOUTH CENTER|FOOD BANK|MEALS ON WHEELS|SHELTER|"
                   r"CHURCH|PARISH|MINISTR(?:Y|IES)|CONGREGATION|BOARD OF EDUCATION|PTA|PTO|BOOSTERS?|FIRE (?:CO|COMPANY|HALL)|VFD|"
                   r"AMERICAN LEGION|VFW|ELKS|MOOSE|FRATERNAL|COUNTRY CLUB|GOLF|YMCA|BOYS AND GIRLS|CAMP|POOL|SWIM CLUB|DORM|"
                   r"DINING HALL|RESIDENCE HALL|FOOD SERVICES?|COMPASS GROUP|SODEXO|ARAMARK|ACELERO)\b", re.I)
OTHER_SOFT = re.compile(r"\b(?:MOBILE|FOOD TRUCK|TRUCK|TRAILER|CATERING|CATERER|COMMISSARY|CONCESSIONS?|SNACK BAR|SNACK SHACK|KIOSK|"
                        r"VENDING|STAND)\b", re.I)
FOODY = re.compile(r"\b(?:RESTAURANT|CAFE|CAFFE|GRILL|GRILLE|KITCHEN|PIZZA|PIZZERIA|TAVERN|PUB|BAR|DINER|BISTRO|EATERY|BBQ|DELI|"
                   r"BAKERY|COFFEE|TACOS?|TAQUERIA|BURGERS?|WINGS|SUSHI|STEAK\w*|SALOON|INN|BREWING|BREWERY|CRAB\w*|SEAFOOD)\b", re.I)
# grocery, convenience and drug stores, and the counters inside them ("Snowfox - Weis Markets 109" is a sushi counter in a Weis)
RETAIL = re.compile(r"\b(?:ACME|GIANT FOOD|GIANT\b|FOOD LION|WEIS|SAFEWAY|SHOPRITE|SHOP RITE|REDNERS?|WALMART|WAL MART|TARGET|COSTCO|"
                    r"SAMS CLUB|BJS WHOLESALE|ALDI|LIDL|WHOLE FOODS|TRADER JOES|SPROUTS|HARRIS TEETER|GROCERY|GROCERIES|SUPERMARKET|"
                    r"MARKET ?PLACE|FOOD MART|MINI ?MART|CONVENIENCE|7 ?ELEVEN|SEVEN ELEVEN|WAWA|ROYAL FARMS|SHEETZ|CUMBERLAND FARMS|"
                    r"SUNOCO|SHELL|EXXON|GETTY|VALERO|CITGO|GULF|BP|SPEEDWAY|DOLLAR GENERAL|FAMILY DOLLAR|DOLLAR TREE|CVS|WALGREENS|"
                    r"RITE AID|CARNICERIA|BUTCHER|MEAT MARKET|LIQUORS?|SPIRITS|BEER AND WINE|TOBACCO|SMOKE SHOP|VAPE|SNOWFOX|HISSHO)\b", re.I)




def _row(jur, lic, name, addr, city, z, la, lo, kind, active=True, ltype=None, holder=None, county=None, status=None):
    num, st = street_key(addr)
    if OTHER.search(name or "") or (OTHER_SOFT.search(name or "") and not FOODY.search(name or "")):
        kind = "other"
    elif RETAIL.search(norm_name(name or "")) and not FOODY.search(name or ""):
        kind = "retail"
    return {"jur": jur, "lic": lic, "name": name, "dba": name, "holder": holder, "keys": _names(name), "addr": addr, "city": city,
            "zip": _zip(z), "num": num, "street": st, "lat": la, "lon": lo, "kind": kind, "active": active, "ltype": ltype,
            "county": county, "status": status}


def latest(pattern):
    fs = sorted(glob.glob(f"{OFF}/{pattern}"))
    if not fs:
        raise FileNotFoundError(f"{OFF}/{pattern}: run fetch_official.py")
    return fs[-1]


LEGAL = re.compile(r"\b(?:LLC|L L C|INC|INCORPORATED|CORP|CORPORATION|CO|COMPANY|LTD|LP|LLP|PLLC|GROUP|HOLDINGS?|HOLD|ENTERPRISES?|"
                   r"HOSPITALITY|VENTURES|PARTNERS|MANAGEMENT|INVESTMENTS?|ASSOCIATES|CONCEPTS|PROPERTIES|DEVELOPMENT|SVCS|SERVICES|"
                   r"OPERATIONS|FRANCHIS\w*)\b", re.I)


def dph_name(raw):
    """DPH's establishment name -> (the name to show, closed?). "Mike & Mels Family Restaurant - MMW Restaurant I" shows the DBA only;
    "1776 Restaurant (Closed)" is closed; "Arenas Caf  5 Points" lost its accent and "DominickG  s Pizza" its apostrophe in DPH's export."""
    n = re.sub(r"\s+", " ", (raw or "").strip())
    closed = bool(re.search(r"\(\s*clos(?:ed?)?\s*\)?\s*$|-\s*\(?closed\)?\s*$|\(closed\s*\)", n, re.I))
    n = re.sub(r"\s*-?\s*\(\s*clos(?:ed?)?\s*\)?\s*", " ", n, flags=re.I).strip()
    n = re.sub(r"\s*\((?:clos|close)$", "", n, flags=re.I).strip()
    parts = [p.strip() for p in re.split(r"\s+-\s+", n) if p.strip()]
    if not parts:
        return "", closed
    dba = parts[0]
    # "Sussex Concessions LLC - Coastal Kitchen at Bear T": the company came first, the place second
    if len(parts) > 1 and LEGAL.search(dba) and not LEGAL.search(parts[1]) and not parts[1].startswith("#") and len(parts[1]) >= 6:
        dba = parts[1]
    dba = re.sub(r"\bCaf\+?(?=\s|$)", "Café", dba)
    dba = re.sub(r"\bCAF\+?(?=\s|$)", "CAFÉ", dba)
    dba = re.sub(r"(?<=[A-Za-z])G\s+s\b", "'s", dba)          # "DominickG  s" -> "Dominick's"
    dba = re.sub(r"\s*#\s*\w+$", "", dba).strip()
    dba = re.sub(r"\s*\((?:MOB|MOBILE|CWOP|CWO|FE|TRAILER|TRUCK|FT)\)\s*", " ", dba, flags=re.I).strip()
    return dba.strip(" -,&/"), closed


def _dph_raw():
    rows = json.load(open(latest("dph_inspections_*.json")))
    d = pd.DataFrame(rows)
    for c in ("restname", "restaddress", "restcity", "restzip", "violation", "vio_desc", "insp_type"):
        d[c] = d[c].fillna("") if c in d else ""
    d["d"] = d.insp_date.str[:10]
    d["zip5"] = d.restzip.map(_zip)
    d["estab"] = [hashlib.md5(f"{n.strip().upper()}|{a.strip().upper()}|{z}".encode()).hexdigest()[:10]
                  for n, a, z in zip(d.restname, d.restaddress, d.zip5)]
    d["la"] = [float(g["latitude"]) if isinstance(g, dict) and g.get("latitude") else np.nan for g in d.get("geocoded_column", [None] * len(d))]
    d["lo"] = [float(g["longitude"]) if isinstance(g, dict) and g.get("longitude") else np.nan for g in d.get("geocoded_column", [None] * len(d))]
    return d


def load_dph(d=None):
    """One row per DPH establishment (name, street address, zip): the name to show, its point and whether DPH marks it closed.
    Live = not "(Closed)" and inspected in the feed's window up to DPH_THROUGH."""
    d = _dph_raw() if d is None else d
    d = d[d.d <= DPH_THROUGH]
    rows = []
    for e, g in d.groupby("estab", sort=False):
        r = g.iloc[0]
        name, closed = dph_name(r.restname)
        la, lo = g.la.dropna(), g.lo.dropna()
        rows.append(_row("dph", "DPH-" + e, name, r.restaddress.strip(), canon_city(r.restcity), r.zip5,
                         float(la.iat[0]) if len(la) else np.nan, float(lo.iat[0]) if len(lo) else np.nan, "food",
                         active=not closed, ltype="Food establishment", status="Closed" if closed else None))
        rows[-1]["raw_name"] = r.restname
        rows[-1]["last"] = g.d.max()
        rows[-1]["first"] = g.d.min()
    return pd.DataFrame(rows)


def load_revenue():
    """One row per current RETAILER  RESTAURANT business license with a Delaware address. The trade name is the name; a license with
    no trade name keeps the legal name for matching only (never shown: it can be a person's name)."""
    rows = []
    for x in json.load(open(latest("revenue_restaurant_*.json"))):
        if (x.get("state") or "").strip().upper() != "DE":
            continue   # an out-of-state mailing address says nothing about where the restaurant is
        trade = re.sub(r"\s+", " ", (x.get("trade_name") or "").strip())
        legal = re.sub(r"\s+", " ", (x.get("business_name") or "").strip())
        addr = " ".join(p for p in ((x.get("address_1") or "").strip(), (x.get("address_2") or "").strip()) if p)
        # "PO BOX 123" is a mailing address: the license matches by name in its town, never by street
        if re.match(r"(?i)^\s*(?:P\.?\s*O\.?\s*BOX|POST OFFICE BOX|BOX\s+\d)", addr):
            addr = ""
        row = _row("rev", "REV-" + str(x.get("license_number")), trade, addr, canon_city(x.get("city")), x.get("zip"), np.nan, np.nan,
                   "restaurant", active=(x.get("current_license_valid_to") or "")[:10] >= REV_DATE, ltype="Retailer - Restaurant",
                   holder=legal)
        row["keys"] = _names(trade) or _names(legal)
        row["named"] = bool(trade)
        row["valid_to"] = (x.get("current_license_valid_to") or "")[:10] or None
        row["valid_from"] = (x.get("current_license_valid_from") or "")[:10] or None
        row["license_number"] = str(x.get("license_number"))
        rows.append(row)
    return pd.DataFrame(rows)


def load():
    df = pd.concat([load_dph(), load_revenue()], ignore_index=True)
    # one business can hold several records (a DPH establishment and its Revenue license; two DPH names for one kitchen after a
    # rename): same address and a name in common
    df["biz"] = np.arange(len(df))
    town = df.city.fillna("").str.upper().str.strip()
    for num, g in df[df.num.notna() & df.street.notna()].groupby("num"):
        idx = list(g.index)
        if len(idx) < 2 or len(idx) > 400:
            continue
        for x in range(len(idx)):
            for y in range(x + 1, len(idx)):
                a, b = idx[x], idx[y]
                if not street_compat(df.at[a, "street"], df.at[b, "street"]):
                    continue
                if not ((df.at[a, "zip"] and df.at[a, "zip"] == df.at[b, "zip"]) or (town[a] and town[a] == town[b])):
                    continue
                ka, kb = df.at[a, "keys"], df.at[b, "keys"]
                if not ka or not kb:
                    continue
                if any(name_sim(p, q) >= 85 or ((_stems(p) - GENERIC) & (_stems(q) - GENERIC)) for p in ka for q in kb):
                    old, new = df.at[b, "biz"], df.at[a, "biz"]
                    df.loc[df.biz == old, "biz"] = new
    return df


# ---------------------------------------------------------------- DPH inspections: the Food Code sections cited, never a grade of ours
# Each row is one Food Code section cited at one inspection (vio_desc is the section's title, "6-501.111 Controlling Pests", not what
# the inspector saw), or one row with no code for an inspection that cited nothing. An inspection is its (establishment, date, type).
# Types: Routine, Follow-up, Complaint. DPH publishes no score, grade, result or priority flag: the app shows the date, the type and
# the sections cited, word for word, and counts sections, never "critical" ones.
def dph_inspections(d=None):
    """One row per inspection up to DPH_THROUGH: establishment id, date, type, the number of distinct sections cited and their codes and
    titles. Oldest first."""
    d = _dph_raw() if d is None else d
    d = d[(d.d <= DPH_THROUGH) & d.d.ne("")]
    g = d.groupby(["estab", "d", "insp_type"]).agg(
        n=("violation", lambda x: len({v for v in x if v})),
        codes=("violation", lambda x: sorted({v for v in x if v}, key=lambda c: [int(p) if p.isdigit() else 0 for p in re.split(r"[-.]", c)])),
    ).reset_index()
    titles = {v: t for v, t in zip(d.violation, d.vio_desc) if v}
    g["items"] = g.codes.map(lambda cs: [[c, titles.get(c, "")] for c in cs])
    g["lic"] = "DPH-" + g.estab
    g = g.rename(columns={"insp_type": "typ"})
    return g.sort_values(["lic", "d"]).reset_index(drop=True)


def section_titles(d=None):
    d = _dph_raw() if d is None else d
    return {v: t for v, t in zip(d.violation, d.vio_desc) if v}
