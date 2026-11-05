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
