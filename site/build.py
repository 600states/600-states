"""Bygger den publika sidan till en uppladdningsbar mapp.

    python site/build.py            -> site/dist
    python site/build.py <malmapp>  -> dit du pekar

Repot bar sidan, inte dess innehall. data.js och de fyra renderingarna
genereras hit ur dataarkivet vid varje bygge, av samma skal som resten av
koden: bevis ligger i bevisrepot och verken ar inte MIT-licensierade. Se
COPYRIGHT.md. Sokvagen till arkivet kommer ur STATES_DATA, aldrig hardkodad.

Malmappen blir exakt det som ska ligga i public_html. Ingenting annat.
"""
import html as html_mod
import io, json, os, re, shutil, subprocess, sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config
import statepaths as sp
import pool_evidence

HERE = Path(__file__).resolve().parent


def _d(day: str) -> date:
    """YYYYMMDD -> datum. Samma strang som kedjan raknar sina dygn ur."""
    return datetime.strptime(day, "%Y%m%d").date()

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


# Dygnet bakom talet pa 600 LABS. Ett annat dygn an faltets, sa talet kan inte
# lasas ur data.js payload - det raknas ur dygnets eget manifest, pa samma falt.
# Dygnet star ocksa i spannets namn i labs.html: andras konstanten harunder utan
# att prosan foljer med, hittar bygget inget span och stannar. Det ar avsikten.
LABS_DAY = "308"
LABS_DIR = "STATE_2026_308"

# Kalibreringsverket med en egen sida och en egen adress. Dygnet ar INTE ett
# seriedygn och far darfor inte ligga i startsidans falt: faltet ar dygn 001 och
# tre av sidans tal raknas ur det. Tva dygn i samma widget vore tvetydigheten
# tillbaka. Nyckeln ar arkivets katalognamn, dygnet det som star i filnamnen.
SIDA_315 = "state-2026-315.html"
NYCKEL_315 = "2026_315"
DYGN_315 = "315"

# SERIENS FORSTA DYGN far en egen sida, byggd som 315:s: en kallfil, tre
# konstanter har och en datafil. Ingen mall, ingen arkivlista och ingen
# slinga - generaliseringen gors nar det finns en handfull dygn att
# generalisera ur, inte pa ett.
#
# DYGNET STAR EN GANG. Nyckeln och ordningstalet raknas ur det med samma
# funktioner som kedjan bygger sina filnamn med; tre stavningar av samma
# dygn vore FYND 004 i datumform.
DAG_335 = "20261201"
NYCKEL_335 = sp.state_key(DAG_335)
DYGN_335 = "%03d" % sp.ordinal(DAG_335)
SIDA_335 = "state-2026-335.html"


def distinkta_farger(data_root: Path, day: str, katalog: str) -> int:
    """Distinkta hexvarden i ett dygns konsensusmanifest."""
    import csv
    m = manifest_for(data_root / "08_V3_STATES" / katalog, day)
    rader = list(csv.DictReader(io.open(m, encoding="utf-8", newline="")))
    if len(rader) != 600:
        raise SystemExit("vantade 600 rader i %s, fick %d" % (m.name, len(rader)))
    return len({r["hex"].strip().lower() for r in rader})


def reproducerar(data_root: Path, nyckel: str, day: str) -> int:
    """Hur manga av dygnets 600 rutor fargprotokollet raknar fram pa nytt.

    Sidan for 2026/315 pastar att fargen reproducerar. Talet raknas darfor vid
    varje bygge, ur det frysta manifestet i arkivet, med samma funktion som
    renderar - aldrig skrivet for hand. Slutar dygnet reproducera sager sidan
    det sjalv i stallet for att fortsatta pasta motsatsen.

    Samma falt som tests/test_color_protocol.py provar for dygn 001: kolumnen
    hex i det frysta manifestet, mot hex_of_row ur de fyra protokollfalten.
    """
    import csv
    sys.path.insert(0, str(HERE.parent / "src"))
    from color_protocol import hex_of_row
    m = manifest_for(data_root / "08_V3_STATES" / ("STATE_" + nyckel), day)
    rader = list(csv.DictReader(io.open(m, encoding="utf-8", newline="")))
    if len(rader) != 600:
        raise SystemExit("vantade 600 rader i %s, fick %d" % (m.name, len(rader)))
    return sum(1 for r in rader if hex_of_row(r).upper() == r["hex"].upper())


