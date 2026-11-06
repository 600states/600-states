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


# ---- precisionen ur specen -------------------------------------------------

@skip_utan_arkiv
def test_precisionen_kommer_ur_specen():
    """Specen anger score/intensity/confidence_precision och ingenting
    kontrollerade det. Ett krav utan efterkontroll ar ett onskemal."""
    import json, classify
    spec = json.loads(SPEC_FILE.read_text(encoding="utf-8"))
    assert classify.spec_precision() == spec["score_precision"]
    assert spec["score_precision"] == spec["intensity_precision"] == spec["confidence_precision"]

@skip_utan_arkiv
def test_for_manga_decimaler_faller():
    import classify
    from vocab import EMOTION_STATES
    def rad(oid, s):
        return {"observation_id": oid, "neutral_event_representation": "x", "scores": s,
                "primary_emotion": "Joy", "secondary_emotion": "Hope",
                "stated_primary": "Joy", "stated_secondary": "Hope",
                "stated_observation_id": oid,
                "intensity": 0.5, "confidence": 0.7, "classification_note": "n"}
    ok = {e: 0.10 for e in EMOTION_STATES}; ok["Joy"], ok["Hope"] = 0.90, 0.60
    inp = [{"observation_id": "OBS-A"}]
    assert classify.validate([rad("OBS-A", dict(ok))], inp) == []

    fel = dict(ok); fel["Grief"] = 0.123456
    assert any("decimaler" in f for f in classify.validate([rad("OBS-A", fel)], inp))

    r = rad("OBS-A", dict(ok)); r["intensity"] = 0.6666
    assert any("decimaler" in f for f in classify.validate([r], inp))

@skip_utan_arkiv
def test_berakande_flyttal_faller_inte():
    """0.05 + 0.01 blir 0.060000000000000005. Kontrollen ska mata vad modellen
    skrev, inte flyttalsrepresentation."""
    import classify
    assert not classify._for_manga_decimaler(0.05 + 0.01, 2)
    assert not classify._for_manga_decimaler(0.1 + 0.2, 1)
    assert classify._for_manga_decimaler(0.123456, 2)
