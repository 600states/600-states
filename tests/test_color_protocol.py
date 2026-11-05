"""Regressionsvakt: fargprotokollet maste reproducera ett fryst manifest.

Andras nagon konstant i color_protocol.py sager detta test ifran. Testet ar
skyddet mot att formeln justeras for att bilden ska bli snyggare.
"""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from color_protocol import hex_of_row, ANCHORS, VOCAB
from config import DATA

REF = DATA / "08_V3_STATES/STATE_001/600_STATES_2026_001_EMOTION_COLOR_MANIFEST_v3.0_CONSENSUS.csv"

import pytest
pytestmark = pytest.mark.skipif(not REF.exists(),
    reason="dataarkivet saknas - satt STATES_DATA (se README)")

def test_vokabular_ar_sexton():
    assert len(VOCAB) == 16 and set(VOCAB) == set(ANCHORS)

def test_reproducerar_fryst_manifest():
    rows = list(csv.DictReader(open(REF, encoding="utf-8")))
    assert len(rows) == 600
    bad = [r["tile_index"] for r in rows if hex_of_row(r).upper() != r["hex"].upper()]
    assert not bad, f"{len(bad)} rader reproducerar inte, forsta {bad[:5]}"

def test_klamning_haller():
    hx = hex_of_row({"primary_emotion": "Joy", "secondary_emotion": "Grief",
                     "intensity": 1.0, "confidence": 1.0})
    assert hx.startswith("#") and len(hx) == 7
