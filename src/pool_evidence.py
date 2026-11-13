"""Bevisfangst pa kandidatpoolen - fore urvalet.

Bevisfangsten hamtar sidan, och sidan bar rubriken. Rubriken ar
klassificerarens input. Darfor maste detta steg ligga fore urvalet, sa att de
600 kan valjas bland kandidater som faktiskt gar att lasa. Se FYND 003.

Cachen ar nycklad pa URL och delas mellan dygn: overlapp hamtas aldrig om.
Resumerbar - kan avbrytas och startas om.
"""
import csv, hashlib, json, re, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_evidence import fetch_one, load_registry
import statepaths as sp
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

# BEVISFONSTRET. EN DEFINITION, OCH DEN LIGGER HAR - inte i basis(), inte i ett
# schema, inte i en docstring. Ett varde som star inuti en funktion gar inte att
# andra utan att lasa kod, och batchstorleken visade vad som hander nar samma
# tal skrivs pa tva stallen: 60 i koden, 50 i specen, i manader.
#
# GRANSEN VAR TIDIGARE HAMTNINGENS KALENDERDYGN I UTC. Den var fel. En hamtning
# 00:30 dygnet efter ar metodologiskt identisk med en 23:50 samma dygn - sidan
# har haft trettio minuter extra pa sig - och klippkanten vid midnatt betyder
# ingenting. Att i stallet hamta UNDER dygnet ar provat och forkastat: det
# fangar varje artikel noll till sextio minuter efter first mention, alltsa
# precis i fonstret dar rubriker skrivs om och stubbar blir artiklar, och det
# kraver en slinga som maste ga i aratal utan att missa en natt. Rotrisken den
# skulle skydda mot ar uppmatt till noll: 600 piloturler, atta manader, inga
# doda lankar.
#
# Beslut 2026-11-11. Hela kedjan acquire -> pool tar 15-20 minuter; tre timmar
# ar marginalen om nagot gar fel, inte malet.
FONSTER_TIMMAR = 3            # efter att observationsdygnet stangde, 24:00 UTC
KORNING_START_UTC = "00:05"   # avsedd start, klart fore 00:30; schemalaggningen byggs senare

BEVISNIVAER = ("NO_EVIDENCE", "RETROSPECTIVE", "CONTEMPORANEOUS_ARCHIVE",
               "CAPTURED_IN_WINDOW")