def render_for(state_dir: Path, day: str) -> Path:
    found = sorted(state_dir.glob("600_STATES_2026_%s_v*_CONSENSUS.png" % day))
    if not found:
        raise SystemExit("hittar ingen rendering i " + str(state_dir))
    return found[-1]


def _block(html: str, namn: str):
    """Ett element markt data-when-<namn>, med sin indragning.

    Fyra taggar racker, och de ar de fyra sidan faktiskt bar ett
    pastaende i: ett stycke, ett block, en mening inne i ett stycke och
    en punkt i en lista. Ett anspraak som star mitt i en mening ska inte
    behova en egen rubrik for att ga att valja bort."""
    return re.search(r"[ \t]*<(p|div|span|li)\b[^>]*\bdata-when-%s\b[^>]*>.*?</\1>\n?"
                     % namn, html, re.S)


def valj(html: str, sida: str, aktiv, alternativ) -> str:
    """Behall ETT av sidans data-when-block och ta bort de ovriga.

    BADA TEXTERNA STAR I KALLFILEN. Ett seriedygn kan bli CANONICAL eller
    UNQUALIFIED och vilket det blir vet ingen i forvag; en sida som bara bar
    det ena utfallet publicerar ett osant pastaende den dag dygnet gar den
    andra vagen. Bygget VALJER darfor mellan texter som gar att lasa i
    kallfilen, i stallet for att satta ihop en mening sjalvt - en mening som
    bara finns i bygget gar inte att granska dar sidan skrivs.

    Samma mekanism bar bevislaget, som ar tre tillstand och inte tva, och
    signaturen, som ar ett eget bevis i en egen post.

    aktiv=None tar bort alla alternativ. Saknas ett block stannar bygget: ett
    bortfallet block ar ett utfall sidan inte langre kan uttrycka, och det ska
    inte ga att tappa bort tyst.

    shortcut: grinden kraver ETT block per utfall, inte varje forekomst. Star
    samma utfall pa tva stallen och det ena tas bort byggs sidan anda, med
    utfallet sagt en gang i stallet for tva. Uppgradera den dagen sidan har
    fler an tva utfall att halla reda pa, eller nar ett bortfall har kostat
    nagot - en rakning per namn i bygget vore sidans layout skriven har.
    """
    for namn in alternativ:
        if not _block(html, namn):
            raise SystemExit("hittar inget data-when-%s-block i %s - sidan kan "
                             "inte langre saga det utfallet" % (namn, sida))
    # ALLA forekomster, inte den forsta: ett utfall kan behova sagas bade i
    # ingressen och i brodtexten, och ett kvarlamnat block vore sidan som
    # pastar bada utfallen samtidigt.
    for namn in alternativ:
        while True:
            m = _block(html, namn)
            if not m:
                break
            behall = re.sub(r"\s+data-when-%s\b" % namn, "", m.group(0)) if namn == aktiv else ""
            html = html[:m.start()] + behall + html[m.end():]
    return html


def fyll(html: str, sida: str, namn: str, varde) -> str:
    """Ett span i kallfilen, ifyllt av bygget. Samma form som data-tests."""
    html, n = re.subn(r"(<span data-%s>)[^<]*(</span>)" % namn,
                      lambda m: m.group(1) + str(varde) + m.group(2), html, count=1)
    if n != 1:
        raise SystemExit("hittar ingen plats for %s i %s" % (namn, sida))
    return html


def luckans_logg(dygn: str) -> str:
    """Forsta raden i _LUCKOR.log som namner dygnet, eller tom strang.

    LOGGEN BLIR LAST HAR. Den har skrivits av varje korning A sedan den kom
    till och lasts av ingenting - en logg utan lasare ar en fil, inte en
    matning. Arkivet svarar pa OM det finns en lucka; loggen svarar pa NAR
    den sags och av vilken korning, och det ar den uppgiften en publicerad
    mening om ett forlorat dygn behover for att ga att folja.
    """
    if not config.LUCKLOGG.exists():
        return ""
    # LUCKANS DYGN, INTE KORNINGENS. Raden lyder "... korning 20261122
    # luckor 1: 20261121", och ett blott `dygn in rad` matchade korningens
    # eget datum - alltsa sa loggen att den sett en lucka den aldrig
    # rapporterat. Bara listan efter kolonet raknas.
    for rad in io.open(config.LUCKLOGG, encoding="utf-8"):
        m = re.search(r"luckor \d+: (.*)$", rad)
        if m and dygn in [x.strip() for x in m.group(1).split(",")]:
            return rad.strip()
    return ""


