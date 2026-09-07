"""Reparationspass for bevisfangst. Idempotent: kan koras om.

1) Poster som spärrades av domängrinden hämtas om (grinden var fel, inte URL:en).
2) Poster utan levande hämtning far sin rubrik fran Wayback-snapshoten,
   sa att klassificerarens input blir publicistens satta rubrik och inte URL-slugen.

Ingen modell ar inblandad. Ra bytes -> SHA-256.
"""
import json, sys, zipfile, urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_evidence import fetch_one, load_registry, UA, _title
from capture_state import REGISTRY, basis
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA

def archive_title(rec):
    u = rec.get("archive_url")
    if not u: return None
    try:
        req = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
        with urllib.request.urlopen(req, timeout=25) as r:
            return _title(r.read(4_000_000))
    except Exception:
        return None

def run(state, day, ids):
    out = DATA / "07_EVIDENCE" / f"STATE_{state}"
    jl, zp = out / "evidence.jsonl", out / "snapshots.zip"
    recs, order = {}, []
    for line in jl.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r = json.loads(line)
        if r["observation_id"] not in recs: order.append(r["observation_id"])
        recs[r["observation_id"]] = r

    mine = [recs[i] for i in ids if i in recs]
    gated = [r for r in mine if (r.get("error") or "").startswith("DOMAN")]
    notitle = [r for r in mine if not r.get("page_title") and r.get("archive_url")]
    allowed = load_registry(REGISTRY)

    bodies = {}
    if gated:
        def refetch(r):
            new = fetch_one(r["url"], allowed)
            body = new.pop("_body", None)
            if new.get("http_status") != 200:
                new["archive_url"], new["archive_timestamp"] = r.get("archive_url"), r.get("archive_timestamp")
            for k in ("observation_id", "tile_index", "state_id"): new[k] = r[k]
            new["evidence_basis"] = basis(new, day)
            return new, body
        with ThreadPoolExecutor(max_workers=8) as ex:
            for new, body in ex.map(refetch, gated):
                if body: bodies[new["content_sha256"]] = body
                recs[new["observation_id"]] = new

    if notitle:
        with ThreadPoolExecutor(max_workers=10) as ex:
            for r, t in zip(notitle, ex.map(archive_title, notitle)):
                if t:
                    r["page_title"] = t
                    r["title_source"] = "ARCHIVE_SNAPSHOT"
                    recs[r["observation_id"]] = r

    if bodies:
        with zipfile.ZipFile(zp, "a", zipfile.ZIP_DEFLATED) as z:
            have = set(z.namelist())
            for h, b in bodies.items():
                if f"{h}.html" not in have: z.writestr(f"{h}.html", b)
    for r in recs.values():
        r.setdefault("title_source", "LIVE_FETCH" if r.get("page_title") else "")
    jl.write_text("".join(json.dumps(recs[i], ensure_ascii=False) + "\n" for i in order), encoding="utf-8")
    print(f"refetched {len(gated)} gated, recovered {sum(1 for r in notitle if r.get('page_title'))}/{len(notitle)} archive titles")

if __name__ == "__main__":
    import csv
    state, day, manifest = sys.argv[1], sys.argv[2], sys.argv[3]
    ids = [r["observation_id"] for r in csv.DictReader(open(manifest, encoding="utf-8"))]
    run(state, day, ids)
