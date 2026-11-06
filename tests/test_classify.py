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
            "stated_observation_id": oid,
            "intensity": 0.5, "confidence": 0.7, "classification_note": "n"}

INP = [{"observation_id": "OBS-A"}, {"observation_id": "OBS-B"}]
OK = [rad("OBS-A", "Joy", "Hope"), rad("OBS-B", "Grief", "Concern")]
def kopia(): return json.loads(json.dumps(OK))

class _Blk:
    type = "text"
    def __init__(self, t): self.text = t

class _Msg:
    def __init__(self, rows): self.content = [_Blk(json.dumps(rows))]

def parsa(rows, inp=None):
    """parse() tar ett Message; testerna behover bara dess text."""
    return classify.parse(_Msg(rows), inp)

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

def test_overskottsnyckel_stryks_nar_alla_sexton_finns():
    """Overskott kastas och raknas. Uppmatt 2026-11-05: "", Surprise2,
    Surprise_dup, Fear_dup, Fear_note - alltid med alla sexton pa plats."""
    for extra in ("Surprise2", "Surprise_dup", "Fear_note", "Joie"):
        b = kopia(); b[0]["scores"][extra] = 0.1
        rows, artefakter = parsa(b)
        assert artefakter == 1, extra
        assert extra not in rows[0]["scores"] and len(rows[0]["scores"]) == 16
        assert classify.validate(rows, INP) == []

def test_felstavad_emotion_faller_nar_den_riktiga_saknas():
    """Sakerhetsvillkoret. Saknas "Joy" kan "Joie" vara en felstavning av den,
    och da far ingenting kastas - batchen ska falla som forut."""
    b = kopia()
    del b[0]["scores"]["Joy"]
    b[0]["scores"]["Joie"] = 0.9
    rows, artefakter = parsa(b)
    assert artefakter == 0 and "Joie" in rows[0]["scores"]
    fel = classify.validate(rows, INP)
    assert any("Joie" in f and "Joy" in f for f in fel)

def test_overskottsrad_kastas_nar_alla_begarda_finns():
    """Modellen lade till en tom vaktrad, OBS-..._DUP_GUARD, bredvid alla
    femtio riktiga. Den bar ingenting protokollet kraver."""
    b = kopia()
    vakt = json.loads(json.dumps(b[0]))
    vakt["observation_id"] = "OBS-A_DUP_GUARD"
    vakt["classification_note"] = "placeholder"
    b.append(vakt)
    rows, artefakter = parsa(b, INP)
    assert artefakter == 1 and len(rows) == 2
    assert {r["observation_id"] for r in rows} == {"OBS-A", "OBS-B"}
    assert classify.validate(rows, INP) == []

def test_stympat_id_aterstalls_genom_uteslutning():
    """Exakt ett begart id saknas, exakt ett okant finns: identiteten ar bestamd.

    Uppmatt pa 2026/308: modellen skrev OBS-231 i stallet for
    OBS-F3239B4CC67CBB1E. Ar de ovriga exakt matchade finns bara en observation
    kvar som raden kan vara. Logik, inte likhet - ingen troskel, inget antagande
    om ordning."""
    b = kopia()
    b[1]["observation_id"] = "OBS-231"
    rows, _ = parsa(b, INP)
    assert {r["observation_id"] for r in rows} == {"OBS-A", "OBS-B"}
    assert rows[1]["stated_observation_id"] == "OBS-231"   # modellens egna star kvar
    assert classify.validate(rows, INP) == []
    assert classify.diagnostics(rows)["stated_id_differs"] == 1

def test_tva_stympade_id_aterstalls_aldrig():
    """Tva okanda och tva saknade: uteslutningen ar inte entydig. Ingenting rors."""
    inp3 = INP + [{"observation_id": "OBS-C"}]
    b = kopia() + [rad("OBS-C", "Fear", "Anger")]
    b[1]["observation_id"] = "OBS-231"
    b[2]["observation_id"] = "OBS-E238"
    rows, _ = parsa(b, inp3)
    assert {r["observation_id"] for r in rows} == {"OBS-A", "OBS-231", "OBS-E238"}
    assert any("saknas" in f for f in classify.validate(rows, inp3))

