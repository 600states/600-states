"""Rubrikcache — url -> page_title. Aterbrukas over dygn och korningar.

Rubriken behovs for klustringen (FYND 002: URL-slug racker inte). Cachen ar
resumerbar och delas mellan dygn, sa samma sida hamtas aldrig tva ganger.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch_evidence import fetch_many, load_registry
from config import DATA

CACHE = DATA / "07_EVIDENCE" / "title_cache.jsonl"
from config import REGISTRY_FILE as REGISTRY   # se config.py - enda definitionen

def load():
    out = {}
    if CACHE.exists():
        for line in CACHE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line); out[r["url"]] = r
    return out

def ensure(urls, limit=None, workers=10):
    have = load()
    todo = [u for u in urls if u not in have]
    if limit: todo = todo[:limit]
    if not todo:
        return have, 0
    allowed = load_registry(REGISTRY)
    res = fetch_many(todo, allowed=allowed, workers=workers)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE, "a", encoding="utf-8") as fh:
        for r in res:
            r.pop("_body", None)
            rec = {"url": r["url"], "page_title": r.get("page_title", ""),
                   "http_status": r.get("http_status"), "content_sha256": r.get("content_sha256"),
                   "retrieved_at_utc": r.get("retrieved_at_utc"), "error": r.get("error")}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            have[r["url"]] = rec
    return have, len(res)
