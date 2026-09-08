"""Bevisfangst pa kandidatpoolen - fore urvalet.

Bevisfangsten hamtar sidan, och sidan bar rubriken. Rubriken ar
klassificerarens input. Darfor maste detta steg ligga fore urvalet, sa att de
600 kan valjas bland kandidater som faktiskt gar att lasa. Se FYND 003.

Cachen ar nycklad pa URL och delas mellan dygn: overlapp hamtas aldrig om.
Resumerbar - kan avbrytas och startas om.
"""
import json, sys
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
