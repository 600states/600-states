"""Batchstorleken kommer ur den frysta specen och star ingen annanstans.

Stod tidigare hardkodad som 60 pa tva stallen medan specen angav 50. Uppmatt
2026-11-05 pa 2026/308: vid 60 rader tappar modellen en observation och hittar
pa en utfyllnadsrad med nollfyllda poang for att na antalet. Testerna finns for
att vardet inte ska kunna driva isar igen - en regel som inte kan falla ett
test ar ett onskemal.
"""
import json, re, sys
from pathlib import Path
ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT)); sys.path.insert(0, str(ROT / "src"))
import pytest
from config import SPEC_FILE, canonical_batch_size

skip_utan_arkiv = pytest.mark.skipif(
    not SPEC_FILE.exists(), reason="dataarkivet saknas")

@skip_utan_arkiv
def test_batchstorleken_kommer_ur_specen():
    spec = json.loads(SPEC_FILE.read_text(encoding="utf-8"))
    assert canonical_batch_size() == spec["canonical_batch_size"]

@skip_utan_arkiv
def test_batchstorleken_ar_ett_rimligt_heltal():
    bs = canonical_batch_size()
    assert isinstance(bs, int) and 1 <= bs <= 600
    assert 600 % bs == 0, "600 observationer maste ga jamnt upp i batchar"

@pytest.mark.parametrize("fil", ["src/run_state.py", "src/build_classifier_input.py"])
def test_ingen_hardkodad_batchstorlek(fil):
    """Batchningen far inte innehalla ett literalt tal. En definition, ett stalle."""
    t = (ROT / fil).read_text(encoding="utf-8")
    for rad in t.splitlines():
        if "range(0, len(items)" in rad or "batch_{k//" in rad:
            assert not re.search(r"\b\d{2,}\b", rad), f"hardkodat tal i batchningen: {rad.strip()}"
    assert "canonical_batch_size" in t
