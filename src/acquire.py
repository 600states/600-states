"""Forvarvssteget. Hamtar ett dygns raflode och fryser det som snapshot.

    python3 src/acquire.py [AAAAMMDD] [--budget N] [--force] [--vanta-events]

Utan dygn tas det UTC-dygn som senast stangde, harlett med samma funktion som
run_state anvander. Dygnet som argument ar arkiv- och reparationsvagen.

Tva kallor per dygn:
  96 st  GDELT 2.0 mentions, en fil per 15 minuter
   1 st  GDELT 1.0 events, dagsfil med 58 falt

TVA OMGANGAR, FOR KALLORNA PUBLICERAS VID OLIKA TID. Mentions-filerna finns
nar dygnet stangt; Events-dagsfilen kommer timmar senare. Uppmatt 2026-11-21
pa dygnet 20261120: HEAD var 15:e minut fran 23:00 UTC gav 404 i 36 forsok
till och med 07:45 och 200 kl. 08:00:02, med Last-Modified 07:00:11 GMT -
alltsa en timme mellan filens egen stampel och att den gick att hamta.

Forsta anropet fryser de 96 mentions-filerna som ett eget snapshot med
status MENTIONS_FROZEN. Andra anropet hamtar Events, hashar in den i SAMMA
snapshotpost och flyttar status till COMPLETE. Det som frystes i forsta
omgangen ror det andra anropet aldrig: mentions-arkivets hash och dess
tidsstampel star kvar. Sommen mellan omgangarna ar inte dold - manifestet
bar en tidsstampel per del, och den som laser posten ser att dygnets raflode
blev fardigt i tva steg.

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
from datetime import datetime, timezone
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

# VANTAN PA EVENTS. Bada talen star har, pa ett stalle, och ingen starttid ar
# hardkodad: vi har ETT dygns matning av nar filen dyker upp, och ett schema
# byggt pa den enda natten skulle gora GDELT:s publiceringstid till var metod.
# Korningen fragar i stallet om tills filen finns.
#
# 5 minuter: ett 404-forsok ar en halv sekund, och tio minuters onodig vantan
# kostar mer an 48 forfragningar. 4 timmar: det enda uppmatta utfallet ar
# 08:00, och taket ska rymma en korning som startar fore det och en
# publicering som drojer langre an den natten - utan att en korning som aldrig
# far sin fil kan ligga kvar hela dygnet. Taket ar det som far korningen att
# falla; forsta 404 ar det inte.
EVENTS_INTERVALL_S = 300
EVENTS_TAK_S       = 4 * 3600

def nu_utc():
    """Hamtningens tidpunkt. TREDJE KLOCKAVLASNINGEN I KEDJAN, se AGENTS.md.

    Den valjer inget dygn - det gor statepaths.senast_stangda_dygnet, och bara
    nar main() inte fick nagot - utan mater nar en fil som inte fanns forut blev
    atkomlig. Samma sort som fetch_evidence.retrieved_at_utc.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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
    """Sant om snapshotet finns och varje FRYST fil stammer mot manifestets sha256.

    Events provas bara nar manifestet sager att den ar fryst. Ett snapshot i
    MENTIONS_FROZEN ar ett helt och giltigt snapshot av det som fanns att frysa
    vid 00:05; att krava events_sha256 har var det som gjorde en korning fore
    GDELT:s publicering omojlig.
    """
    mz, ez, mf = snapshot_paths(day)
    if not (mz.exists() and mf.exists()):
        return False, "snapshot saknas"
    man = json.loads(mf.read_text(encoding="utf-8"))
    prov = [(mz, "mentions_archive_sha256")]
    if man.get("events_sha256"):
        if not ez.exists():
            return False, f"{ez.name} saknas men star i manifestet"
        prov.append((ez, "events_sha256"))
    for p, key in prov:
        if hashlib.sha256(p.read_bytes()).hexdigest() != man.get(key):
            return False, f"{p.name} stammer inte mot manifestet"
    return True, f"{man['slots_present']}/{SLOTS} slots, status {man['status']}"

def hamta_events(day, vanta):
    """(bytes, sista_404_utc, fel). Med vanta=True gors forsoket om tills filen
    finns eller taket nas.

    sista_404_utc bracketar nar filen blev atkomlig: tillsammans med
    events_frozen_at_utc sager manifestet "fanns inte da, fanns nu", vilket ar
    sa nara en matning av publiceringstiden vi kommer utifran.
    """
    sista404 = None
    slut = time.monotonic() + EVENTS_TAK_S
    while True:
        data, err = fetch(events_url(day))
        if data is not None:
            return data, sista404, None
        if not vanta or time.monotonic() >= slut:
            return None, sista404, err
        sista404 = nu_utc()
        print(f"    events {err} {sista404} - forsoker igen om {EVENTS_INTERVALL_S // 60} min")
        time.sleep(EVENTS_INTERVALL_S)

