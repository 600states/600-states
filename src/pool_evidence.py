"""Bevisfangst pa kandidatpoolen - fore urvalet.

Bevisfangsten hamtar sidan, och sidan bar rubriken. Rubriken ar
klassificerarens input. Darfor maste detta steg ligga fore urvalet, sa att de
600 kan valjas bland kandidater som faktiskt gar att lasa. Se FYND 003.

Cachen ar nycklad pa URL och delas mellan dygn: overlapp hamtas aldrig om.
Resumerbar - kan avbrytas och startas om.
"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_evidence import fetch_one, load_registry
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA

CACHE = DATA / "07_EVIDENCE" / "pool_titles.jsonl"

def load_cache(path=CACHE):
    out = {}
    if Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line); out[r["url"]] = r
    return out

def capture(pool, registry, budget=None, workers=12, path=CACHE):
    """Hamtar rubrik for de kandidater som saknas i cachen. Returnerar (nya, kvar)."""
    cache = load_cache(path)
    todo = [c for c in pool if c["url"] not in cache]
    if budget: todo = todo[:budget]
    if not todo:
        return 0, 0
    allowed = load_registry(registry)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        recs = list(ex.map(lambda c: fetch_one(c["url"], allowed), todo))
    with open(path, "a", encoding="utf-8") as fh:
        for r in recs:
            r.pop("_body", None)
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    cache = load_cache(path)
    return len(recs), sum(1 for c in pool if c["url"] not in cache)

def attach(pool, path=CACHE):
    """Satter page_title och evidence pa kandidaterna. Muterar posterna."""
    cache = load_cache(path)
    for c in pool:
        r = cache.get(c["url"], {})
        c["page_title"] = r.get("page_title") or ""
        c["http_status"] = r.get("http_status")
        c["content_sha256"] = r.get("content_sha256")
        c["evidence_retrieved_at"] = r.get("retrieved_at_utc")
    return pool

BEVISNIVAER = ("NO_EVIDENCE", "RETROSPECTIVE", "CONTEMPORANEOUS_ARCHIVE",
               "OBSERVED_AT_CAPTURE")

def basis(c, day):
    """Bevisnivan for EN kandidat i v3.0-vagen. day ar observationsdygnet, YYYYMMDD.

    GRANSEN FOR "UNDER OBSERVATIONSDYGNET" ar hamtningens kalenderdygn i UTC,
    jamfort med dygnet som hela kedjan redan ar parametriserad pa. Ingen
    tolerans at nagot hall: en sida last 00:04 dygnet efter ar hamtad efter
    dygnet, och det ar hela skillnaden v3.0 finns till for att gora.

    BEVISET AR DEN HASHADE SIDAN, inte forsoket. fetch_one stamplar
    retrieved_at_utc aven nar hamtningen misslyckas, sa tidsstampeln ensam
    sager bara nar vi lasade. Utan content_sha256 finns inget bevis att datera.

    capture_state.basis() hor till pilotvagen, kan inte na OBSERVED_AT_CAPTURE
    och anropas aldrig harifran. Se FYND 011.
    """
    t = c.get("evidence_retrieved_at")
    if not t or not c.get("content_sha256"):
        return "NO_EVIDENCE"
    d = datetime.fromisoformat(t)
    if d.tzinfo is None:
        # Utan tidszon skulle astimezone() tolka stampeln i maskinens lokala tid
        # och ge ett dygn som beror pa var programmet kors. Hellre stopp.
        raise ValueError(f"evidence_retrieved_at saknar tidszon: {t!r}")
    return ("OBSERVED_AT_CAPTURE"
            if d.astimezone(timezone.utc).strftime("%Y%m%d") == day
            else "RETROSPECTIVE")
