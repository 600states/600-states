"""Leveransen ar Batch API, och ett jobb far aldrig betalas tva ganger.

Beslutet "Batch API, 50 % av listpris" stod i parameterregistret fran
2026-11-06 och fanns inte i koden. Tva dygn kordes till fullt pris, och taket
slog i mitt i 2026/309. Samma form som FYND 001-004: regeln i ett dokument,
aldrig i den kodvag som avgor.

Det har testet gor leveransvagen till en grind, och provar det som daglig
obevakad drift faktiskt kraver:

  1. batch ar standardvagen
  2. begaran ar BYTE FOR BYTE densamma som direktvagens
  3. jobbfilen skrivs INNAN vantan - annars betalar nasta korning en gang till
  4. en korning som hittar en jobbfil HAMTAR, den skickar inte
  5. jobbfilen raderas nar svaren ar omhandertagna
  6. en batch som redan har sin passfil skrivs inte over
"""
import json, sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import classify


class _Usage:
    input_tokens = 100; output_tokens = 200
    cache_read_input_tokens = 0; cache_creation_input_tokens = 0

class _Block:
    type = "text"
    def __init__(s, t): s.text = t

class _Msg:
    def __init__(s, text): s.content = [_Block(text)]; s.usage = _Usage()

class _Rakning:
    def __init__(s, k): s.succeeded = k; s.errored = 0; s.processing = 0
    canceled = expired = 0

class _Jobb:
    def __init__(s, bid, n): s.id = bid; s.processing_status = "ended"; s.request_counts = _Rakning(n)

class _Resultat:
    def __init__(s, msg): s.type = "succeeded"; s.message = msg

class _Rad:
    def __init__(s, cid, msg): s.custom_id = cid; s.result = _Resultat(msg)

class _Batches:
    def __init__(s, svar):
        s.svar = svar; s.skickade = []; s.hamtade = []
    def create(s, requests):
        s.skickade.append([r["custom_id"] for r in requests])
        return _Jobb(f"batch_{len(s.skickade)}", len(requests))
    def retrieve(s, bid):
        return _Jobb(bid, len(s.skickade[-1]))
    def results(s, bid):
        s.hamtade.append(bid)
        return [_Rad(cid, _Msg(s.svar)) for cid in s.skickade[-1]]

class _Meddelanden:
    def __init__(s, svar): s.batches = _Batches(svar)

class _Klient:
    def __init__(s, svar=None): s.messages = _Meddelanden(svar if svar is not None else GILTIGT)


def _giltigt_svar(oid="OBS-1"):
    """Ett svar som gar igenom parse och validate, sa att testet provar
    leveransvagen och inte valideringen."""
    from vocab import EMOTION_STATES
    poang = {e: 0.0 for e in EMOTION_STATES}
    for e, v in zip(EMOTION_STATES, (0.62, 0.41, 0.33, 0.27, 0.21, 0.18,
                                     0.14, 0.11, 0.09, 0.07, 0.06, 0.04)):
        poang[e] = v
    rad = {"observation_id": oid,
           "neutral_event_representation": "En handelse som instrumentet last.",
           "scores": poang,
           "primary_emotion": EMOTION_STATES[0],
           "secondary_emotion": EMOTION_STATES[1],
           "intensity": 0.57, "confidence": 0.63,
           "classification_note": "Testrad."}
    import json as _json
    return _json.dumps([rad], ensure_ascii=False)

GILTIGT = _giltigt_svar()


def test_batch_ar_leveransvagen():
    assert classify.LEVERANS == "batch", (
        "parameterregistret: leverans Batch API, 50 % av listpris, faststallt 2026-11-06")


def test_begaran_ar_identisk_med_direktvagens():
    """Tva vagar till samma instrument, eller inget av dem."""
    import inspect
    assert "anropsparametrar(model, prompt, items)" in inspect.getsource(classify.call)
    assert "anropsparametrar(model, prompt, items)" in inspect.getsource(classify.skicka_jobb)


def test_jobbfilen_skrivs_innan_vantan_borjar(tmp_path, monkeypatch):
    """Ett jobb ar betalt i samma stund det tas emot."""
    monkeypatch.setattr(classify, "passdir", lambda day: tmp_path)
    k = _Klient()
    bid = classify.skicka_jobb(k, "claude-opus-5", "prompt", "20261201",
                               [(1, 1, [{"observation_id": "OBS-1"}])])
    sparat = json.loads((tmp_path / "batch_jobb.json").read_text(encoding="utf-8"))
    assert sparat["id"] == bid
    assert sparat["begaran"] == ["pass1_batch01"]
    assert sparat["prompt_sha256"]


def test_kund_id_gar_att_tyda_tillbaka():
    for p, n in ((1, 1), (3, 12)):
        assert classify.tyd_kund_id(classify.kund_id(p, n)) == (p, n)


def test_en_hittad_jobbfil_hamtas_i_stallet_for_att_skickas(tmp_path, monkeypatch):
    """Det har ar skyddet mot dubbel betalning i en obevakad korning."""
    monkeypatch.setattr(classify, "passdir", lambda day: tmp_path)
    monkeypatch.setattr(classify, "batches", lambda day: [(1, [{"observation_id": "OBS-1"}])])
    k = _Klient()
    k.messages.batches.skickade.append(["pass1_batch01"])      # som om ett jobb redan gatt ivag
    (tmp_path / "batch_jobb.json").write_text(json.dumps(
        {"id": "batch_1", "skickat": "igar", "begaran": ["pass1_batch01"],
         "prompt_sha256": classify.sha(classify.PROMPT_FILE)}), encoding="utf-8")
    rec = {"calls": []}
    classify.kor_i_batch(k, "claude-opus-5", "prompt", "20261201",
                         [(1, 1, [{"observation_id": "OBS-1"}])], tmp_path, rec, "omg")
    assert len(k.messages.batches.skickade) == 1, "ett nytt jobb skickades trots att ett lag kvar"
    assert k.messages.batches.hamtade == ["batch_1"]


def test_jobbfilen_rensas_nar_svaren_ar_omhandertagna(tmp_path, monkeypatch):
    monkeypatch.setattr(classify, "passdir", lambda day: tmp_path)
    monkeypatch.setattr(classify, "batches", lambda day: [(1, [{"observation_id": "OBS-1"}])])
    k = _Klient()
    rec = {"calls": []}
    classify.kor_i_batch(k, "claude-opus-5", "prompt", "20261201",
                         [(1, 1, [{"observation_id": "OBS-1"}])], tmp_path, rec, "omg")
    assert not (tmp_path / "batch_jobb.json").exists()


def test_en_batch_med_passfil_rors_inte(tmp_path, monkeypatch):
    """Passfiler som finns hoppas over - att fullborda en korning far aldrig
    skriva om det som redan ar klassificerat."""
    monkeypatch.setattr(classify, "passdir", lambda day: tmp_path)
    monkeypatch.setattr(classify, "batches", lambda day: [(1, [{"observation_id": "OBS-1"}])])
    f = tmp_path / "pass1_batch_01.json"
    f.write_text('["redan klart"]', encoding="utf-8")
    k = _Klient()
    classify.kor_i_batch(k, "claude-opus-5", "prompt", "20261201",
                         [(1, 1, [{"observation_id": "OBS-1"}])], tmp_path, {"calls": []}, "omg")
    assert f.read_text(encoding="utf-8") == '["redan klart"]'
    assert k.messages.batches.skickade == [], "skickade en begaran for en batch som redan var klar"
