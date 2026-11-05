"""Konsensus maste reproducera ett fryst manifest, falt for falt.

STATE_001 har bade de tre ra passen (610 observationer vardera) och det frusna
konsensusmanifestet. Testet bygger om konsensus fran passen och jamfor. Det ar
vakten mot att rostningsregeln eller medianen andras obemarkt - dar bestams
vilken emotion varje ruta far, och darmed vilken farg.
"""
import csv, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from consensus import rows, load_passes, load_inputs
from config import DATA

PILOT = DATA / "08_V3_STATES" / "STATE_001"
PASSES = PILOT / "600_STATES_2026_001_CLASSIFIER_PASSES.zip"
REF = PILOT / "600_STATES_2026_001_EMOTION_COLOR_MANIFEST_v3.1_CONSENSUS.csv"

pytestmark = pytest.mark.skipif(not (PASSES.exists() and REF.exists()),
                                reason="pilotdata for STATE_001 saknas")

def _build():
    d = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(PASSES) as z:
        z.extractall(d)
    passdir = next(p for p in d.rglob("*") if p.is_dir() and list(p.glob("pass1_*.json")))
    return rows(load_passes(passdir), load_inputs(PILOT / "classifier_input"))

OUT = None
def _out():
    global OUT
    if OUT is None:
        OUT = _build()
    return OUT

def test_reproducerar_frysta_manifestet():
    got = {r["observation_id"]: r for r in _out()}
    ref = list(csv.DictReader(open(REF, encoding="utf-8-sig")))
    assert len(ref) == 600 and len(got) == 600
    fel = []
    for r in ref:
        g = got[r["observation_id"]]
        for f in ("primary_emotion", "secondary_emotion", "intensity", "confidence",
                  "primary_agreement"):
            if str(g[f]) != str(r[f]):
                fel.append((r["tile_index"], f, r[f], g[f]))
    assert not fel, f"{len(fel)} avvikelser, forsta {fel[:3]}"

def test_fargen_berors_inte_av_konsensus():
    """Emotionsmanifestet far inte innehalla hex. Fargen kommer sist i kedjan."""
    assert "hex" not in _out()[0]

def test_primary_och_secondary_ar_alltid_olika():
    assert all(r["primary_emotion"] != r["secondary_emotion"] for r in _out())
