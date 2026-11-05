"""Kandidatpoolen maste innehalla hela den historiska urvalslistan.

Missar poolen rader som det gamla systemet valde, ar filtreringen fel och
urvalsmotorn kan omojligt producera ett giltigt dygn.
"""
import csv, io, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from candidates import build
from config import RAW_GDELT, REMEDIATION

PKG = REMEDIATION / "600_STATES_2026_002_010_FROZEN_PRE_EMOTION_PACKAGE_v2.2_SEMANTIC_MATERIALITY_STRICT.zip"

import pytest
pytestmark = pytest.mark.skipif(not PKG.exists(),
    reason="dataarkivet saknas - satt STATES_DATA (se README)")

def _hist(state):
    with zipfile.ZipFile(PKG) as z:
        n = next(x for x in z.namelist() if f"2026_{state}_FROZEN" in x and x.endswith(".csv"))
        return list(csv.DictReader(io.StringIO(z.read(n).decode("utf-8"))))

def test_pool_tacker_historiskt_urval_002():
    pool = {c["url"] for c in build("20260102", RAW_GDELT / "600_STATES_20260102_GDELT2_MENTIONS.zip")}
    hist = _hist("002")
    miss = [h for h in hist if h["representative_url"] not in pool]
    assert not miss, f"{len(miss)} historiska rader saknas i kandidatpoolen"

if __name__ == "__main__":
    test_pool_tacker_historiskt_urval_002()
    print("OK - 600/600 historiska rader finns i kandidatpoolen")
