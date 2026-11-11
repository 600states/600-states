"""Bevisfangst pa kandidatpoolen - fore urvalet.

Bevisfangsten hamtar sidan, och sidan bar rubriken. Rubriken ar
klassificerarens input. Darfor maste detta steg ligga fore urvalet, sa att de
600 kan valjas bland kandidater som faktiskt gar att lasa. Se FYND 003.

Cachen ar nycklad pa URL och delas mellan dygn: overlapp hamtas aldrig om.
Resumerbar - kan avbrytas och startas om.
"""
import json, sys
from datetime import datetime, timedelta, timezone
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
