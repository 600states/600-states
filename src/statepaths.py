"""Dygnets identitet och alla filnamn. ETT stalle.

Observationsdygnet ar enda indata. Allt annat harleds:

    day        20261201            CLI-argument, UTC, aldrig systemklockan
    ordinal    335                 dagnummer inom aret
    state_id   2026/335            som i Observation Day Rule v1.0 FROZEN
    state_key  2026_335            filnamnssaker form av samma sak

VARFOR state_id maste harledas har och ingen annanstans: formatet gick fran
"2026/001" i v3.0 till "2026-001" i v3.1 utan beslut. state_id ingar i
observation_id-hashen, sa varje ID i v3.1 blev ett annat an det skulle varit.
Ett protokollbrott som uppstod av att strangen byggdes pa fem stallen i koden.

ARET ar aldrig hardkodat. Serien ar oppen over ar; 2027/001 kommer.

MANIFESTVERSIONEN NAMNER EN FORM, inte en smak. v3.2 har 17 kolumner i
pre-emotionsmanifestet, v3.3 har 19: evidence_retrieved_at och evidence_basis
kom till med FYND 011. Tva former under ett versionsnamn ar precis det som
gjorde "Execution Spec v2.2" oanvandbart som referens - se AGENTS.md.

SKRIVNING ANVANDER ALLTID V. LASNING TAR DYGNETS EGEN FIL. De tre dygn som
redan ar frysta bar v3.2 och ska fortsatta gora det; de ska anda ga att
revidera och publicera. Darfor frozen().

KATALOGEN heter STATE_<state_key>, alltsa STATE_2026_335. Pilotserien ligger i
STATE_001..STATE_010 med den gamla namngivningen och ror inte dessa - en
efterhandskorning av 2 januari 2026 hamnar i STATE_2026_002 bredvid, aldrig
ovanpa.
"""
from datetime import date

MANIFEST_VERSION = "v3.3"
GENERATION_DIR = "08_V3_STATES"

def _d(day):
    s = str(day).strip()
    if len(s) != 8 or not s.isdigit():
        raise ValueError(f"dygnet ska vara YYYYMMDD (UTC), fick {day!r}")
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))

def year(day):      return _d(day).year
def ordinal(day):   return _d(day).timetuple().tm_yday
def state_id(day):  return f"{year(day)}/{ordinal(day):03d}"
def state_key(day): return f"{year(day)}_{ordinal(day):03d}"

def outdir(DATA, day):
    return DATA / GENERATION_DIR / f"STATE_{state_key(day)}"

def workdir(DATA, day):
    d = outdir(DATA, day) / "_work"; d.mkdir(parents=True, exist_ok=True); return d

def _f(DATA, day, tail):
    return outdir(DATA, day) / f"600_STATES_{state_key(day)}_{tail}"

V = MANIFEST_VERSION
def pre_manifest(DATA, day):      return _f(DATA, day, f"PRE_EMOTION_MANIFEST_{V}.csv")
def emotion_manifest(DATA, day):  return _f(DATA, day, f"EMOTION_MANIFEST_{V}_CONSENSUS.csv")
def color_manifest(DATA, day):    return _f(DATA, day, f"EMOTION_COLOR_MANIFEST_{V}_CONSENSUS.csv")
def near_duplicate(DATA, day):    return _f(DATA, day, f"NEAR_DUPLICATE_OBSERVED_{V}.csv")
def selection_report(DATA, day):  return _f(DATA, day, f"SELECTION_REPORT_{V}.json")
def png(DATA, day):               return _f(DATA, day, f"{V}_CONSENSUS.png")
def site_json(DATA, day):         return outdir(DATA, day) / f"site_{state_key(day)}.json"
def classifier_input(DATA, day):  return outdir(DATA, day) / "classifier_input"
def sha_sidecar(path):            return path.with_name(path.name + ".sha256")

def frozen(path):
    """Dygnets egen fil, aven om den frystes under en tidigare manifestversion.

    Anvands vid LASNING - revision, publicering, batteribygge. Skrivning gar
    aldrig genom den har funktionen: ett nytt dygn ska bara V och ingenting
    annat, annars avgor vad som rakar ligga pa disk vilken form som skrivs.
    """
    if path.exists():
        return path
    hits = sorted(path.parent.glob(path.name.replace(V, "v*")))
    if not hits:
        raise FileNotFoundError(path)
    return hits[-1]