def basis(c, day):
    """Bevisnivan for EN kandidat i v3.0-vagen. day ar observationsdygnet, YYYYMMDD.

    CAPTURED_IN_WINDOW galler nar hamtningen skedde EFTER observationens first
    mention och senast FONSTER_TIMMAR efter att dygnet stangde. Nivan het
    tidigare OBSERVED_AT_CAPTURE, vilket betydde "under dygnet" och inte langre
    ar sant om fonstret. Ett namn som beskriver fel sak ar ett pastaende.

    DEN UNDRE GRANSEN AR MED AVSIKT. En sida som hamtades innan historien fanns
    bar inte historien, hur tidigt vi an var. Saknas first_mention_utc gar den
    gransen inte att visa, och da far raden den svagare nivan - aldrig den
    starkare. Att faltet finns vaktas av gate_candidates, fore urvalet.

    BEVISET AR DEN HASHADE SIDAN, inte forsoket. fetch_one stamplar
    retrieved_at_utc aven nar hamtningen misslyckas, sa tidsstampeln ensam
    sager bara nar vi lasade. Utan content_sha256 finns inget bevis att datera.

    capture_state.basis() hor till pilotvagen, kan inte na den starka nivan
    och anropas aldrig harifran. Se FYND 011.
    """
    t = c.get("evidence_retrieved_at")
    if not t or not c.get("content_sha256"):
        return "NO_EVIDENCE"
    d = datetime.fromisoformat(t)
    if d.tzinfo is None:
        # Utan tidszon skulle astimezone() tolka stampeln i maskinens lokala tid
        # och ge ett svar som beror pa var programmet kors. Hellre stopp.
        raise ValueError(f"evidence_retrieved_at saknar tidszon: {t!r}")
    fm = c.get("first_mention_utc")
    if not fm:
        return "RETROSPECTIVE"
    forst = datetime.strptime(fm, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    stangde = datetime.strptime(day, "%Y%m%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    return ("CAPTURED_IN_WINDOW"
            if forst < d.astimezone(timezone.utc) <= stangde + timedelta(hours=FONSTER_TIMMAR)
            else "RETROSPECTIVE")


# GOLVET FOR KANONISKT MEDLEMSKAP. Beslut 2026-11-13, PARAMETER_REGISTER 1.15
# och EVIDENCE_AND_PUBLICATION_SPEC 3.1.
#
# Uppmatt andel rader med innehallshash i de fyra v3-dygnen, samtliga
# retrospektiva: 94,3 % (2026/308), 95,5 % (309), 95,3 % (310), 94,2 % (315).
#
# TALET AR SATT MOT HAMTNINGENS FRAMGANGSGRAD, MEN MATT PA FEL FALT OM MAN
# MATER INNEHALLSHASHEN. I skarp drift hamtas dygnet 00:05-00:25, alltsa inne i
# fonstret: varje rad som far en innehallshash far da ocksa CAPTURED_IN_WINDOW,
# och de fyra talen ovan galler fortfarande som matt pa hur manga sidor som gar
# att hamta alls. Ett dygn hamtat i efterhand har daremot hog hashandel och noll
# fonsterandel - och det ar precis den skillnaden golvet finns till for att se.
# En innehallshash sager att vi HAR sidan, inte att vi hade den i tid.
#
# TALET AR RUNT MED AVSIKT, och det ar sjalva beviset. 0,90 ligger fyra
# procentenheter under den samsta uppmatta kvoten, alltsa klart under utfallen
# men inte anpassat till dem. Hade golvet statt pa 0,941 eller 0,94 hade det
# varit ett tal som lasts av mataren: en troskel trimmad sa att allt man redan
# producerat ramlar in ovanfor den. Ett runt tal gar inte att trimma i efterhand
# utan att synas.
#
# GOLVET HOJS ALDRIG. En hojning skulle gora redan numrerade dygn okanoniska i
# efterhand, och ordningstalet ar hashat och darmed permanent. Visar det sig for
# lagt ar svaret ett nytt kriterium med eget namn, aldrig ett nytt varde har.
GOLV_KANONISK = 0.90

# COMMISSIONED kan inte raknas fram ur rader; den satts for verk utanfor den
# lopande serien och star da i filen. serie() avgor de tva den kan avgora.
SERIER = ("CANONICAL", "COMMISSIONED", "UNQUALIFIED")


def serie(rader):
    """CANONICAL eller UNQUALIFIED for ett dygns manifestrader.

    Andelen ar rader med evidence_basis == CAPTURED_IN_WINDOW delat med antalet
    rader. Serien ar 600 verk fangade i fonstret, inte 600 verk vi rakar ha
    sidorna till: en innehallshash sager att vi HAR sidan, inte att vi hade den
    i tid. Ett retrospektivt dygn far aldrig vara ett av de 600, och pa
    hashandelen ar det omojligt att skilja fran ett dygn hamtat 00:05.

    INGET ANNAT INGAR. Inte http_status, inte evidence_sha256, inte orsaken
    till bortfallet, inte vems fel det var: skuldfragan hor inte hemma i
    berakningen. En rad ar fangad i fonstret eller inte.

    Noll rader ger UNQUALIFIED. Ett tomt dygn ar inte ett kanoniskt dygn, och
    ett undantag har skulle gora det till ett. Likasa ett dygn vars form inte
    bar faltet alls: det som inte sager nar det fangades sager inte att det
    fangades i tid.
    """
    if not rader:
        return "UNQUALIFIED"
    i_fonstret = sum(1 for r in rader
                     if (r.get("evidence_basis") or "").strip() == "CAPTURED_IN_WINDOW")
    return "CANONICAL" if i_fonstret / len(rader) >= GOLV_KANONISK else "UNQUALIFIED"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _nyckel(namn):
    """(ar, dagnummer) ur ett katalognamn, eller None.

    Pilotserien heter STATE_001..STATE_010 och matchar darfor inte: den ar
    ersatt for validering och hor inte till den kanoniska serien.
    """
    m = re.fullmatch(r"STATE_(\d{4})_(\d{3})", namn)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _dygn(ar, nr):
    return (date(ar, 1, 1) + timedelta(days=nr - 1)).strftime("%Y%m%d")


def _serie_i_fil(rader):
    """Serien for ett redan skrivet manifest.

    Star den i filen galler den: det ar den frysta posten, och COMMISSIONED gar
    inte att rakna fram. Saknas kolumnen - dygnen fore beslutet - raknas den
    fram ur raderna, for serie() ar en ren funktion av just dem och ger samma
    svar idag som den dagen.
    """
    stod = (rader[0].get("series") or "").strip() if rader else ""
    return stod or serie(rader)


def kedja(DATA, day):
    """Arkivets kanoniska kedja fram till, men inte med, day.

    Returnerar (antal_kanoniska_fore, prev_canonical_sha256, brott).

    ORDNINGSTALET RAKNAS FRAM UR ARKIVET och skrivs sedan in i ett manifest som
    hashas, alltsa permanent. Darfor gar lanken bakat med: utan den skulle ett
    saknat manifest bara gora talet ett for litet, tyst, och felet skulle
    frysas in. Med den gar kedjan inte ihop och korningen stannar.

    Brott ar allt som gor arkivet otolkat: ett dygn utan manifest, ett dygn med
    tva former, en lagrad lank som inte stammer mot filen fore den, ett lagrat
    ordningstal som inte ar sin egen plats i serien. Grinden avgor vad de
    kostar - den har funktionen rakna och rapporterar.
    """
    # Lasningen gar genom frozen(), som bade haller fast "ett dygn har en form"
    # och sager ifran nar den byter version. Den sista raden skrivs ut en gang
    # per aldre dygn, alltsa en gang per dygn i serien efter ett versionsbyte.
    # shortcut: brus i utskriften, inte i talen; gor frozen() tystbar om listan
    # blir lang nog att dolja grindarnas rader.
    gransen = (sp.year(day), sp.ordinal(day))
    brott, kanoniska = [], []
    for d in sorted((Path(DATA) / sp.GENERATION_DIR).glob("STATE_*")):
        nyckel = _nyckel(d.name)
        if not nyckel or nyckel >= gransen:
            continue
        try:
            fil = sp.frozen(sp.pre_manifest(Path(DATA), _dygn(*nyckel)))
        except (FileNotFoundError, ValueError) as e:
            brott.append(f"{d.name}: {e if not isinstance(e, FileNotFoundError) else 'inget pre-manifest'}")
            continue
        rader = list(csv.DictReader(open(fil, encoding="utf-8")))
        if _serie_i_fil(rader) == "CANONICAL":
            kanoniska.append((d.name, fil, rader))

    forra = None
    for plats, (namn, fil, rader) in enumerate(kanoniska, 1):
        huvud = rader[0] if rader else {}
        vantad = _sha(forra) if forra else ""
        if "prev_canonical_sha256" in huvud:
            star = (huvud.get("prev_canonical_sha256") or "").strip()
            if star != vantad:
                brott.append(f"{namn}: lanken bakat ar {star[:16] or 'tom'}, "
                             f"filen fore ar {vantad[:16] or 'ingen'}")
        if (huvud.get("canonical_index") or "").strip() not in ("", f"{plats:03d}"):
            brott.append(f"{namn}: bar ordningstal {huvud['canonical_index']}, "
                         f"men ar nummer {plats:03d} i arkivet")
        forra = fil
    return len(kanoniska), (_sha(forra) if forra else ""), brott
