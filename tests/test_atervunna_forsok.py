"""Acceptanstest for FYND 012: grinden ska rakna ogiltiga RADER, inte forsok.

Opus-korningen 2026-11-11 09:12 hade tva forsok som foll i rond 1 och lyckades
i rond 2. Alla 150 rader var kompletta och giltiga, men fel_tot bar de tva
forsoken vidare och korningen fick FALLER. Omforsoket finns for att laka just
det; grinden raknade det som ett haveri - och beslutsregeln vi satt i forvag
hade da slagit ut produktionsmodellen pa ett fel koden sjalv lagade.

Skrivet av den andra parten an den som atgardade, enligt AGENTS.md.

GRINDEN HAR TVA GRENAR och ett test som bara provar den ena missar halften:
  - en-i-taget-formen: en rad som aldrig blir giltig fangas av PASSGRINDEN,
    passet blir ofullstandigt och korningen faller pa "bara N av M pass"
  - direktvagen: grind_ur_spec:s felgren, dar ett pass med valideringsfel
    accepteras vid sista forsoket
Bada provas har.
"""
import json, sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT / "tools"))
import classify
import calibrate
from test_batchleverans import _Msg, GILTIGT


def _obs(i):
    return {"observation_id": f"OBS-{i:016X}", "tile_index": i,
            "neutral_source_claim": f"Rubrik {i}", "review_region": "Europe",
            "selection_layer": "GLOBAL", "source_tier": "A",
            "representative_domain": "example.com"}

def _giltigt(oid):
    rad = json.loads(GILTIGT)[0]
    rad["observation_id"] = oid
    return json.dumps([rad], ensure_ascii=False)

def _extra_data(oid):
    """Felformen exakt som den intraffade: giltig JSON foljd av extra text."""
    return _giltigt(oid) + "\n\nNote: the above reflects my reading.\n"


class _Batches:
    """Svarar giltigt utom for de custom_id som ska falla, i angivna ronder."""
    def __init__(s, obs, faller):
        s.obs, s.faller, s.skickade, s.rond = obs, faller, [], 0
    def create(s, requests):
        s.rond += 1
        s.skickade.append([(r["custom_id"], s.rond) for r in requests])
        class J: id = f"msgbatch_{s.rond}"
        return J()
    def retrieve(s, bid):
        class J: processing_status = "ended"
        return J()
    def results(s, bid):
        ut = []
        for cid, rond in s.skickade[-1]:
            p, i = (int(x) for x in cid.replace("pass", "").split("_obs"))
            oid = s.obs[i - 1]["observation_id"]
            trasig = rond in s.faller.get(cid, ())
            class R:
                custom_id = cid
                class result:
                    type = "succeeded"
                    message = _Msg(_extra_data(oid) if trasig else _giltigt(oid))
            ut.append(R())
        return ut

class _Klient:
    def __init__(s, obs, faller):
        class M: pass
        s.messages = M(); s.messages.batches = _Batches(obs, faller)


def _kor(tmp_path, monkeypatch, faller, n=2, passes=1):
    obs = [_obs(i) for i in range(1, n + 1)]
    monkeypatch.setattr(calibrate, "REMEDIATION", tmp_path)
    klient = _Klient(obs, faller)
    P, usage, fel, art, atervunna = calibrate.kor_en_i_taget(
        klient, "testmodell", "PROMPT", obs, passes, "STAMPEL")
    return P, fel, atervunna, tmp_path / "kalibrering_rasvar" / "testmodell_en_i_taget_STAMPEL"


# ---- 1. ett lakt omforsok ar inget haveri -------------------------------
def test_atervunnet_omforsok_ger_inga_ogiltiga_rader(tmp_path, monkeypatch):
    P, fel, atervunna, _ = _kor(tmp_path, monkeypatch, {"pass1_obs002": (1,)})
    assert fel == [], "en rad som lyckades i rond 2 ar ingen ogiltig rad"
    assert atervunna == 1
    assert len(P) == 1, "passet ska vara fullstandigt"


