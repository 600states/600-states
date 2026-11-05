"""Klassificeringsanropets validering. Den sista grinden fore konsensus."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
import classify
from vocab import EMOTION_STATES

def rad(oid, pri, sec):
    s = {e: 0.05 + i * 0.01 for i, e in enumerate(EMOTION_STATES)}
    s[pri], s[sec] = 0.90, 0.60
    return {"observation_id": oid, "neutral_event_representation": "x", "scores": s,
            "primary_emotion": pri, "secondary_emotion": sec,
            "intensity": 0.5, "confidence": 0.7, "classification_note": "n"}

INP = [{"observation_id": "OBS-A"}, {"observation_id": "OBS-B"}]
OK = [rad("OBS-A", "Joy", "Hope"), rad("OBS-B", "Grief", "Concern")]
def kopia(): return json.loads(json.dumps(OK))

def test_giltig_batch_godkanns():
    assert classify.validate(OK, INP) == []

def test_fel_antal_rader():
    assert classify.validate(OK[:1], INP)

def test_scores_maste_ha_exakt_sexton_nycklar():
    b = kopia(); b[0]["scores"].pop("Fatigue")
    assert any("16 nycklar" in f for f in classify.validate(b, INP))

def test_felet_namner_vilken_nyckel_som_saknas():
    """En felrapport som inte namner skillnaden kraver ett nytt anrop for att
    forstas. Sexton nycklar ar fryst protokoll - felet ska peka, inte fylla i."""
    b = kopia(); b[0]["scores"].pop("Fatigue")
    assert any("Fatigue" in f for f in classify.validate(b, INP))

def test_felet_namner_vilken_nyckel_som_ar_over():
    b = kopia(); b[0]["scores"]["Joie"] = 0.1
    fel = classify.validate(b, INP)
    assert any("Joie" in f for f in fel)
    assert all("Joie" not in str(r["scores"].keys()) for r in OK)  # originalet orort

def test_primary_maste_vara_hogsta():
    b = kopia(); b[0]["primary_emotion"] = "Fear"
    assert any("hogsta" in f for f in classify.validate(b, INP))

def test_secondary_maste_vara_nast_hogsta():
    b = kopia(); b[0]["secondary_emotion"] = "Fear"
    assert any("nast hogsta" in f for f in classify.validate(b, INP))

def test_varden_utanfor_intervallet_stoppas():
    for falt in ("intensity", "confidence"):
        b = kopia(); b[0][falt] = 1.4
        assert any(falt in f for f in classify.validate(b, INP))

def test_observation_id_maste_stamma():
    b = kopia(); b[0]["observation_id"] = "OBS-X"
    assert classify.validate(b, INP)

def test_motivering_kravs():
    b = kopia(); b[0]["classification_note"] = "   "
    assert classify.validate(b, INP)

def test_nollfyllning_syns_i_diagnostiken():
    """Defekten som ogiltigforklarade pilotserien: fjorton poang mekaniskt noll."""
    noll = [dict(r, scores={e: (r["scores"][e] if e in (r["primary_emotion"],
                                                        r["secondary_emotion"]) else 0.0)
                            for e in EMOTION_STATES}) for r in kopia()]
    assert classify.validate(noll, INP) == []          # passerar formell validering
    assert classify.diagnostics(noll)["authored_scores_median"] <= 2
    assert classify.diagnostics(OK)["authored_scores_median"] == 16

def test_instrumentgrinden_kraver_ratt_prompt():
    if not classify.PROMPT_FILE.exists():
        pytest.skip("dataarkivet saknas - satt STATES_DATA (se README)")
    spec = json.loads(classify.SPEC_FILE.read_text(encoding="utf-8"))
    assert classify.sha(classify.PROMPT_FILE) == spec["canonical_prompt_sha256"]
