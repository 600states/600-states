"""Forvarvssteget. Hamtar ett dygns raflode och fryser det som snapshot.

    python3 src/acquire.py <AAAAMMDD> [--budget N] [--force]

Tva kallor per dygn:
  96 st  GDELT 2.0 mentions, en fil per 15 minuter
   1 st  GDELT 1.0 events, dagsfil med 58 falt

KOMPLETTHETSGRINDEN, inte en fordrojning. Uppmatt pa pilotdata: samtliga
202 517 rader i ett dygns mentions-filer har MentionTimeDate exakt lika med
filens 15-minutersstampel. Det finns alltsa ingen sen instromning till ett
stangt UTC-dygn - mentions som indexeras efter midnatt hamnar i nasta dygns
filer och tillhor nasta dygn enligt Observation Day Rule.

Fragan ar darfor bara om alla 96 filer finns. Saknas nagon ar dygnet
ofullstandigt och det ska synas i manifestet, inte doljas.

IDEMPOTENS. Finns snapshotet och verifierar mot sitt manifest gor korningen
ingenting. All vidare bearbetning laser snapshotet, aldrig GDELT - en
omkorning om tio ar ger darfor samma resultat.

RESUMERBART. Hamtade filer mellanlagras per fil. Avbryts korningen tas bara
det som saknas vid nasta forsok. --budget begransar antalet hamtningar per
korning sa att steget far plats i ett kort tidsfonster.
"""
import hashlib, json, sys, time, urllib.error, urllib.request, zipfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
from atomic import write_text, write_bytes
from config import DATA, raw_day_dir

MENTIONS_BASE = "http://data.gdeltproject.org/gdeltv2/"
EVENTS_BASE   = "http://data.gdeltproject.org/events/"
UA      = "600STATES-archival/1.0 (research archival crawler; contact: archive@600states.com)"
SLOTS   = 96                      # 24h / 15 min
TIMEOUT = 60
RETRIES = 3

def slots(day):
    """De 96 15-minutersstamplarna for dygnet. Harledda, inte hamtade."""
    return [f"{day}{h:02d}{m:02d}00" for h in range(24) for m in (0, 15, 30, 45)]

def mentions_url(stamp): return f"{MENTIONS_BASE}{stamp}.mentions.CSV.zip"
def events_url(day):     return f"{EVENTS_BASE}{day}.export.CSV.zip"

def fetch(url):
    """Returnerar (bytes, None) eller (None, felbeskrivning). Ingen tyst tystnad."""
    last = None
    for n in range(RETRIES):
        try:
            rq = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(rq, timeout=TIMEOUT) as r:
                data = r.read()
            zipfile.ZipFile(__import__("io").BytesIO(data)).namelist()   # kastar om trasig
            return data, None
        except urllib.error.HTTPError as e:
            last = f"HTTP_{e.code}"
            if e.code == 404: break           # finns inte, meningslost att forsoka igen
        except Exception as e:
            last = type(e).__name__
        time.sleep(1.5 * (n + 1))
    return None, last

def work_dir(day):
    d = raw_day_dir(day) / "_work" / day
    d.mkdir(parents=True, exist_ok=True)
    return d

def snapshot_paths(day):
    d = raw_day_dir(day)
    return (d / f"600_STATES_{day}_GDELT2_MENTIONS.zip",
            d / f"{day}.export.CSV.zip",
            d / f"600_STATES_{day}_SNAPSHOT_MANIFEST.json")

def verify(day):
    """Sant om snapshotet finns och varje fil stammer mot manifestets sha256."""
    mz, ez, mf = snapshot_paths(day)
    if not (mz.exists() and ez.exists() and mf.exists()):
        return False, "snapshot saknas"
    man = json.loads(mf.read_text(encoding="utf-8"))
    for p, key in ((mz, "mentions_archive_sha256"), (ez, "events_sha256")):
        if hashlib.sha256(p.read_bytes()).hexdigest() != man.get(key):
            return False, f"{p.name} stammer inte mot manifestet"
    return True, f"{man['slots_present']}/{SLOTS} slots, status {man['status']}"

