"""Kor bevisfangst for en State. Resumerbar: kan avbrytas och startas om.

Utdata per State i datamappen:
  07_EVIDENCE/STATE_XXX/evidence.jsonl   - en post per observation
  07_EVIDENCE/STATE_XXX/snapshots.zip    - ra HTML, namngiven efter content_sha256

Snapshots ligger i zip for att halla filantalet nere (600/dygn x hundratals dygn).
Ingen modell ar inblandad. Ra bytes -> SHA-256.
"""
import csv, json, sys, zipfile, urllib.request, socket, hashlib
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_evidence import fetch_one, load_registry, UA
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA

from config import REGISTRY_FILE as REGISTRY

def wayback(url, day):
    api = f"https://archive.org/wayback/available?url={urllib.request.quote(url, safe='')}&timestamp={day}"
    try:
        req = urllib.request.Request(api, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            s = json.load(r).get("archived_snapshots", {}).get("closest")
        if s and s.get("available"):
            return s.get("url"), s.get("timestamp")
    except Exception:
        pass
    return None, None

def basis(rec, day):
    """Tre nivaer, se bevisspec v0.2 + matning 2026-09-07."""
    if rec.get("http_status") == 200:
        return "RETROSPECTIVE"          # hamtad idag, inte under observationsdygnet
    ts = rec.get("archive_timestamp") or ""
    if not rec.get("archive_url"):
        return "NO_EVIDENCE"
    return "CONTEMPORANEOUS_ARCHIVE" if ts.startswith(day[:6]) else "RETROSPECTIVE"

def run(manifest, state, day, limit=None, workers=10):
    out = DATA / "07_EVIDENCE" / f"STATE_{state}"
    out.mkdir(parents=True, exist_ok=True)
    jl, zp = out / "evidence.jsonl", out / "snapshots.zip"

    done = set()
    if jl.exists():
        for line in jl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["observation_id"])

    rows = list(csv.DictReader(open(manifest, encoding="utf-8")))
    todo = [r for r in rows if r["observation_id"] not in done]
    if limit: todo = todo[:limit]
    if not todo:
        print(f"STATE_{state}: klart, {len(done)}/{len(rows)} poster"); return len(done), len(rows)

    allowed = load_registry(REGISTRY)
    def work(r):
        rec = fetch_one(r["representative_url"], allowed)
        body = rec.pop("_body", None)
        if rec.get("http_status") != 200:
            u, ts = wayback(r["representative_url"], day)
            rec["archive_url"], rec["archive_timestamp"] = u, ts
        rec["observation_id"] = r["observation_id"]
        rec["tile_index"] = r["tile_index"]
        rec["state_id"] = r["state_id"]
        rec["evidence_basis"] = basis(rec, day)
        return rec, body

    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(work, todo))

    with zipfile.ZipFile(zp, "a", zipfile.ZIP_DEFLATED) as z:
        have = set(z.namelist())
        with open(jl, "a", encoding="utf-8") as fh:
            for rec, body in results:
                if body:
                    n = f"{rec['content_sha256']}.html"
                    if n not in have:
                        z.writestr(n, body); have.add(n)
                    rec["snapshot_path"] = n
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    tot = len(done) + len(results)
    print(f"STATE_{state}: +{len(results)} -> {tot}/{len(rows)}")
    return tot, len(rows)

if __name__ == "__main__":
    manifest, state, day = sys.argv[1], sys.argv[2], sys.argv[3]
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else None
    run(manifest, state, day, limit)
