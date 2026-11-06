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


TALORD = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
          "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
          "nineteen": 19, "twenty": 20}


def gate_hjaltens_rakning(html: str) -> int:
    """Siffran i hjalten ska vara lika med antalet kapitel pa sidan.

    Sidan pastod "wrong eleven times" och listade tio kapitel. Felet ar inte
    siffran utan att ingenting kunde fanga den: en rakning i en rubrik ar ett
    pastaende som vem som helst kan kontrollera, och det fanns ingen kontroll.
    Att lamna den ogrindad pa just den har sidan vore att upprepa kapitel IV,
    "The check that could not fail".

    Returnerar antalet kapitel. Faller med besked om de inte stammer."""
    kapitel = len(re.findall(r'<p class="ch-num">[IVXLC]+</p>', html))
    lead = re.search(r'<p class="lead">(.*?)</p>', html, re.S)
    if not lead:
        raise SystemExit("hittar ingen <p class=\"lead\"> att rakna mot")
    ord_ = re.search(r"\b(%s)\b" % "|".join(TALORD), lead.group(1))
    if not ord_:
        raise SystemExit("hjalten innehaller inget talord ur ordboken: "
                         + lead.group(1)[:80])
    sagt = TALORD[ord_.group(1)]
    if sagt != kapitel:
        raise SystemExit(
            "hjalten sager %s (%d) men sidan har %d kapitel — "
            "andra ordet eller kapitlen, bygget stoppas"
            % (ord_.group(1), sagt, kapitel))
    return kapitel


def cirkel_ur_verket(src: Path, storlek: int):
    """En cirkel ur verket: diametern ar verkets fulla hojd, centrerad i bredd.

    Faltet ar 30x20 rutor, alltsa bredare an hogt. Cirkeln tar hela hojden och
    skar lika mycket fran bada sidorna, sa att mitten av verket ar mitten av
    market. Masken ritas i fyrdubbel skala och krymps, annars blir kanten
    trappstegsformad vid 16 px.
    """
    from PIL import Image, ImageDraw
    im = Image.open(src).convert("RGB")
    w, h = im.size
    kvadrat = im.crop(((w - h) // 2, 0, (w - h) // 2 + h, h)).resize(
        (storlek, storlek), Image.LANCZOS)
    mask = Image.new("L", (storlek * 4, storlek * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, storlek * 4 - 1, storlek * 4 - 1), fill=255)
    kvadrat.putalpha(mask.resize((storlek, storlek), Image.LANCZOS))
    return kvadrat


def build_favicon(data_root: Path, out: Path):
    """Markena genereras ur verket vid varje bygge, som data.js och
    renderingarna: de ar harledda ur arkivet och hor darfor inte i git."""
    src = render_for(data_root / "08_V3_STATES" / "STATE_001", "001")
    ico = out / "favicon.ico"
    cirkel_ur_verket(src, 48).save(ico, sizes=[(16, 16), (32, 32), (48, 48)])
    # Apple visar ingen genomskinlighet, den blir svart. Lagg cirkeln pa
    # sidans egen bakgrund i stallet for att lata systemet valja.
    from PIL import Image
    platta = Image.new("RGB", (180, 180), (10, 10, 11))
    c = cirkel_ur_verket(src, 180)
    platta.paste(c, (0, 0), c)
    apple = out / "apple-touch-icon.png"
    platta.save(apple)
    for f in (ico, apple):
        print("  %-14s %7d bytes" % (f.name, f.stat().st_size))


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


def gate_rent_trad(out: Path, stamp: str) -> None:
    """UPPLADDNINGSMAPPEN FAR INTE INNEHALLA ETT SMUTSIGT BYGGE.

    Felet som gav upphov till grinden, 2026-11-06: bygget kordes fore
    commiten, stampeln blev "9a1f3ba-dirty", och filerna lag kvar i dist
    redo att laddas upp. En sida som pastar sig byggd ur ingen kand commit
    hor inte hemma pa en sajt vars hela tes ar sparbarhet - och stampeln
    finns just for att den sidan ska kunna bindas till en version.

    RATT ORDNING AR COMMITTA, BYGG, LADDA UPP. Grinden gor ordningen till en
    regel i stallet for nagot man ska komma ihag.

    Den galler bara standardmappen. Vill du forhandsgranska ett opaverkat
    trad finns malmappsargumentet sedan tidigare:

        python site/build.py ..\forhandsvisning

    Det bygget far behalla sin -dirty-stampel. Det ar inte till servern.
    """
    if not stamp.endswith("-dirty"):
        return
    if out.resolve() != (HERE / "dist").resolve():
        print("  NOTERA smutsigt trad: stampeln blir %s. Bygget gar till en egen"
              " mapp och ska inte laddas upp." % stamp)
        return
    raise SystemExit(
        "smutsigt trad: stampeln skulle bli %s och bygget hamna i dist.\n"
        "  Committa forst, bygg sedan. Vill du bara titta:\n"
        "    python site/build.py <nagon annan mapp>" % stamp)


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
    gate_rent_trad(out, stamp)
    # Varje sida stamplas, och en sida utan stampel faller bygget: en sida som
    # inte gar att binda till en version ar inte sparbar, och det ar hela
    # skalet till att stampeln finns.
    for sida in ("index.html", "labs.html"):
        html = io.open(HERE / sida, encoding="utf-8").read()
        html, n = re.subn(r'(<meta name="build" content=")[^"]*(">)', r"\g<1>" + stamp + r"\g<2>", html, count=1)
        if n != 1:
            raise SystemExit("hittar ingen byggstampel i " + sida)
        if sida == "labs.html":
            kap = gate_hjaltens_rakning(html)
            print("  %-14s %d kapitel, hjaltens rakning stammer" % ("grind:", kap))
        # newline="\n": utan den oversatter Python \n till CRLF pa Windows, och
        # med core.autocrlf=true i arbetstradet blev den utrullade filens bytes
        # beroende av vilken maskin som byggde. Servern ar Unix och det som
        # ligger ute ar LF.
        io.open(out / sida, "w", encoding="utf-8", newline="\n").write(html)
        print("  %-14s %7d bytes  build=%s" % (sida, (out / sida).stat().st_size, stamp))

    build_data(data_root, out)

    build_favicon(data_root, out)

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