def acquire(day, budget=None, force=False):
    sp.state_id(day)                                   # validerar formatet
    if not force:
        ok, why = verify(day)
        if ok:
            print(f"  snapshotet finns och verifierar: {why}")
            return 0

    w = work_dir(day)
    need = [s for s in slots(day) if not (w / f"{s}.zip").exists()]
    print(f"  {SLOTS - len(need)}/{SLOTS} mentions redan hamtade, {len(need)} kvar")

    fel = {}
    hamtade = 0
    for s in need:
        if budget is not None and hamtade >= budget:
            print(f"  budget {budget} nadd, {len(need) - hamtade} kvar - kor steget igen")
            return 2
        data, err = fetch(mentions_url(s))
        hamtade += 1
        if data is None:
            fel[s] = err
            print(f"    {s}  {err}")
        else:
            write_bytes(w / f"{s}.zip", data)

    ev = w / f"{day}.export.CSV.zip"
    if not ev.exists():
        data, err = fetch(events_url(day))
        if data is None:
            print(f"  events-filen gick inte att hamta: {err}")
            return 3
        write_bytes(ev, data)

    have = [s for s in slots(day) if (w / f"{s}.zip").exists()]
    status = "COMPLETE" if len(have) == SLOTS else "INCOMPLETE_SOURCE"
    print(f"  {len(have)}/{SLOTS} mentions-filer, events-fil finns, status {status}")

    files = []
    for s in have:
        b = (w / f"{s}.zip").read_bytes()
        files.append({"timestamp_utc": f"{s[:4]}-{s[4:6]}-{s[6:8]}T{s[8:10]}:{s[10:12]}:00Z",
                      "filename": f"{s}.mentions.CSV.zip", "url": mentions_url(s),
                      "size_bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})

    mz, ez, mf = snapshot_paths(day)
    mz.parent.mkdir(parents=True, exist_ok=True)
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:   # inre filer ar redan komprimerade
        for s in have:
            z.writestr(f"{s}.mentions.CSV.zip", (w / f"{s}.zip").read_bytes())
    write_bytes(mz, buf.getvalue())
    write_bytes(ez, ev.read_bytes())

    man = {
        "project": "600 STATES", "state_id": sp.state_id(day), "date_utc": day,
        "status": status, "slots_expected": SLOTS, "slots_present": len(have),
        "missing_slots": {s: fel.get(s, "saknas") for s in slots(day) if s not in have},
        "mentions_archive": mz.name,
        "mentions_archive_sha256": hashlib.sha256(mz.read_bytes()).hexdigest(),
        "events_file": ez.name,
        "events_sha256": hashlib.sha256(ez.read_bytes()).hexdigest(),
        "source_base_url": MENTIONS_BASE, "events_base_url": EVENTS_BASE,
        "files": files,
        "note": ("Snapshotet ar fryst. All vidare bearbetning laser detta arkiv, aldrig GDELT. "
                 "MentionTimeDate ar alltid lika med filens 15-minutersstampel, sa dygnets "
                 "mentions ar exakt dessa filer."),
    }
    write_text(mf, json.dumps(man, ensure_ascii=False, indent=1))
    print(f"  {mz.name}  sha256 {man['mentions_archive_sha256'][:16]}")
    print(f"  {mf.name}")
    if status != "COMPLETE":
        print(f"  DYGNET AR OFULLSTANDIGT: {len(man['missing_slots'])} slots saknas")
        return 1
    return 0

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    day = sys.argv[1]
    a = sys.argv[2:]
    budget = int(a[a.index("--budget") + 1]) if "--budget" in a else None
    print(f"=== {sp.state_id(day)} — forvarv ===")
    sys.exit(acquire(day, budget, "--force" in a))

if __name__ == "__main__":
    main()