def test_grinden_slapper_igenom_en_korning_som_lakte_sig_sjalv(tmp_path, monkeypatch):
    _, fel, atervunna, _ = _kor(tmp_path, monkeypatch, {"pass1_obs002": (1,)})
    prompt, spec = classify.gate_instrument()
    grind, skal = calibrate.grind_ur_spec([], spec, fel)
    assert grind, f"skulle klara, foll pa: {skal}"
    assert atervunna == 1, "men omforsoket ska synas som eget matt"


def test_atervunna_forsok_grindar_aldrig(tmp_path, monkeypatch):
    """Instrumentets halsa rapporteras. Den faller inte en korning."""
    _, fel, atervunna, _ = _kor(tmp_path, monkeypatch,
                                {"pass1_obs001": (1,), "pass1_obs002": (1,)})
    prompt, spec = classify.gate_instrument()
    assert atervunna == 2
    assert calibrate.grind_ur_spec([], spec, fel)[0]


# ---- 2. en rad som aldrig blir giltig ----------------------------------
def test_rad_som_aldrig_blir_giltig_lamnar_passet_ofullstandigt(tmp_path, monkeypatch):
    """En-i-taget-formen: passgrinden fangar den, inte grind_ur_spec."""
    alla_ronder = tuple(range(1, classify.MAX_TRIES + 1))
    P, fel, atervunna, _ = _kor(tmp_path, monkeypatch, {"pass1_obs002": alla_ronder})
    assert P == [], "ett ofullstandigt pass far inte raknas som ett pass"
    assert len(fel) == 1, "raden ska bara bidra med en post, inte en per rond"
    assert atervunna == 0


def test_en_rad_bidrar_med_en_post_oavsett_antal_ronder(tmp_path, monkeypatch):
    """Annars faller en rad hardare an en annan bara for att den fick fler
    ronder pa sig."""
    alla = tuple(range(1, classify.MAX_TRIES + 1))
    _, fel, _, _ = _kor(tmp_path, monkeypatch, {"pass1_obs002": alla})
    assert len(fel) == 1
    assert "obs002" in fel[0]


# ---- 3. grind_ur_spec:s felgren lever (direktvagen) ---------------------
def test_grind_ur_spec_faller_pa_en_ogiltig_rad():
    prompt, spec = classify.gate_instrument()
    grind, skal = calibrate.grind_ur_spec([], spec, ["pass1_obs002: Extra data"])
    assert not grind
    assert "ogiltiga rader" in " ".join(skal).lower() or "rader" in " ".join(skal).lower()


def test_grind_ur_spec_klarar_med_tom_fellista():
    prompt, spec = classify.gate_instrument()
    assert calibrate.grind_ur_spec([], spec, [])[0]


# ---- 4. ett misslyckat forsok lamnar spar ------------------------------
def test_misslyckat_forsok_lamnar_lika_mycket_spar_som_ett_lyckat(tmp_path, monkeypatch):
    """Projektets egen regel. Utan svaret gar ett parsefel inte att undersoka -
    vi forlorade ett den 11 november for att omforsoket skrev over det."""
    _, _, _, rap = _kor(tmp_path, monkeypatch, {"pass1_obs002": (1,)})
    namn = {p.name for p in rap.glob("*")}
    assert "pass1_obs002.txt" in namn, "det lyckade svaret ska sta under sitt namn"
    spar = [n for n in namn if "obs002" in n and "MISSLYCKAT" in n]
    assert spar, f"det misslyckade forsoket saknar spar: {sorted(namn)}"
    assert "rond1" in spar[0], "rondnumret ska sta i namnet"
    assert "Note: the above" in (rap / spar[0]).read_text(encoding="utf-8")


def test_tva_fallna_ronder_for_samma_rad_tar_inte_varandra(tmp_path, monkeypatch):
    _, _, _, rap = _kor(tmp_path, monkeypatch, {"pass1_obs002": (1, 2)})
    spar = sorted(p.name for p in rap.glob("*MISSLYCKAT*") if "obs002" in p.name)
    assert len(spar) == 2, f"ett spar per fallen rond, fick {spar}"
