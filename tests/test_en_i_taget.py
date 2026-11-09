"""Matvagen for FYND 009: en observation per begaran.

Identifierarna glider ett steg i svansen av en batch om femtio, och felet gar
inte att reparera - tva rader gor ansprak pa samma observation. Med EN
observation per begaran finns ingen rad att halka mellan: identiteten kommer ur
begaran, inte ur modellens avskrift.

Vagen ar en MATVAG, inte ett beslut. Testet laser fast det som maste halla for
att mattet ska vara nagot vart:

  1. den frysta prompten och specen ror sig inte
  2. passfilen blir identisk i form, sa konsensus och farg inte ser skillnad
  3. ett betalt svar hamtas aldrig tva ganger
  4. ett dygn kort pa matvagen gar inte att forvaxla med ett kort pa den
     beslutade formen
"""
import json, sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import classify
from test_batchleverans import _Klient, _Msg, GILTIGT          # delade attrapper


def _obs(i):
    return {"observation_id": f"OBS-{i:016X}", "tile_index": i,
            "neutral_source_claim": f"Rubrik {i}", "review_region": "Europe",
            "selection_layer": "GLOBAL", "source_tier": "A",
            "representative_domain": "example.com"}

def _svar_for(oid):
    rad = json.loads(GILTIGT)[0]
    rad["observation_id"] = oid
    return json.dumps([rad], ensure_ascii=False)


class _BatchesEn:
    """Svarar med ratt observation per custom_id."""
    def __init__(s, items_per_batch): s.items = items_per_batch; s.skickade = []; s.jobb = 0
    def create(s, requests):
        s.skickade.append([r["custom_id"] for r in requests]); s.jobb += 1
        class J:
            id = f"msgbatch_{s.jobb}"
        return J()
    def retrieve(s, bid):
        class R:
            succeeded = len(s.skickade[-1]); errored = processing = canceled = expired = 0
        class J:
            id = bid; processing_status = "ended"; request_counts = R(); created_at = ended_at = None
        return J()
    def results(s, bid):
        ut = []
        for cid in s.skickade[-1]:
            p, n, i = classify.tyd_kund_id_en(cid)
            oid = s.items[n][i - 1]["observation_id"]
            class Rad:
                custom_id = cid
                class result:
                    type = "succeeded"
                    message = _Msg(_svar_for(oid))
            ut.append(Rad())
        return ut

class _KlientEn:
    def __init__(s, items_per_batch):
        class M: pass
        s.messages = M(); s.messages.batches = _BatchesEn(items_per_batch)


def test_prompten_och_specen_ror_sig_inte():
    """Prompten sager 'one object per supplied observation'. Med en observation
    ar svaret en array om ett objekt, och kontraktet haller ordagrant."""
    import inspect
    src = inspect.getsource(classify.kor_i_batch_en)
    assert "anropsparametrar(model, prompt, [it])" in src
    assert "PROMPT_FILE" in src           # samma hashkontroll som i ovrigt


def test_femtio_begaran_blir_en_passfil_i_vanlig_form(tmp_path, monkeypatch):
    items = {1: [_obs(i) for i in range(1, 51)]}
    monkeypatch.setattr(classify, "passdir", lambda day: tmp_path)
    monkeypatch.setattr(classify, "batches", lambda day: list(items.items()))
    k = _KlientEn(items)
    rec = {"calls": []}
    classify.kor_i_batch_en(k, "claude-opus-5", "prompt", "20261201",
                            [(1, 1, items[1])], tmp_path, rec, "omg")
    fil = tmp_path / "pass1_batch_01.json"
    assert fil.exists(), "ingen passfil skrevs"
    rows = json.loads(fil.read_text(encoding="utf-8"))
    assert len(rows) == 50
    assert [r["observation_id"] for r in rows] == [o["observation_id"] for o in items[1]], \
        "raderna star inte i indatans ordning"
    assert rec["calls"][0]["requests"] == 50
    assert rec["calls"][0]["delivery"] == "batch_en_i_taget"


def test_ett_betalt_svar_hamtas_aldrig_tva_ganger(tmp_path, monkeypatch):
    """Artonhundra begaran kan behova flera ronder. Delresultaten ligger kvar."""
    items = {1: [_obs(i) for i in range(1, 51)]}
    monkeypatch.setattr(classify, "passdir", lambda day: tmp_path)
    monkeypatch.setattr(classify, "batches", lambda day: list(items.items()))
    k = _KlientEn(items)
    classify.kor_i_batch_en(k, "claude-opus-5", "prompt", "20261201",
                            [(1, 1, items[1])], tmp_path, {"calls": []}, "omg")
    forsta = len(k.messages.batches.skickade)
    # kor igen: allt finns, ingenting ska skickas
    classify.kor_i_batch_en(k, "claude-opus-5", "prompt", "20261201",
                            [(1, 1, items[1])], tmp_path, {"calls": []}, "omg")
    assert len(k.messages.batches.skickade) == forsta, "skickade om redan betalda begaran"


def test_delresultat_overlever_och_bara_det_som_saknas_begars(tmp_path, monkeypatch):
    items = {1: [_obs(i) for i in range(1, 51)]}
    monkeypatch.setattr(classify, "passdir", lambda day: tmp_path)
    monkeypatch.setattr(classify, "batches", lambda day: list(items.items()))
    k = _KlientEn(items)
    # lagg 48 av 50 pa plats som om en tidigare rond redan betalat dem
    kat = classify.endir(tmp_path)
    for i in range(1, 49):
        rad = json.loads(_svar_for(items[1][i - 1]["observation_id"]))[0]
        (kat / f"{classify.kund_id_en(1, 1, i)}.json").write_text(json.dumps(
            {"row": rad, "artefakter": 0, "batch_id": "gammalt",
             "usage": {"input_tokens": 1, "output_tokens": 1,
                       "cache_read": 0, "cache_write": 0}}), encoding="utf-8")
    classify.kor_i_batch_en(k, "claude-opus-5", "prompt", "20261201",
                            [(1, 1, items[1])], tmp_path, {"calls": []}, "omg")
    assert len(k.messages.batches.skickade[0]) == 2, (
        f"begarde {len(k.messages.batches.skickade[0])} i stallet for de 2 som saknades")


def test_dygnet_markeras_i_journalen():
    """Ett dygn kort pa matvagen far aldrig forvaxlas med ett kort pa den
    beslutade formen."""
    import inspect
    src = inspect.getsource(classify.run)
    assert 'rec["delivery_form"] = "en_observation_per_begaran"' in src
    assert "FYND 009" in src
