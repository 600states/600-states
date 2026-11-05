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
            "stated_primary": pri, "stated_secondary": sec,
            "intensity": 0.5, "confidence": 0.7, "classification_note": "n"}

INP = [{"observation_id": "OBS-A"}, {"observation_id": "OBS-B"}]
OK = [rad("OBS-A", "Joy", "Hope"), rad("OBS-B", "Grief", "Concern")]
def kopia(): return json.loads(json.dumps(OK))

class _Blk:
    type = "text"
    def __init__(self, t): self.text = t

class _Msg:
    def __init__(self, rows): self.content = [_Blk(json.dumps(rows))]

def parsa(rows):
    """parse() tar ett Message; testerna behover bara dess text."""
    return classify.parse(_Msg(rows))

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

def test_primary_och_secondary_harleds_ur_scores():
    """Specen definierar falten som harledda: primary_must_rank_first,
    secondary_must_rank_second. Modellens etikett ar en bedomning vid sidan."""
    s = {e: 0.1 for e in EMOTION_STATES}; s["Tension"], s["Fear"] = 0.9, 0.8
    rows, _ = parsa([{"scores": s, "primary_emotion": "Hope",
                      "secondary_emotion": "Surprise"}])
    assert (rows[0]["primary_emotion"], rows[0]["secondary_emotion"]) == ("Tension", "Fear")
    assert (rows[0]["stated_primary"], rows[0]["stated_secondary"]) == ("Hope", "Surprise")

def test_lika_poang_avgors_av_den_frysta_ordningen():
    """Samma skiljedomarregel som vocab.arbitrate(): lagsta index vinner."""
    s = {e: 0.1 for e in EMOTION_STATES}
    s["Fear"] = s["Hope"] = 0.9                      # lika hogst, Hope lagre index
    assert classify.derive(s) == ("Hope", "Fear")
    s2 = {e: 0.1 for e in EMOTION_STATES}
    s2["Tension"] = 0.9
    s2["Anger"] = s2["Relief"] = 0.8                 # lika tvaa, Relief lagre index
    assert classify.derive(s2) == ("Tension", "Relief")

def test_harledningen_ar_oberoende_av_nyckelordningen():
    """Vore JSON-ordningen med i sorteringen vore faltet inte reproducerbart."""
    s = {e: 0.1 for e in EMOTION_STATES}; s["Tension"], s["Fear"] = 0.9, 0.8
    bakvant = {e: s[e] for e in reversed(EMOTION_STATES)}
    assert classify.derive(s) == classify.derive(bakvant) == ("Tension", "Fear")

def test_tomnamnad_nyckel_stryks_och_raknas():
    """Ett emissionsfel i kompakt JSON, inte en sextonde-nyckel-overtradelse."""
    s = {e: 0.1 for e in EMOTION_STATES}; s[""] = 0
    rows, artefakter = parsa([{"scores": s, "primary_emotion": "Joy",
                               "secondary_emotion": "Hope"}])
    assert artefakter == 1 and "" not in rows[0]["scores"]
    assert len(rows[0]["scores"]) == 16

def test_felstavad_emotion_stryks_aldrig():
    """"Joie" ar en helt annan sak an ett emissionsfel och far inte smyga igenom."""
    b = kopia(); b[0]["scores"]["Joie"] = 0.1
    rows, artefakter = parsa(b)
    assert artefakter == 0 and "Joie" in rows[0]["scores"]
    assert any("Joie" in f for f in classify.validate(rows, INP))

def test_modellens_egen_bedomning_maste_finnas():
    """Vi slutar krava att den stammer, inte att den finns."""
    for falt in ("stated_primary", "stated_secondary"):
        b = kopia(); b[0][falt] = None
        assert any(falt in f for f in classify.validate(b, INP))

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

def _journal(tmp_path, monkeypatch):
    """Journalen OCH passkatalogen pekas om. passdir() skapar katalogen den
    pekar pa, sa ett test som bara pekar om journalen lamnar en tom katalog i
    dataarkivet."""
    fil = tmp_path / "RUN.json"
    passar = tmp_path / "classifier_passes"; passar.mkdir(exist_ok=True)
    monkeypatch.setattr(classify, "journalfil", lambda day: fil)
    monkeypatch.setattr(classify, "passdir", lambda day: passar)
    return fil

BAS = {"model": "m", "prompt_sha256": "p", "spec_sha256": "s"}
def anrop(i, o, c): return {"input_tokens": i, "output_tokens": o, "cache_read": c}

def test_journalen_vaxer_over_omgangar(tmp_path, monkeypatch):
    """Ett dygns trettio anrop tas i flera omgangar. Journalen ar manifestets
    proveniensansprak och far inte beskriva bara den sista."""
    fil = _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [anrop(10, 20, 0)]}, 1)
    gammal = classify.las_journal("20260101", BAS)
    classify.skriv_journal("20260101", gammal, {**BAS, "calls": [anrop(5, 7, 3)]}, 2)
    ut = json.loads(fil.read_text(encoding="utf-8"))
    assert len(ut["calls"]) == 2
    assert ut["totals"] == {"calls": 2, "input": 15, "output": 27, "cache_read": 3,
                            "parse_failures": 3}

def test_byte_av_instrument_mitt_i_ett_dygn_stoppar(tmp_path, monkeypatch):
    """Annan modell, prompt eller spec an i tidigare omgangar ar ett annat
    instrument - grinden gar fore anropen, inte efter."""
    _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [anrop(1, 1, 0)]}, 0)
    for falt in ("model", "prompt_sha256", "spec_sha256"):
        with pytest.raises(classify.gates.GateFailure) as e:
            classify.las_journal("20260101", {**BAS, falt: "annan"})
        assert falt in str(e.value)

def test_en_omgang_utan_anrop_skriver_ingenting(tmp_path, monkeypatch):
    fil = _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": []}, 0)
    assert not fil.exists()

def test_journalen_namner_passfiler_den_inte_tacker(tmp_path, monkeypatch):
    """FYND 001: en journal som tiger om sina luckor ar ett tyst osant
    pastaende. Luckan uppstar nar en batch klassificerades utan att anropet
    hann skrivas, och usage gar inte att rekonstruera i efterhand."""
    fil = _journal(tmp_path, monkeypatch)
    passar = tmp_path / "classifier_passes"
    (passar / "pass1_batch_01.json").write_text("[]", encoding="utf-8")
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [anrop(1, 1, 0)]}, 0)
    ut = json.loads(fil.read_text(encoding="utf-8"))
    assert ut["unrecorded"] == ["pass1_batch_01"]
    assert "usage" in ut["unrecorded_note"]

def test_lucklistan_raknas_om_och_arvs_inte(tmp_path, monkeypatch):
    """Listan ar en matning av disken, inte ett pastaende som arvs."""
    fil = _journal(tmp_path, monkeypatch)
    passar = tmp_path / "classifier_passes"
    (passar / "pass1_batch_01.json").write_text("[]", encoding="utf-8")
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [anrop(1, 1, 0)]}, 0)
    gammal = classify.las_journal("20260101", BAS)
    assert gammal["unrecorded"] == ["pass1_batch_01"]
    # samma batch skrivs nu med ett anrop i journalen: luckan ar borta
    classify.skriv_journal("20260101", gammal,
                           {**BAS, "calls": [dict(anrop(1, 1, 0), **{"pass": 1, "batch": 1})]}, 0)
    ut = json.loads(fil.read_text(encoding="utf-8"))
    assert ut["unrecorded"] == [] and "unrecorded_note" not in ut
