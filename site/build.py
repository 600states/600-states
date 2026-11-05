"""Bygger den publika sidan till en uppladdningsbar mapp.

    python site/build.py            -> site/dist
    python site/build.py <malmapp>  -> dit du pekar

Repot bar sidan, inte dess innehall. data.js och de fyra renderingarna
genereras hit ur dataarkivet vid varje bygge, av samma skal som resten av
koden: bevis ligger i bevisrepot och verken ar inte MIT-licensierade. Se
COPYRIGHT.md. Sokvagen till arkivet kommer ur STATES_DATA, aldrig hardkodad.

Malmappen blir exakt det som ska ligga i public_html. Ingenting annat.
"""
import io, json, os, re, shutil, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

HERE = Path(__file__).resolve().parent
DAYS = ["001", "002", "003", "004"]     # kalibreringsdygnen sidan visar
FIELD_DAY = "001"                       # dygnet bakom det klickbara faltet


def manifest_for(state_dir: Path, day: str) -> Path:
    """Nyaste konsensusmanifestet for dygnet. Versionen globbas: arkivet star
    pa v3.1 medan statepaths.py redan pekar pa v3.2, och sidan ska inte ga
    sonder pa den skillnaden."""
    found = sorted(state_dir.glob("600_STATES_2026_%s_EMOTION_COLOR_MANIFEST_v*_CONSENSUS.csv" % day))
    if not found:
        raise SystemExit("hittar inget konsensusmanifest i " + str(state_dir))
    return found[-1]


def render_for(state_dir: Path, day: str) -> Path:
    found = sorted(state_dir.glob("600_STATES_2026_%s_v*_CONSENSUS.png" % day))
    if not found:
        raise SystemExit("hittar ingen rendering i " + str(state_dir))
    return found[-1]


def build_data(data_root: Path, out: Path) -> None:
    """Skriver data.js: 600 rutor med farg, tolkning OCH kallan bakom.

    Kedjan nyhet -> observation -> emotion -> farg far aldrig kortas av, sa de
    tva kallorna joinas rad for rad och skriptet stannar hellre an skriver en
    halvriktig fil. En sida som pastar att varje ruta bar sitt eget bevis far
    inte skeppa en ruta vars bevis har flyttat."""
    state_dir = data_root / "08_V3_STATES" / ("STATE_" + FIELD_DAY)
    site_json = state_dir / ("site_%s.json" % FIELD_DAY)
    if not site_json.exists():
        raise SystemExit("saknas: " + str(site_json))

    site = json.load(io.open(site_json, encoding="utf-8"))
    site = site if isinstance(site, list) else (site.get("tiles") or list(site.values())[0])
    import csv
    manifest = list(csv.DictReader(io.open(manifest_for(state_dir, FIELD_DAY), encoding="utf-8")))

    if not (len(site) == len(manifest) == 600):
        raise SystemExit("vantade 600 rader i bada kallorna, fick %d och %d" % (len(site), len(manifest)))

    tiles = []
    for a, b in zip(site, manifest):
        if a["o"] != b["observation_id"] or a["h"] != b["hex"]:
            raise SystemExit("kallorna ar oense om ruta %s" % a.get("i"))
        if not a["u"].startswith(("http://", "https://")):
            raise SystemExit("ruta %s saknar anvandbar kall-URL" % a.get("i"))
        tiles.append([
            b["hex"],
            b["neutral_event_representation"].strip(),
            b["primary_emotion"],
            b["secondary_emotion"],
            b["primary_agreement"],
            round(float(b["intensity"]), 2),
            round(float(b["confidence"]), 2),
            b["classification_note"].strip(),
            a["u"], a["d"], a["t"], a["cs"], a["o"],
        ])

    agreement = {}
    for t in tiles:
        agreement[t[4]] = agreement.get(t[4], 0) + 1

    payload = {"tiles": tiles, "agreement": agreement,
               "distinct": len(set(t[0] for t in tiles)), "n": len(tiles)}
    with io.open(out / "data.js", "w", encoding="utf-8") as f:
        f.write("window.STATE001=")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("  data.js        %7d bytes  %s" % ((out / "data.js").stat().st_size, agreement))


def build_stamp() -> str:
    """Kort commit-hash, sa att den utrullade adressen sjalv kan sagas vilken
    version som ligger ute. Ett tillagg i tradet markeras, annars ljuger
    stampeln om vad som faktiskt byggdes."""
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(HERE),
                           capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=str(HERE),
                               capture_output=True, text=True, check=True).stdout.strip()
        return h + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def main(argv):
    if len(argv) > 2:
        raise SystemExit("anvandning: python site/build.py [malmapp]")
    # dist ligger i repot men utanfor git: det som laddas upp ska inte kunna
    # bytas ut av en filsynk mellan bygge och uppladdning
    out = Path(argv[1]).resolve() if len(argv) == 2 else (HERE / "dist")
    data_root = config.require_data()

    out.mkdir(parents=True, exist_ok=True)
    (out / "img").mkdir(exist_ok=True)

    stamp = build_stamp()
    html = io.open(HERE / "index.html", encoding="utf-8").read()
    html, n = re.subn(r'(<meta name="build" content=")[^"]*(">)', r"\g<1>" + stamp + r"\g<2>", html, count=1)
    if n != 1:
        raise SystemExit("hittar ingen byggstampel i index.html")
    io.open(out / "index.html", "w", encoding="utf-8").write(html)
    print("  index.html     %7d bytes  build=%s" % ((out / "index.html").stat().st_size, stamp))

    build_data(data_root, out)

    for day in DAYS:
        src = render_for(data_root / "08_V3_STATES" / ("STATE_" + day), day)
        dst = out / "img" / ("state_%s.png" % day)
        shutil.copyfile(src, dst)
        print("  img/%s  %7d bytes" % (dst.name, dst.stat().st_size))

    print("\nKlart: " + str(out))
    print("Ladda upp innehallet i mappen till /600states.com/public_html/ .")
    print("Mappen innehaller bara det som ska ut. Versaler spelar roll pa servern.")


if __name__ == "__main__":
    main(sys.argv)