def gate_obruten_produktion(data_root: Path, html: str, sida: str) -> str:
    """Sidan far inte pasta obruten produktion medan en lucka finns.

    GRINDEN STOPPAR INTE BYGGET. Ett tappat dygn fylls aldrig - dygnet har
    passerat - sa en grind som vagrade bygga pa en lucka hade gjort sajten
    opublicerbar for alltid, vilket ar samma form som felet A27a rattade:
    ett forlorat dygn som blir en forlorad serie. Grinden byter i stallet ut
    pastaendet mot ett som ar sant, och bada texterna star i kallfilen.

    TRE TILLSTAND, INTE TVA:

      ingen lucka                 anspraaket star kvar
      lucka som loggen sett       luckmeningen, med radens tid och korning
      lucka som loggen INTE sett  luckmeningen, och ett eget besked om att
                                  loggen tiger. Det ar inte ett fel och
                                  faller inte: en utebliven korning A har
                                  inte skrivit nagon rad, och att vagra
                                  publicera da vore att lata en utebliven
                                  korning stoppa utgivningen.

    Dygnet SJALVT raknas inte - nattens korning har inte skett nar bygget
    gors - och det foljer av att luckor() stannar vid dygnet fore.
    """
    idag = datetime.now(timezone.utc).strftime("%Y%m%d")
    luckor = pool_evidence.luckor(data_root, idag)
    html = valj(html, sida, "lucka" if luckor else "obruten", ("obruten", "lucka"))
    if not luckor:
        print("  %-14s inga luckor efter %s" % ("produktion:", pool_evidence.SERIESTART))
        return html

    html = fyll(html, sida, "missed",
                "%d day%s" % (len(luckor), "" if len(luckor) == 1 else "s"))
    html = fyll(html, sida, "missed-days",
                ", ".join("%s-%s-%s" % (d[:4], d[4:6], d[6:]) for d in luckor))
    print("  %-14s %d lucka/luckor: %s" % ("produktion:", len(luckor), ", ".join(luckor)))
    for dygn in luckor:
        rad = luckans_logg(dygn)
        print("                 %s: %s" % (dygn, rad if rad else
                                           "ARKIVET HAR LUCKAN, LOGGEN HAR INTE SETT DEN"))
    return html


def dygnet_finns(data_root: Path, day: str, nyckel: str, dygn: str) -> bool:
    """Har dygnet kort an? Tre filer kravs, och de skrivs av tre olika steg.

    Sidan byggs for ett dygn som ligger i framtiden tills natten har kort det.
    Att stoppa hela bygget tills dess vore att gora sajten obyggbar i en vecka;
    att bygga en sida av tomma falt vore varre. Bygget sager vilket det blev.
    """
    st = data_root / "08_V3_STATES" / ("STATE_" + nyckel)
    return (sp.pre_manifest(data_root, day).exists()
            and bool(sorted(st.glob("600_STATES_2026_%s_EMOTION_COLOR_MANIFEST_v*_CONSENSUS.csv" % dygn)))
            and (st / ("site_%s.json" % nyckel)).exists())