def frys_events(day, vanta=False):
    """Andra omgangen. Hashar in Events i den befintliga snapshotposten.

    Den rader inte en enda rad som forsta omgangen skrev: mentions-arkivets
    hash, dess filista och dess tidsstampel lases och skrivs tillbaka som de ar.
    """
    mz, ez, mf = snapshot_paths(day)
    man = json.loads(mf.read_text(encoding="utf-8"))
    cache = work_dir(day) / f"{day}.export.CSV.zip"
    sista404 = None
    if cache.exists():
        data = cache.read_bytes()
    else:
        data, sista404, err = hamta_events(day, vanta)
        if data is None:
            print(f"  events-filen gick inte att hamta: {err}"
                  + (f" - gav upp efter {EVENTS_TAK_S // 3600} h"
                     if vanta else " - kor steget igen med --vanta-events"))
            return 3 if vanta else 0
        write_bytes(cache, data)
    write_bytes(ez, data)
    man["events_file"] = ez.name
    man["events_sha256"] = hashlib.sha256(data).hexdigest()
    man["events_frozen_at_utc"] = nu_utc()
    man["events_last_404_utc"] = sista404
    man["status"] = "COMPLETE" if man["slots_present"] == SLOTS else "INCOMPLETE_SOURCE"
    write_text(mf, json.dumps(man, ensure_ascii=False, indent=1))
    print(f"  {ez.name}  sha256 {man['events_sha256'][:16]}  hamtad {man['events_frozen_at_utc']}"
          + (f" (404 annu {sista404})" if sista404 else ""))
    print(f"  status {man['status']}")
    return 0

def acquire(day, budget=None, force=False, vanta_events=False):
    sp.state_id(day)                                   # validerar formatet
    if not force:
        ok, why = verify(day)
        if ok:
            print(f"  snapshotet finns och verifierar: {why}")
            man = json.loads(snapshot_paths(day)[2].read_text(encoding="utf-8"))
            if man.get("events_sha256"):
                return 0
            # Mentions ar frysta sedan forsta omgangen. Bara Events aterstar.
            return frys_events(day, vanta_events) or (
                0 if man["slots_present"] == SLOTS else 1)

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

    have = [s for s in slots(day) if (w / f"{s}.zip").exists()]
    print(f"  {len(have)}/{SLOTS} mentions-filer, status MENTIONS_FROZEN")

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

    man = {
        "project": "600 STATES", "state_id": sp.state_id(day), "date_utc": day,
        # MENTIONS_FROZEN: de 96 filerna ar frysta, Events ar inte hamtad an.
        # COMPLETE och INCOMPLETE_SOURCE betyder bada att BADA kallorna ligger i
        # posten; skillnaden mellan dem ar om nagon av de 96 slotsen saknas.
        "status": "MENTIONS_FROZEN", "slots_expected": SLOTS, "slots_present": len(have),
        "missing_slots": {s: fel.get(s, "saknas") for s in slots(day) if s not in have},
        "mentions_archive": mz.name,
        "mentions_archive_sha256": hashlib.sha256(mz.read_bytes()).hexdigest(),
        "mentions_frozen_at_utc": nu_utc(),
        "events_file": None, "events_sha256": None,
        "events_frozen_at_utc": None, "events_last_404_utc": None,
        "source_base_url": MENTIONS_BASE, "events_base_url": EVENTS_BASE,
        "files": files,
        "note": ("Snapshotet ar fryst. All vidare bearbetning laser detta arkiv, aldrig GDELT. "
                 "MentionTimeDate ar alltid lika med filens 15-minutersstampel, sa dygnets "
                 "mentions ar exakt dessa filer. Mentions och Events fryses i var sin omgang "
                 "och bar var sin tidsstampel - Events-dagsfilen publiceras timmar efter att "
                 "dygnet stangde."),
    }
    write_text(mf, json.dumps(man, ensure_ascii=False, indent=1))
    print(f"  {mz.name}  sha256 {man['mentions_archive_sha256'][:16]}")
    print(f"  {mf.name}  fryst {man['mentions_frozen_at_utc']}")

    rc = frys_events(day, vanta_events)
    if len(have) != SLOTS:
        print(f"  DYGNET AR OFULLSTANDIGT: {len(man['missing_slots'])} slots saknas")
        return rc or 1
    return rc

def main():
    a = sys.argv[1:]
    if "--help" in a or "-h" in a:
        sys.exit(__doc__)
    # HARLETT LAGE, samma regel som run_state: forsta argumentet ar ett dygn
    # bara om det inte ar en flagga. Utan den provade --vanta-events att vara
    # ett datum, och den dagliga korningen kunde inte anropa acquire alls.
    harlett = not a or a[0].startswith("-")
    day = sp.senast_stangda_dygnet(datetime.now(timezone.utc)) if harlett else a.pop(0)
    sp.state_id(day)                      # validerar formatet, kastar vid fel
    budget = int(a[a.index("--budget") + 1]) if "--budget" in a else None
    print(f"=== {sp.state_id(day)} — forvarv ==="
          + ("  (dygnet harlett ur klockan)" if harlett else ""))
    sys.exit(acquire(day, budget, "--force" in a, "--vanta-events" in a))

if __name__ == "__main__":
    main()