def test_stympat_id_aterstalls_aldrig_vid_dubblett():
    """En dubblett betyder att radantalet stammer av fel anledning."""
    b = kopia()
    b[1]["observation_id"] = "OBS-A"
    rows, _ = parsa(b, INP)
    assert [r["observation_id"] for r in rows] == ["OBS-A", "OBS-A"]
    assert any("dubbletter" in f for f in classify.validate(rows, INP))

def test_overskottsrad_aterstalls_inte_som_id():
    """Fel radantal: en extra rad ar inte ett stympat id. Ingenting rors."""
    b = kopia()
    extra = rad("OBS-B_DUP_GUARD", "Calm", "Curiosity")
    b.append(extra)
    b[1]["observation_id"] = "OBS-231"       # och ett stympat id ovanpa
    rows, artefakter = parsa(b, INP)
    assert artefakter == 0 and len(rows) == 3
    assert any("saknas" in f for f in classify.validate(rows, INP))

def test_dubblerad_begard_rad_kastas_aldrig():
    """Forekommer ett begart id tva ganger gar det inte att veta vilken
    klassificering som galler. Ingenting kastas."""
    b = kopia()
    b.append(json.loads(json.dumps(b[0])))
    rows, artefakter = parsa(b, INP)
    assert artefakter == 0 and len(rows) == 3
    assert any("dubbletter" in f for f in classify.validate(rows, INP))

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


def test_id_felet_namner_skillnaden():
    """Felet ska saga vilka id som saknas, ar over och ar dubbletter.

    "observation_id stammer inte mot indata" kravde att nagon lade sig i
    rasvaret for att forstas. Uppmatt 2026-11-05: modellen slappte ett riktigt
    id och skrev ett pahittat med suffix i stallet - det gick inte att se ur
    meddelandet.
    """
    rows = kopia()
    rows[1]["observation_id"] = "OBS-B-DUP"          # slapper OBS-B, hittar pa ett
    fel = classify.validate(rows, INP)
    assert len(fel) == 1
    m = fel[0]
    assert "OBS-B" in m and "OBS-B-DUP" in m
    assert "saknas" in m and "over" in m

def test_id_felet_namner_dubbletter():
    rows = kopia()
    rows[1]["observation_id"] = "OBS-A"              # samma id tva ganger
    fel = classify.validate(rows, INP)
    assert any("dubbletter" in f and "OBS-A" in f for f in fel)


def test_tankandet_ar_per_modell():
    """Instrumentparametern ar "taenkandet av". Hur den uttrycks skiljer sig per
    modell, och det ar transport - ingen modell far en annan prompt.

    Uppmatt 2026-11-06: claude-opus-5-5 svarar 400 pa "disabled" och erbjuder
    bara adaptivt taenkande; claude-sonnet-5-5 vill ha "between_tools"."""
    assert classify.tankande_for("claude-opus-5") == {"type": "disabled"}
    assert classify.tankande_for("claude-sonnet-5-5") == {"type": "between_tools"}
    assert classify.tankande_for("en-okand-modell") == {"type": "disabled"}

def test_ett_400_kors_aldrig_om():
    """Fel parameter ar fel parameter aven vid forsok tva. Uppmatt 2026-11-06:
    nio rundresor av tre konfigurationsfel, eftersom BadRequestError arver
    APIError."""
    import anthropic
    class Status(anthropic.APIStatusError):
        # Byggs utan httpx: SDK:ns transportberoende ska inte avgora om ett test
        # gar att kora. ska_forsoka_igen laser bara status_code och typen.
        def __init__(self, kod): self.status_code = kod
    status = Status
    assert not classify.ska_forsoka_igen(status(400))   # fel parameter
    assert not classify.ska_forsoka_igen(status(401))   # fel nyckel
    assert classify.ska_forsoka_igen(status(429))       # hastighetsgrans
    assert classify.ska_forsoka_igen(status(503))       # tillfalligt
    assert classify.ska_forsoka_igen(json.JSONDecodeError("x", "y", 0))
    assert not classify.ska_forsoka_igen(ValueError("lokalt fel"))