def dygnets_falt(data_root: Path, day: str, nyckel: str, dygn: str, distinkta: int) -> dict:
    """Sidans tal och tillstand, ur arkivets egna filer. Inget skrivs for hand.

    Varje varde kommer fran det stalle i kedjan som AGER det:

      series och canonical_index  pre-manifestet. De falten finns bara i v3.4
                                  och skrivs av run_state nar dygnet fryses.
      bevisandelen                raknad over samma rader, pa evidence_basis
                                  mot pool_evidence.FONSTERNIVAN. Golvet lases
                                  ur GOLV_KANONISK och star inte en andra gang.
      manifestets sha256          sidecaren bredvid emotionsmanifestet - samma
                                  hash som stampeln och signaturen intygar.
      bevislaget                  tidsstampelposten: stamplad, forankrad eller
                                  ingetdera. TXID FINNS INTE och namns inte,
                                  se FYND 025; posten bar blockhojd och
                                  merkle-rot per kalender.
      signaturen                  signaturposten, en egen fil och ett eget
                                  bevis. Saknas den sager sidan det.

    RADERNA MASTE VARA ENSE om series och ordningstal. De skrivs per rad av
    kedjan, och tva varden i samma manifest vore ett dygn som ar tva dygn.
    """
    import csv
    st = data_root / "08_V3_STATES" / ("STATE_" + nyckel)
    rader = list(csv.DictReader(io.open(sp.pre_manifest(data_root, day),
                                        encoding="utf-8", newline="")))
    if len(rader) != 600:
        raise SystemExit("vantade 600 rader i pre-manifestet for %s, fick %d"
                         % (sp.state_id(day), len(rader)))
    for falt in ("series", "canonical_index", "evidence_basis"):
        if falt not in rader[0]:
            raise SystemExit("pre-manifestet for %s saknar %s - ar det v3.4?"
                             % (sp.state_id(day), falt))
    for falt in ("series", "canonical_index"):
        varden = {r[falt].strip() for r in rader}
        if len(varden) != 1:
            raise SystemExit("raderna ar oense om %s i %s: %s"
                             % (falt, sp.state_id(day), sorted(varden)))
    series = rader[0]["series"].strip()
    i_fonstret = sum(1 for r in rader
                     if (r.get("evidence_basis") or "").strip() == pool_evidence.FONSTERNIVAN)

    sidecar = sp.sha_sidecar(sp.emotion_manifest(data_root, day))
    if not sidecar.exists():
        raise SystemExit("saknas: " + sidecar.name + " - dygnet ar inte fryst")

    ts = json.loads(io.open(sp.timestamp_record(data_root, day), encoding="utf-8").read()) \
        if sp.timestamp_record(data_root, day).exists() else {}
    sig = json.loads(io.open(sp.signature_record(data_root, day), encoding="utf-8").read()) \
        if sp.signature_record(data_root, day).exists() else {}
    stampel, forankring = ts.get("stampel") or {}, ts.get("forankring") or {}
    bevis = "anchored" if forankring else ("stamped" if stampel.get("at") else "unstamped")
    kal = forankring.get("kalendrar") or []
    signatur = (sig.get("signatur") or {}).get("betrodd_kommentar") or ""

    d = _d(day)
    return {
        "state_id": sp.state_id(day),
        "observerat": "%d %s %d" % (d.day, d.strftime("%B"), d.year),
        "series": series,
        "index": rader[0]["canonical_index"].strip(),
        "fonster": "%d of %d" % (i_fonstret, len(rader)),
        "golv": "%.0f%%" % (pool_evidence.GOLV_KANONISK * 100),
        "sha": io.open(sidecar, encoding="utf-8").read().split()[0],
        "distinkta": distinkta,
        "bevis": bevis,
        "stamplad_at": stampel.get("at") or "",
        # Blockhojd OCH merkle-rot per kalender, hela roten: den ska ga att
        # sla upp tecken for tecken i en blockutforskare.
        "forankring": "; ".join("block %s &middot; merkleroot %s"
                                % (k["block_height"], k["merkle_root"]) for k in kal),
        "signatur": html_mod.escape(signatur),
    }


