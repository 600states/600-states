"""Enda stallet dar sokvagen till datamappen bor.

Koden ligger i git (denna mapp). Datan ligger utanfor och foljer inte med i
repot - den ar stor, binar och andras sallan.

Satt STATES_DATA till katalogen som innehaller 00_CANONICAL_PROJECT_DOCS och
08_V3_STATES. Ingen sokvag ar hardkodad: en sokvag i ett publikt repo sager
nagot om den som skrev den, och om fem ar sager den fel sak om alla.
"""
import os
from pathlib import Path

_MOUNT = Path.home() / "mnt" / "600 STATES"

def data_root() -> Path:
    env = os.environ.get("STATES_DATA")
    if env:
        return Path(env)
    return _MOUNT            # kan saknas - anvand require_data() nar den kravs

def require_data() -> Path:
    d = data_root()
    if not d.exists():
        raise SystemExit(
            "Hittar inte dataarkivet: " + str(d) + "\n"
            "Satt STATES_DATA till katalogen med 00_CANONICAL_PROJECT_DOCS och 08_V3_STATES.\n"
            '  Windows:  setx STATES_DATA "<sokvag>"\n'
            '  bash:     export STATES_DATA="<sokvag>"')
    return d

DATA = data_root()
RAW_GDELT = DATA / "01_RAW_GDELT_2026_001_010"      # pilotdygnen 001-010, historiska
RAW_ROOT  = DATA / "01_RAW_GDELT"                   # nya dygn, ett ar per underkatalog

def raw_day_dir(day: str) -> Path:
    """Katalogen for ett dygns rasnapshot. Aret harleds ur dygnet, aldrig ur klockan."""
    return RAW_ROOT / day[:4]
FROZEN = DATA / "00_CANONICAL_PROJECT_DOCS" / "01_FROZEN_PROTOCOL_LIBRARY_v1.0"
REMEDIATION = DATA / "03_VALIDATION_REMEDIATION"

def raw_day_zip(yyyymmdd: str) -> Path:
    return RAW_GDELT / f"600_STATES_{yyyymmdd}_GDELT2_MENTIONS.zip"


# Kallregistret. EN definition. Versionen harleds ur filnamnet och skrivs i
# manifestet, sa att manifestet aldrig kan pasta en annan version an den kod
# faktiskt laste. Se FYND 004.
REGISTRY_FILE = FROZEN / "600_STATES_Source_Registry_v2.0_FROZEN.csv"

def registry_version() -> str:
    import re
    m = re.search(r"_v(\d+\.\d+)", REGISTRY_FILE.name)
    return "v" + m.group(1) if m else "UNKNOWN"


# Exekveringsspecen. EN definition, av samma skal som registret: ett varde som
# beskriver instrumentet ska lasas ur instrumentet, aldrig skrivas for hand.
SPEC_FILE = FROZEN / "600_STATES_Emotion_Classification_Execution_Spec_v2.1_FROZEN.json"

def canonical_batch_size() -> int:
    """Batchstorleken ur den frysta specen.

    Stod tidigare hardkodad som 60 pa tva stallen - run_state.py och
    build_classifier_input.py - medan specen angav 50. Tva definitioner av
    samma sak, och ingen av dem specens.

    Uppmatt 2026-11-05 pa 2026/308: vid 60 rader tappar modellen bort en
    observation, marker att den bara har 59, och hittar pa en sextionde med
    pahittat id och nollfyllda poang - "No content supplied for this slot".
    Nollfyllningen ar den defekt som ogiltigforklarade pilotserien.

    Vardet lases nu ur specen och kan inte driva isar igen. Se FYND 004: ett
    falt som beskriver en resurs ska lasas ur resursen.
    """
    import json
    return int(json.loads(SPEC_FILE.read_text(encoding="utf-8"))["canonical_batch_size"])
