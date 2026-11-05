"""Enda stallet dar sokvagen till datamappen bor.

Koden ligger i git (denna mapp). Datan ligger i OneDrive och foljer inte med
i repot - den ar stor, binar och andras sallan. Satt STATES_DATA for att peka
nagon annanstans, t.ex. pa en annan maskin.
"""
import os
from pathlib import Path

_DEFAULT_WIN = r"%STATES_DATA%"
_DEFAULT_NIX = Path.home() / "mnt" / "600 STATES"

def data_root() -> Path:
    env = os.environ.get("STATES_DATA")
    if env:
        return Path(env)
    p = Path(_DEFAULT_NIX)
    return p if p.exists() else Path(_DEFAULT_WIN)

DATA = data_root()
RAW_GDELT = DATA / "01_RAW_GDELT_2026_001_010"
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