def build_data(data_root: Path, out: Path, nyckel: str = FIELD_DAY,
               day: str = FIELD_DAY, fil: str = "data.js",
               variabel: str = "STATE001") -> dict:
    """Skriver data.js: 600 rutor med farg, tolkning OCH kallan bakom.

    Kedjan nyhet -> observation -> emotion -> farg far aldrig kortas av, sa de
    tva kallorna joinas rad for rad och skriptet stannar hellre an skriver en
    halvriktig fil. En sida som pastar att varje ruta bar sitt eget bevis far
    inte skeppa en ruta vars bevis har flyttat."""
    state_dir = data_root / "08_V3_STATES" / ("STATE_" + nyckel)
    site_json = state_dir / ("site_%s.json" % nyckel)
    if not site_json.exists():
        raise SystemExit("saknas: " + str(site_json))

    site = json.load(io.open(site_json, encoding="utf-8"))
    site = site if isinstance(site, list) else (site.get("tiles") or list(site.values())[0])
    import csv
    manifest = list(csv.DictReader(io.open(manifest_for(state_dir, day), encoding="utf-8")))

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
    with io.open(out / fil, "w", encoding="utf-8") as f:
        f.write("window.%s=" % variabel)
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("  %-14s %7d bytes  %s" % (fil, (out / fil).stat().st_size, agreement))
    return payload


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

    Talordet far ocksa sta pa bara ETT stalle i sidans beskrivning av sig
    sjalv. En rakning pa tva stallen ar en rakning som bara halvt gar att
    ratta.

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
    # EN RAKNING, ETT STALLE. Talordet stod bade i hjalten och i underrubriken,
    # och grinden sag bara hjalten: vid sjutton kapitel hade den ena rattats och
    # den andra blivit kvar. Det ar FYND 004:s form - ett varde pa tva stallen -
    # den har gangen i grindens egen text.
    #
    # Bara sidans beskrivning av sig sjalv raknas. Kapiteltexten namner sexton
    # kanslor och sexton hextecken, och innehallsforteckningen bar en
    # kapitelrubrik med samma ord; inget av det ar ett pastaende om sidan.
    omsig = [lead.group(1)] + [m.group(1) for m in (
        re.search(r'<p class="sub">(.*?)</p>', html, re.S),
        re.search(r'<meta name="description" content="(.*?)">', html, re.S)) if m]
    helt = r"(?<![A-Za-z])%s(?![A-Za-z])" % ord_.group(1)
    star = sum(len(re.findall(helt, t, re.I)) for t in omsig)
    if star != 1:
        raise SystemExit(
            "talordet %s star %d ganger i sidans beskrivning av sig sjalv "
            "(hjalten, underrubriken, meta-beskrivningen) — det ska sta pa "
            "ETT stalle, annars rattas bara det ena nar kapitlen blir fler"
            % (ord_.group(1), star))
    return kapitel


# Filerna som provar exakt det tabellraden namner: urval, storytak, regionkvoter.
# Kommer en till fil som provar samma sak hor den hemma har. Glommer nagon bort
# den undercountar talet, och det ar ratt felriktning - ett tal som pastar for
# lite ar inte samma sorts fel som 42.
URVALETS_TESTER = ("tests/test_select_day.py", "tests/test_story_cap.py")


def rakna_tester(filer=URVALETS_TESTER) -> int:
    """Talet i tabellen raknas fram vid bygget, aldrig skrivet for hand.

    Raden sa "42 tests" om urval, storytak och regionkvoter. Uppmatt 2026-11-20:
    de tva filerna som provar just det samlar 16 fall, hela sviten 258. 42 var
    varken det ena eller det andra - ett tal som pastar sig vara en sak och
    raknar en annan, alltsa samma form som hjaltens rakning hade.

    VARFOR RADENS EGNA TESTER OCH INTE HELA SVITEN: sviten ar ett sant tal om
    nagot annat an raden handlar om. Att satta 254 dar vore att upprepa felet
    med en riktigare siffra. Texten sager vad som raknats, sa lasaren kan kora
    samma kommando.

    Pytest raknar, inte vi: en egen rakning av "def test_" missar varje
    parametriserat fall. Saknas en fil stannar bygget."""
    rot = HERE.parent
    saknas = [f for f in filer if not (rot / f).exists()]
    if saknas:
        raise SystemExit("hittar inte %s - testtalet gar inte att rakna" % ", ".join(saknas))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--collect-only", *filer],
                       cwd=str(rot), capture_output=True, text=True)
    m = re.search(r"(\d+) tests? collected", r.stdout)
    if not m:
        raise SystemExit("pytest gav ingen rakning att skriva in:\n"
                         + (r.stdout or r.stderr)[-400:])
    return int(m.group(1))


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
    # TVA STORA PNG-MARKEN, GENOMSKINLIGA. Utan dem fanns bara tva
    # deklarationer, och den storsta av dem var apple-ikonen. Firefox
    # valjer den storsta till sin startsidesruta och visade alltsa den
    # enda fil som har malade svarta horn - en cirkel i en svart
    # kvadrat i stallet for en fristaende cirkel. Nu finns storre
    # filer som INTE har horn, och valet faller pa dem.
    #
    # Ingen ny bildlogik: samma cirkel_ur_verket som de andra tva.
    # Alfakanalen sparas som den ar - plattas den mot en bakgrund ar
    # vi tillbaka i samma fel.
    stora = []
    for n in (192, 512):
        f = out / ("icon-%d.png" % n)
        cirkel_ur_verket(src, n).save(f)
        stora.append(f)
    # Apple visar ingen genomskinlighet, den blir svart. Lagg cirkeln pa
    # sidans egen bakgrund i stallet for att lata systemet valja.
    from PIL import Image
    platta = Image.new("RGB", (180, 180), (10, 10, 11))
    c = cirkel_ur_verket(src, 180)
    platta.paste(c, (0, 0), c)
    apple = out / "apple-touch-icon.png"
    platta.save(apple)
    for f in [ico] + stora + [apple]:
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
    redo att laddas upp. Stampelstrangen star kvar som bygget skrev den;
    commiten heter 831632f efter omskrivningen 2026-11-11. En sida som pastar sig byggd ur ingen kand commit
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


