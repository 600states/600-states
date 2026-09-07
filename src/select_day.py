"""Kvotmotorn — fran kandidatpool till exakt 600 frusna observationer.

Helt deterministisk. Ingen modell. Ordningen ar:

  1. storytak (N=1, troskel 0,25) — ett informationstillstand, en ruta
  2. REGIONAL 240  — exakt 30 per region. FORST, for det ar den harda
                     bivillkoret: tunna regioner far annars inget kvar
                     nar GLOBAL redan tagit toppen.
  3. GLOBAL 300    — dygnets storsta berattelser, oavsett region
  4. DISCOVERY 60  — ur den tystare svansen, jamnt fordelat, sa att rutnatet
                     inte bara bestar av de hogljuddaste nyheterna
  5. publisher cap 10 galler over hela urvalet
  6. kronologisk ordning -> tile_index 1..600

Rangordningssignal: mention_rows (uppmatt som enda starkt separerande signal).
"""
import hashlib, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from story_cap import apply_cap, near_duplicates, tokens, DEFAULT_N, DEFAULT_THRESHOLD

REGIONS = ["Africa", "East & Southeast Asia", "Europe", "Latin America & Caribbean",
           "Middle East & North Africa", "North America", "Oceania & Pacific", "South & Central Asia"]
N_TOTAL, N_GLOBAL, N_REGIONAL, N_DISCOVERY = 600, 300, 240, 60
PER_REGION = N_REGIONAL // len(REGIONS)          # 30
PUBLISHER_CAP = 10
REGISTRY_VERSION = "v2.0"

def _rank(c):
    return (-c["mention_rows"], c["first_mention_utc"], c["url"])

def _take(pool, want, used_dom, predicate=None, step=1):
    out = []
    idx = 0
    items = [c for c in pool if predicate is None or predicate(c)]
    while len(out) < want and idx < len(items):
        c = items[idx]; idx += step if step > 1 else 1
        if used_dom.get(c["domain"], 0) >= PUBLISHER_CAP:
            continue
        out.append(c); used_dom[c["domain"]] = used_dom.get(c["domain"], 0) + 1
    if len(out) < want and step > 1:                 # svansen tog slut, fyll tatt
        for c in items:
            if len(out) >= want: break
            if c in out: continue
            if used_dom.get(c["domain"], 0) >= PUBLISHER_CAP: continue
            out.append(c); used_dom[c["domain"]] = used_dom.get(c["domain"], 0) + 1
    return out

def _slug_text(c):
    """Rubrik nar den finns, annars URL:ens sokvag som ord."""
    if c.get("page_title"):
        return c["page_title"]
    path = re.sub(r"^https?://[^/]+", "", c["url"])
    path = re.sub(r"[?#].*$", "", path)
    return " ".join(w for w in re.split(r"[^a-zA-Z0-9]+", path) if not w.isdigit())


def select(cands, state_id, text_of=_slug_text):
    """Returnerar (valda 600, rapport)."""
    ranked = sorted(cands, key=_rank)
    kept, dropped = apply_cap(ranked, text_of, lambda c: c["first_mention_utc"],
                              n=DEFAULT_N, threshold=DEFAULT_THRESHOLD)
    kept = sorted(kept, key=_rank)
    near = near_duplicates(kept, text_of)

    used_dom, chosen, taken = {}, [], set()

    region_report = {}
    for reg in REGIONS:
        r = _take(kept, PER_REGION, used_dom,
                  lambda c, reg=reg: c["review_region"] == reg and c["url"] not in taken)
        for c in r: c["selection_layer"] = "REGIONAL"; taken.add(c["url"])
        chosen += r
        region_report[reg] = len(r)

    g = _take(kept, N_GLOBAL, used_dom, lambda c: c["url"] not in taken)
    for c in g: c["selection_layer"] = "GLOBAL"; taken.add(c["url"])
    chosen += g

    tail = [c for c in kept if c["url"] not in taken]
    step = max(1, len(tail) // N_DISCOVERY) if tail else 1
    d = _take(tail, N_DISCOVERY, used_dom, lambda c: c["url"] not in taken, step=step)
    for c in d: c["selection_layer"] = "DISCOVERY"; taken.add(c["url"])
    chosen += d

    chosen.sort(key=lambda c: (c["first_mention_utc"], c["url"]))
    for i, c in enumerate(chosen, 1):
        c["state_id"] = state_id
        c["tile_index"] = i
        c["grid_row"] = (i - 1) // 30 + 1
        c["grid_column"] = (i - 1) % 30 + 1
        c["registry_version"] = REGISTRY_VERSION
        sig = " ".join(sorted(tokens(text_of(c))))
        c["family_key"] = "F3-" + hashlib.sha256(sig.encode()).hexdigest()[:16].upper()
        c["observation_id"] = "OBS-" + hashlib.sha256(
            f"{state_id}|{c['family_key']}|{c['url']}|{c['first_mention_utc']}".encode()
        ).hexdigest()[:16].upper()

    report = {"kandidater": len(cands), "efter_storytak": len(kept), "bortsorterade_av_tak": len(dropped),
              "near_duplicate_observed": len(near), "valda": len(chosen),
              "per_layer": {L: sum(1 for c in chosen if c["selection_layer"] == L)
                            for L in ("GLOBAL", "REGIONAL", "DISCOVERY")},
              "regional_per_region": region_report,
              "unika_urler": len({c["url"] for c in chosen}),
              "unika_observation_id": len({c["observation_id"] for c in chosen}),
              "max_per_publicist": max((sum(1 for c in chosen if c["domain"] == d)
                                        for d in {c["domain"] for c in chosen}), default=0),
              "unika_domaner": len({c["domain"] for c in chosen})}
    return chosen, report, near
