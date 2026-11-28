"""Klassificeringsanropets validering. Den sista grinden fore konsensus."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
import classify
from vocab import EMOTION_STATES
from conftest import SPEC_PRECISION, kraver_arkiv, pinna_specens_decimalkrav


@pytest.fixture(autouse=True)
def _pinna_decimalkravet(monkeypatch):
    """validate() laser decimalkravet ur den frysta specen vid varje anrop.
    Inget test i den har filen handlar om decimaler. Se conftest.py."""
    pinna_specens_decimalkrav(monkeypatch)

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

@kraver_arkiv
def test_pinnade_decimalkravet_ar_specens():
    """Sviten pinnar decimalkravet sa att tester om helt andra pastaenden gar
    att kora utan arkivet. Ett pinnat varde ar vardelost om det inte ar
    specens, och har knyts de ihop. Filen lases direkt, forbi den pinnade
    funktionen - annars provar testet sin egen attrapp."""
    spec = json.loads(classify.SPEC_FILE.read_text(encoding="utf-8"))
    assert spec["score_precision"] == SPEC_PRECISION


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
    # HELA dicten jamfors, inte valda nycklar. En ny nyckel i totals ska gora
    # provet rott och tvinga fram ett medvetet beslut - journalen ar
    # manifestets proveniensansprak och far inte vaxa tyst. De tva nedan kom
    # med A21, 2026-11-27.
    assert ut["totals"] == {"calls": 2, "input": 15, "output": 27, "cache_read": 3,
                            "parse_failures": 3,
                            "begaran": {"skickade": 2, "lyckade": 2,
                                        "fallna_kanda": 0, "fallna_okanda": 0},
                            "fallna_tokens": {"input": 0, "output": 0,
                                              "cache_read": 0, "cache_write": 0},
                            "cache_write": 0}


# ---- A21: journalen bokfor ANROP, inte resultat -------------------------
#
# Fram till b228420 bokfordes ett anrop forst nar det lyckats hela vagen. Ett
# svar som kom tillbaka, kostade pengar och foll pa parsning eller validering
# slapptes som kostnad. Tre utfall provas nedan, och de far aldrig slas ihop:
# ett fallet anrop ar inte ett lyckat, och ett okant ar inte ett nollat.

def fallet(i, o, c): return {**anrop(i, o, c), "utfall": "fallet"}
def okant(): return {"input_tokens": None, "output_tokens": None,
                     "cache_read": None, "utfall": "okand"}


def test_ett_fallet_anrop_bokfors_med_sina_tal(tmp_path, monkeypatch):
    """Svaret kom tillbaka och kostade pengar. Talen gar att lasa, sa de ska
    bokforas - men inte bland de lyckade, for da sager journalen att dygnet
    producerade mer an det gjorde."""
    fil = _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [anrop(10, 20, 5),
                                                             fallet(3, 7, 1)]}, 0)
    t = json.loads(fil.read_text(encoding="utf-8"))["totals"]
    assert (t["input"], t["output"], t["cache_read"]) == (10, 20, 5)
    assert t["fallna_tokens"] == {"input": 3, "output": 7,
                                  "cache_read": 1, "cache_write": 0}
    assert t["begaran"] == {"skickade": 2, "lyckade": 1,
                            "fallna_kanda": 1, "fallna_okanda": 0}


def test_ett_okant_anrop_bokfors_som_okant_aldrig_som_noll(tmp_path, monkeypatch):
    """API:et rapporterade sjalvt fel: errored, canceled eller expired bar
    inget message, sa det finns ingen usage att lasa. En nollrad och en
    saknad rad ljuger bada - en rad som sager okand ar sann."""
    fil = _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [anrop(10, 20, 5),
                                                             okant()]}, 0)
    ut = json.loads(fil.read_text(encoding="utf-8"))
    t = ut["totals"]
    assert t["begaran"]["fallna_okanda"] == 1
    # Talen far INTE summeras som nollor nagonstans.
    assert (t["input"], t["output"]) == (10, 20)
    assert t["fallna_tokens"] == {"input": 0, "output": 0,
                                  "cache_read": 0, "cache_write": 0}
    # Och raden sjalv bar null i filen, inte 0.
    rad = [x for x in ut["calls"] if x.get("utfall") == "okand"][0]
    assert rad["input_tokens"] is None and rad["output_tokens"] is None


def test_en_fallen_rad_gor_inte_passfilen_tackt(tmp_path, monkeypatch):
    """unrecorded ar listan over passfiler journalen inte tacker. Raknades en
    fallen rad som inspelad skulle ett dygn dar passfilen finns men bara
    felraderna tacktes se komplett ut."""
    fil = _journal(tmp_path, monkeypatch)
    (tmp_path / "classifier_passes" / "pass1_batch_01.json").write_text("[]", encoding="utf-8")
    rad = {**fallet(1, 1, 0), "pass": 1, "batch": 1}
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [rad]}, 0)
    assert json.loads(fil.read_text(encoding="utf-8"))["unrecorded"] == ["pass1_batch_01"]


def test_kontrollprov_en_lyckad_rad_gor_passfilen_tackt(tmp_path, monkeypatch):
    """Provet ovan pastar en narvaro i listan. Utan det har provet kunde
    unrecorded namna varje passfil alltid."""
    fil = _journal(tmp_path, monkeypatch)
    (tmp_path / "classifier_passes" / "pass1_batch_01.json").write_text("[]", encoding="utf-8")
    rad = {**anrop(1, 1, 0), "pass": 1, "batch": 1}
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [rad]}, 0)
    assert json.loads(fil.read_text(encoding="utf-8"))["unrecorded"] == []


def test_journalen_doljer_inte_skillnaden_mellan_talen(tmp_path, monkeypatch):
    """ARBETSDELNINGEN, SKRIVEN 2026-11-27 EFTER ad50b48.

    skriv_journal BOKFOR, den domer inte. Journalen ar manifestets
    proveniensansprak, och den ska skriva vad som hande aven nar det inte
    gick ihop - en journal som vagrar bli till nar nagot ar fel tar bort
    just det spar som behovs for att forsta felet.

    totals.begaran.skickade raknas ur journalens egna rader, sa identiteten
    skickade = lyckade + fallna + okanda ar sann per
    konstruktion. Det oberoende talet ar batch_latency_seconds[].requests,
    skrivet ur jobbfilen FORE resultatslingan. Provet visar att de tva kan
    saga olika saker OCH att bada talen star kvar i filen.

    DET AR GRINDEN SOM UPPTACKER SKILLNADEN, inte skrivningen - se
    test_grinden_faller_nar_ett_skickat_anrop_saknar_rad nedan.
    """
    fil = _journal(tmp_path, monkeypatch)
    rec = {**BAS, "calls": [anrop(1, 1, 0), anrop(1, 1, 0)],
           "batch_latency_seconds": [{"batch_id": "b1", "requests": 3, "seconds": 1.0}]}
    classify.skriv_journal("20260101", {}, rec, 0)
    ut = json.loads(fil.read_text(encoding="utf-8"))
    oberoende = sum(x["requests"] for x in ut["batch_latency_seconds"])
    assert oberoende == 3
    assert ut["totals"]["begaran"]["skickade"] == 2
    # Tre skickade, tva med rad - och ingenting sager ifran.
    assert oberoende != ut["totals"]["begaran"]["skickade"]

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


# ---- grinden som upptacker ett obokfort anrop (ad50b48) -----------------

def batchrad(bid="b1"): return {**anrop(1, 1, 0), "batch_id": bid}
def jobb(bid="b1", n=1): return {"batch_id": bid, "requests": n, "seconds": 1.0}


def test_grinden_faller_nar_ett_skickat_anrop_saknar_rad(tmp_path, monkeypatch):
    """Tre skickade enligt jobbet, tva med rad. Det egna talet foljer med
    ner i felet; det oberoende gor det inte."""
    _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [batchrad(), batchrad()],
                                            "batch_latency_seconds": [jobb(n=3)]}, 0)
    with pytest.raises(classify.gates.GateFailure) as e:
        classify.gate_journalen_tacker_anropen("20260101", tmp_path)
    assert "saknar rad" in str(e.value)


def test_grinden_faller_aven_at_andra_hallet(tmp_path, monkeypatch):
    """En rad utan skickat anrop ar ocksa en journal som inte ar lika med
    dygnet. Faller bara det ena hallet provar provet riktningen, inte
    likheten."""
    _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [batchrad(), batchrad()],
                                            "batch_latency_seconds": [jobb(n=1)]}, 0)
    with pytest.raises(classify.gates.GateFailure) as e:
        classify.gate_journalen_tacker_anropen("20260101", tmp_path)
    assert "har rad utan att ha skickats" in str(e.value)


def test_kontrollprov_grinden_slapper_igenom_nar_talen_stammer(tmp_path, monkeypatch):
    """Proven ovan ar vardelosa om grinden faller pa allt."""
    _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [batchrad(), batchrad()],
                                            "batch_latency_seconds": [jobb(n=2)]}, 0)
    classify.gate_journalen_tacker_anropen("20260101", tmp_path)


def test_utan_oberoende_tal_faller_grinden_inte_men_sager_det(tmp_path, monkeypatch, capsys):
    """Tredje tillstandet. Ett jobb utan created_at lamnar ingen rad i
    batch_latency_seconds, och da FINNS inget oberoende tal. Leverantorens
    metadata ar inte var bokforing och far inte stoppa ett fryst dygn - men
    tystnad far aldrig lasas som 'lika'."""
    _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [batchrad()]}, 0)
    classify.gate_journalen_tacker_anropen("20260101", tmp_path)
    ut = capsys.readouterr().out
    assert "INGET OBEROENDE TAL" in ut
    assert "b1" in ut


def test_batchraderna_vaxer_over_omgangar_och_raknas_inte_tva_ganger(
        tmp_path, monkeypatch, capsys):
    """FORUTSATTNINGEN SOM INTE HOLL fore ad50b48: {**gammal, **rec} lat en
    senare omgangs batch_latency_seconds ERSATTA den tidigare. Ett dygn taget
    i tva processer - normallaget med --slapp - tappade forsta jobbets
    oberoende tal medan dess anrop lag kvar bland raderna.

    ANDRA OMGANGEN SKICKAR BARA SITT EGET JOBB. Det ar hela poangen: en
    process som hamtar b2 vet ingenting om b1. Skickar provet bada ser
    ersattning och sammanslagning likadana ut, och provet prover ingenting -
    sa sag forsta versionen av det har provet ut.

    Faller sammanslagningen bort hamnar b1 utan oberoende tal, och grinden
    degraderar tyst till tredje tillstandet i stallet for att jamfora. Den
    faller inte - den slutar prova. Darfor provas UTSKRIFTEN."""
    _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [batchrad("b1")],
                                            "batch_latency_seconds": [jobb("b1")]}, 0)
    gammal = classify.las_journal("20260101", BAS)
    classify.skriv_journal("20260101", gammal,
                           {**BAS, "calls": [batchrad("b2")],
                            "batch_latency_seconds": [jobb("b2")]}, 0)
    capsys.readouterr()
    classify.gate_journalen_tacker_anropen("20260101", tmp_path)
    ut = capsys.readouterr().out
    assert "INGET OBEROENDE TAL" not in ut, "b1 tappade sitt oberoende tal"
    assert "2 skickade enligt jobben, 2 med rad" in ut


def test_samma_jobb_tva_ganger_raknas_en_gang(tmp_path, monkeypatch):
    """En aterupptagen korning hamtar samma jobb igen. Det ar samma skickade
    anrop, inte nya - raknas det tva ganger faller grinden pa en atergang."""
    _journal(tmp_path, monkeypatch)
    classify.skriv_journal("20260101", {}, {**BAS, "calls": [batchrad("b1")],
                                            "batch_latency_seconds": [jobb("b1")]}, 0)
    gammal = classify.las_journal("20260101", BAS)
    classify.skriv_journal("20260101", gammal,
                           {**BAS, "calls": [], "batch_latency_seconds": [jobb("b1")]}, 0)
    classify.gate_journalen_tacker_anropen("20260101", tmp_path)   # faller inte


def test_en_journal_som_inte_finns_ar_inget_godkant(tmp_path, monkeypatch, capsys):
    """Grinden far inte tiga sig forbi en saknad journal."""
    _journal(tmp_path, monkeypatch)
    classify.gate_journalen_tacker_anropen("20260101", tmp_path)
    assert "ingen korjournal" in capsys.readouterr().out