# /labs AR ADRESSEN SOM REDAN AR PUBLICERAD. Atta publika inlagg bar
# 600states.com/labs, och sidan ligger pa /labs.html - alltsa Apaches 404-sida
# for var och en som foljer dem. En katalog med en index.html gor adressen
# verklig utan .htaccess, som bara finns pa servern och inte i bygget.
#
# OMDIRIGERING OCH INTE EN KOPIA. labs.html pekar pa img/state_001.png med
# relativ sokvag; ur /labs/ skulle den bli /labs/img/ och bilden forsvinna.
# En kopia skulle dessutom vara tva filer att halla lika, och den sortens par
# glider isar. /labs.html ror sig inte - aven den lanken ar publicerad, och
# canonical pekar dit sa att sokmotorn vet vilken av de tva som ar sidan.
LABS_REDIRECT = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="build" content="%s">
<title>600 LABS</title>
<link rel="canonical" href="https://600states.com/labs.html">
<meta http-equiv="refresh" content="0; url=/labs.html">
<p><a href="/labs.html">600 LABS</a>
"""


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

    # Fore sidorna, for att index.html bar tva tal ur den har rakningen: rutor
    # utan samstammighet och antalet distinkta farger. En andra rakning for
    # prosan vore samma varde pa tva stallen - FYND 004 - och den forsta av dem
    # raknade med ett reguljart uttryck over hela data.js och gav 603 traffar
    # over 600 rutor. Talen kommer ur payloaden, en gang.
    talen = build_data(data_root, out)
    # Kalibreringsverkets egen datafil, samma funktion och samma kontroller.
    # En andra vag hit vore en andra definition av vad en ruta ar.
    build_data(data_root, out, NYCKEL_315, DYGN_315, "data_2026_315.js", "STATE2026315")
    # Seriens forsta dygn. Finns det inte an byggs sidan inte, och startsidans
    # lank till den tas bort i samma bygge - en lank till en sida som inte
    # laddades upp ar en 404 pa en sajt vars hela tes ar sparbarhet.
    bygg_335 = dygnet_finns(data_root, DAG_335, NYCKEL_335, DYGN_335)
    falt_335 = None
    if bygg_335:
        talen_335 = build_data(data_root, out, NYCKEL_335, DYGN_335,
                               "data_2026_335.js", "STATE2026335")
        # Talet kommer ur payloaden, dar det redan raknats. En andra rakning
        # over samma manifest vore samma varde pa tva stallen - FYND 004.
        falt_335 = dygnets_falt(data_root, DAG_335, NYCKEL_335, DYGN_335,
                                talen_335["distinct"])
        print("  %-14s %s, %s" % ("dygnet:", falt_335["state_id"], falt_335["series"]))
    else:
        print("  %-14s %s finns inte i arkivet an - %s byggs inte, och"
              " startsidans lank till den tas bort i samma bygge"
              % ("NOTERA:", sp.state_id(DAG_335), SIDA_335))
    # Varje sida stamplas, och en sida utan stampel faller bygget: en sida som
    # inte gar att binda till en version ar inte sparbar, och det ar hela
    # skalet till att stampeln finns.
    for sida in ["index.html", "labs.html", SIDA_315] + ([SIDA_335] if bygg_335 else []):
        html = io.open(HERE / sida, encoding="utf-8").read()
        html, n = re.subn(r'(<meta name="build" content=")[^"]*(">)', r"\g<1>" + stamp + r"\g<2>", html, count=1)
        if n != 1:
            raise SystemExit("hittar ingen byggstampel i " + sida)
        if sida == "index.html":
            n = rakna_tester()
            html, k = re.subn(r"(<span data-tests>)[^<]*(</span>)",
                              r"\g<1>%d\g<2>" % n, html, count=1)
            if k != 1:
                raise SystemExit("hittar ingen plats for testtalet i " + sida)
            print("  %-14s %d tester over urval och storytak" % ("rakning:", n))
            utan = talen["agreement"].get("1/3", 0)
            html, k = re.subn(r"(<span data-nocons>)[^<]*(</span>)",
                              r"\g<1>%d\g<2>" % utan, html, count=1)
            if k != 1:
                raise SystemExit("hittar ingen plats for talet utan samstammighet i " + sida)
            print("  %-14s %d rutor utan samstammighet (1/3)" % ("enighet:", utan))
            # Talet lag redan i payloaden som data.js skickar till sidan. Att
            # rakna det en gang till har vore samma varde pa tva stallen.
            html, k = re.subn(r"(<span data-distinct>)[^<]*(</span>)",
                              r"\g<1>%d\g<2>" % talen["distinct"], html, count=1)
            if k != 1:
                raise SystemExit("hittar ingen plats for antalet distinkta farger i " + sida)
            print("  %-14s %d distinkta farger av %d rutor"
                  % ("farger:", talen["distinct"], talen["n"]))
            # Rutornas index 11 ar claim_source: P rubrik, S ord ur adressen,
            # U osakrad sidtitel. Samma falt som sidan glossar i lasrutan, sa
            # det talet kan en besokare rakna om sjalv ur data.js. Dygnet star
            # i spannets namn: byts FIELD_DAY utan att prosan foljer med,
            # hittar raden nedan inget span och bygget stannar.
            slug = sum(1 for t in talen["tiles"] if t[11] == "S")
            html, k = re.subn(r"(<span data-slug-%s>)[^<]*(</span>)" % FIELD_DAY,
                              r"\g<1>%d\g<2>" % slug, html, count=1)
            if k != 1:
                raise SystemExit("hittar ingen plats for slugandelen i " + sida)
            print("  %-14s %d av %d rutor lasta ur webbadressen (S), dygn %s"
                  % ("urladress:", slug, talen["n"], FIELD_DAY))
            # EN LANK, INTE EN LISTA. Finns dygnet inte tas stycket bort helt:
            # hellre ingen lank an en lank till ingenting.
            html = valj(html, sida, "latest" if bygg_335 else None, ("latest",))
            html = gate_obruten_produktion(data_root, html, sida)
            if bygg_335:
                html = fyll(html, sida, "latest-id", falt_335["state_id"])
                if ('href="/%s"' % SIDA_335) not in html:
                    raise SystemExit("startsidans lank pekar inte pa " + SIDA_335)
                print("  %-14s lank till %s" % ("startsidan:", falt_335["state_id"]))
            else:
                print("  %-14s ingen lank till det senaste dygnet" % "startsidan:")
        if sida == SIDA_315:
            r = reproducerar(data_root, NYCKEL_315, DYGN_315)
            html, k = re.subn(r"(<span data-repro-2026-%s>)[^<]*(</span>)" % DYGN_315,
                              r"\g<1>%d\g<2>" % r, html, count=1)
            if k != 1:
                raise SystemExit("hittar ingen plats for reproduktionstalet i " + sida)
            print("  %-14s %d av 600 rutor reproducerar ur protokollet, dygn 2026/%s"
                  % ("farg:", r, DYGN_315))
        if sida == SIDA_335:
            f = falt_335
            # Sidan valjer sina texter ur arkivets falt och fyller sina tal.
            html = valj(html, sida, "canonical" if f["series"] == "CANONICAL"
                        else "unqualified", ("canonical", "unqualified"))
            html = valj(html, sida, f["bevis"], ("unstamped", "stamped", "anchored"))
            html = valj(html, sida, "signed" if f["signatur"] else "unsigned",
                        ("signed", "unsigned"))
            for namn, nyckel in (("state-id", "state_id"), ("observed", "observerat"),
                                 ("window", "fonster"), ("floor", "golv"),
                                 ("sha", "sha"), ("distinct", "distinkta")):
                html = fyll(html, sida, namn, f[nyckel])
            if f["series"] == "CANONICAL":
                html = fyll(html, sida, "index", f["index"])
            if f["bevis"] != "unstamped":
                html = fyll(html, sida, "stamp-at", f["stamplad_at"])
            if f["bevis"] == "anchored":
                html = fyll(html, sida, "anchor", f["forankring"])
            if f["signatur"]:
                html = fyll(html, sida, "signature", f["signatur"])
            # TVA GRINDAR SOM FANGAR DET JAG GLOMMER. Ett kvarlamnat block ar
            # tva utfall pa en sida; ett tomt span ar ett pastaende utan tal.
            # Bada faller bygget i stallet for att ligga ute.
            kvar = sorted(set(re.findall(r"data-when-[a-z]+", html)))
            if kvar:
                raise SystemExit("%s bar kvar ovalda block: %s" % (sida, kvar))
            kvar = sorted(set(re.findall(r"<span data-[a-z-]+>&mdash;</span>", html)))
            if kvar:
                raise SystemExit("%s bar tomma span: %s" % (sida, kvar))
            print("  %-14s %s, bevis: %s, signatur: %s"
                  % ("sidan:", f["series"], f["bevis"], "ja" if f["signatur"] else "nej"))
        if sida == "labs.html":
            d = distinkta_farger(data_root, LABS_DAY, LABS_DIR)
            html, k = re.subn(r"(<span data-distinct-2026-%s>)[^<]*(</span>)" % LABS_DAY,
                              r"\g<1>%d\g<2>" % d, html, count=1)
            if k != 1:
                raise SystemExit("hittar ingen plats for 2026/%s distinkta farger i %s"
                                 % (LABS_DAY, sida))
            print("  %-14s %d distinkta farger av 600 rutor, dygn 2026/%s"
                  % ("farger:", d, LABS_DAY))
            kap = gate_hjaltens_rakning(html)
            print("  %-14s %d kapitel, hjaltens rakning stammer" % ("grind:", kap))
        # newline="\n": utan den oversatter Python \n till CRLF pa Windows, och
        # med core.autocrlf=true i arbetstradet blev den utrullade filens bytes
        # beroende av vilken maskin som byggde. Servern ar Unix och det som
        # ligger ute ar LF.
        io.open(out / sida, "w", encoding="utf-8", newline="\n").write(html)
        print("  %-14s %7d bytes  build=%s" % (sida, (out / sida).stat().st_size, stamp))

    (out / "labs").mkdir(exist_ok=True)
    io.open(out / "labs" / "index.html", "w", encoding="utf-8",
            newline="\n").write(LABS_REDIRECT % stamp)
    print("  %-14s %7d bytes  -> /labs.html" %
          ("labs/index.html", (out / "labs" / "index.html").stat().st_size))

    # Faltet och lasrutan: en fil, last av bada sidorna. Se site/field.js.
    shutil.copyfile(HERE / "field.js", out / "field.js")
    print("  %-14s %7d bytes" % ("field.js", (out / "field.js").stat().st_size))

    # BILDER SOM LIGGER I REPOT, inte i arkivet: bokens uppslag. Verken
    # kommer ur arkivet och hor inte i git, men en rendering AV boken ar
    # harledd ur repots egen kod och foljer med den. De kopieras som de ar,
    # och byggets lista sager hur manga det blev.
    for f in sorted((HERE / "img").glob("*.png")):
        shutil.copyfile(f, out / "img" / f.name)
        print("  img/%s  %7d bytes" % (f.name, f.stat().st_size))

    build_favicon(data_root, out)

    for day in DAYS:
        src = render_for(data_root / "08_V3_STATES" / ("STATE_" + day), day)
        dst = out / "img" / ("state_%s.png" % day)
        shutil.copyfile(src, dst)
        print("  img/%s  %7d bytes" % (dst.name, dst.stat().st_size))

    src = render_for(data_root / "08_V3_STATES" / ("STATE_" + NYCKEL_315), DYGN_315)
    dst = out / "img" / ("state_%s.png" % NYCKEL_315)
    shutil.copyfile(src, dst)
    print("  img/%s  %7d bytes" % (dst.name, dst.stat().st_size))

    if bygg_335:
        src = render_for(data_root / "08_V3_STATES" / ("STATE_" + NYCKEL_335), DYGN_335)
        dst = out / "img" / ("state_%s.png" % NYCKEL_335)
        shutil.copyfile(src, dst)
        print("  img/%s  %7d bytes" % (dst.name, dst.stat().st_size))

    print("\nKlart: " + str(out))
    print("Ladda upp innehallet i mappen till /600states.com/public_html/ .")
    print("Mappen innehaller bara det som ska ut. Versaler spelar roll pa servern.")


if __name__ == "__main__":
    main(sys.argv)
