"""Lager 1 — kandidatbyggare (deterministisk, ingen modell).

Fran raflodet for ett UTC-dygn till en kandidatpool av mojliga observationer.
Tar INGA materialitetsbeslut; det ar lager 2 (se FYND 002).
"""
import csv, io, json, re, sys, zipfile, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA, RAW_GDELT, REGISTRY_FILE, raw_day_dir
from gdelt import iter_mentions

REGISTRY = REGISTRY_FILE     # se config.py - enda definitionen
REGION_MAP = json.loads((Path(__file__).resolve().parents[1] / "data/region_map.json").read_text())

# GDELT 1.0 Events, 58 falt
E_ID, E_ACTIONGEO_COUNTRY, E_SOURCEURL = 0, 51, 57

def load_registry():
    with open(REGISTRY, encoding="utf-8") as fh:
        return {r["domain"].strip().lower(): r["source_tier"].strip() for r in csv.DictReader(fh)}

def events_zip(day):
    """Nya dygn ligger i arssnapshotet, pilotdygnen i den gamla mappen."""
    for p in (raw_day_dir(day) / f"{day}.export.CSV.zip", RAW_GDELT / f"{day}.export.CSV.zip"):
        if p.exists():
            return p
    raise SystemExit(f"hittar ingen events-fil for {day}")

def load_events(day):
    """eventid -> ActionGeo_CountryCode"""
    z = zipfile.ZipFile(events_zip(day))
    geo = {}
    with z.open(z.namelist()[0]) as fh:
        for line in io.TextIOWrapper(fh, encoding="utf-8", errors="replace"):
            f = line.rstrip("\n").split("\t")
            if len(f) >= 58:
                geo[f[E_ID]] = f[E_ACTIONGEO_COUNTRY].strip()
    return geo

def norm_domain(d):
    return re.sub(r"^www\.", "", (d or "").strip().lower())

def domain_of(url):
    """Doman ur URL:en, inte ur MentionSourceName. Manifesten anvander URL-varden,
    och GDELT:s MentionSourceName avviker for en del sajter (t.ex. mobilvarianter)."""
    m = re.match(r"https?://([^/]+)", url or "", re.I)
    return norm_domain(m.group(1)) if m else ""

def regioner(docs, day):
    """Skriver action_geo_country och review_region pa posterna. Muterar dem.

    EGET STEG, inte en del av build(). Events-dagsfilen ar den enda kallan till
    land, och den publiceras timmar efter att dygnet stangde - uppmatt
    2026-11-21: 404 till 07:45 UTC, 200 kl. 08:00, stampel 07:00. Kandidatbygget
    far darfor inte rora den, annars kan ingenting goras fore morgonen.
    """
    geo = load_events(day)
    for d in docs:
        countries = [geo[e] for e in d["event_ids"] if geo.get(e)]
        c = collections.Counter(countries).most_common(1)
        d["action_geo_country"] = c[0][0] if c else ""
        d["review_region"] = REGION_MAP.get(d["action_geo_country"], "UNMAPPED")
    return docs

def build(day, mentions_zip):
    """Kandidatpoolen ur mentions ensamt. Inget Events, alltsa inget land.

    Uppmatt 2026-11-21 pa 20261120: 3 786 kandidater med och utan Events,
    samma URL-mangd, samma mention_rows. Landet tillfor inget till poolens
    storlek - det ar en egenskap pa posten, och den satts av regioner().
    """
    reg = load_registry()

    docs = {}   # url -> post
    for m in iter_mentions(mentions_zip):
        if not m["MentionTimeDate"].startswith(day):
            continue
        url = m["MentionIdentifier"]
        dom = domain_of(url)
        if dom not in reg:
            dom2 = norm_domain(m["MentionSourceName"])
            if dom2 not in reg:
                continue
            dom = dom2
        d = docs.get(url)
        if d is None:
            d = docs[url] = {"url": url, "domain": dom, "source_tier": reg[dom],
                             "event_ids": set(), "mention_rows": 0,
                             "first_mention_utc": m["MentionTimeDate"]}
        d["event_ids"].add(m["GlobalEventID"])
        d["mention_rows"] += 1
        if m["MentionTimeDate"] < d["first_mention_utc"]:
            d["first_mention_utc"] = m["MentionTimeDate"]

    for d in docs.values():
        d["event_ids"] = sorted(d["event_ids"])
    return list(docs.values())

if __name__ == "__main__":
    day = sys.argv[1]
    mz = RAW_GDELT / (sys.argv[2] if len(sys.argv) > 2 else f"600_STATES_{day}_GDELT2_MENTIONS.zip")
    cands = regioner(build(day, mz), day)
    print(f"dygn {day}: {len(cands):,} kandidatdokument fran {len({c['domain'] for c in cands})} domaner")
    r = collections.Counter(c["review_region"] for c in cands)
    for k, v in r.most_common():
        print(f"   {k:32s} {v:5d}")
