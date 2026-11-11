"""Acceptanstest for FYND 011: tidsstampeln ska overleva frysningen.

Beviset samlades in - fetch_one stamplade varje hamtning - och tappades i det
ogonblick som gor en post permanent. I den publicerade posten sag ett dygn
fangat samma dygn darfor identiskt ut som ett fangat tva veckor senare.

Testet ar skrivet av den andra parten an den som atgardade, enligt AGENTS.md.
Det provar BETEENDE, inte kallkod: varje pastaende har ska kunna falla om
funktionen andras, och inget har far ga gront for att ett ord finns i en fil.

  1. fonstret har TVA sidor: efter first mention, senast 24:00 UTC + 3h
  2. en stampel utan tidszon avbryter i stallet for att gissa maskinens zon
  3. beviset ar den hashade sidan, inte forsoket
  4. grinden faller pa en rad som saknar tid eller niva
  5. GRINDEN GAR FORE SKRIVNINGEN - ett avvisat dygn lamnar ingen fil
"""
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import gates
import pool_evidence
from pool_evidence import BEVISNIVAER, basis

DYGN = "20261104"


def _rad(tid="2026-11-05T00:20:00+00:00", sha="a" * 64, i=1):
    c = {"tile_index": i, "evidence_retrieved_at": tid, "content_sha256": sha,
         "first_mention_utc": "20261104090000"}
    c["evidence_basis"] = basis(c, DYGN)
    return c


# ---- 1. fonstret har tva sidor ------------------------------------------
# Observationsdygnet 20261104 stanger 2026-11-05T00:00Z. Ovre gransen ar da
# 03:00Z den 5:e, inklusive. Undre gransen ar first mention, strikt.
FM = "20261104090000"          # first mention 09:00Z den 4:e


@pytest.mark.parametrize("tid,vantat", [
    ("2026-11-04T09:00:01+00:00", "CAPTURED_IN_WINDOW"),   # en sekund efter first mention
    ("2026-11-04T23:59:59+00:00", "CAPTURED_IN_WINDOW"),   # under dygnet
    ("2026-11-05T00:30:00+00:00", "CAPTURED_IN_WINDOW"),   # avsedd korning, 00:05-00:30
    ("2026-11-05T03:00:00+00:00", "CAPTURED_IN_WINDOW"),   # sista sekunden i fonstret
    ("2026-11-05T03:00:01+00:00", "RETROSPECTIVE"),        # en sekund for sent
    ("2026-11-04T09:00:00+00:00", "RETROSPECTIVE"),        # exakt first mention: inte efter
    ("2026-11-04T08:59:59+00:00", "RETROSPECTIVE"),        # fore historien fanns
    ("2026-11-05T04:00:00+01:00", "CAPTURED_IN_WINDOW"),   # = 03:00Z, offset raknas om
])
def test_fonstrets_bada_granser(tid, vantat):
    assert basis({"evidence_retrieved_at": tid, "content_sha256": "x",
                  "first_mention_utc": FM}, DYGN) == vantat


def test_midnatt_ar_inte_langre_en_grans():
    """Den forra regeln lade en klippkant vid 24:00 som inte betydde nagonting:
    00:30 dygnet efter ar metodologiskt identisk med 23:50. Bada ar nu starka."""
    for tid in ("2026-11-04T23:50:00+00:00", "2026-11-05T00:30:00+00:00"):
        assert basis({"evidence_retrieved_at": tid, "content_sha256": "x",
                      "first_mention_utc": FM}, DYGN) == "CAPTURED_IN_WINDOW"


def test_fonstret_foljer_parametern_inte_ett_tal_i_koden():
    """Ett ställe, inte tva. Flyttas FONSTER_TIMMAR ska gransen folja med."""
    sent = {"evidence_retrieved_at": "2026-11-05T02:00:00+00:00",
            "content_sha256": "x", "first_mention_utc": FM}
    assert basis(sent, DYGN) == "CAPTURED_IN_WINDOW"
    gammalt = pool_evidence.FONSTER_TIMMAR
    try:
        pool_evidence.FONSTER_TIMMAR = 1
        assert basis(sent, DYGN) == "RETROSPECTIVE"
    finally:
        pool_evidence.FONSTER_TIMMAR = gammalt
    assert basis(sent, DYGN) == "CAPTURED_IN_WINDOW"


def test_utan_first_mention_nedgraderas_aldrig_uppgraderas():
    """Felriktningen gar alltid mot det svagare pastaendet. Att faltet finns
    vaktas av gate_candidates, fore urvalet."""
    assert basis({"evidence_retrieved_at": "2026-11-05T00:30:00+00:00",
                  "content_sha256": "x"}, DYGN) == "RETROSPECTIVE"


# ---- 2. ingen gissad tidszon --------------------------------------------
def test_stampel_utan_tidszon_avbryter():
    """astimezone() pa en naiv stampel tolkar den i maskinens lokala tid, och
    da beror bevisnivan pa var programmet kordes. Hellre stopp an ett svar som
    inte gar att reproducera."""
    with pytest.raises(ValueError):
        basis({"evidence_retrieved_at": "2026-11-04T12:00:00",
               "content_sha256": "x", "first_mention_utc": "20261104090000"}, DYGN)


# ---- 3. beviset ar sidan, inte forsoket ---------------------------------
def test_utan_hashad_sida_finns_inget_bevis_att_datera():
    snabbt = {"evidence_retrieved_at": "2026-11-05T00:20:00+00:00",
              "content_sha256": None, "first_mention_utc": "20261104090000"}
    assert basis(snabbt, DYGN) == "NO_EVIDENCE"
    assert basis({"evidence_retrieved_at": None, "content_sha256": "x",
                  "first_mention_utc": "20261104090000"}, DYGN) == "NO_EVIDENCE"


def test_alla_nivaer_basis_kan_returnera_star_i_specens_lista():
    for r in [{"evidence_retrieved_at": None, "content_sha256": None},
              {"evidence_retrieved_at": "2026-11-05T00:20:00+00:00", "content_sha256": "x",
               "first_mention_utc": "20261104090000"},
              {"evidence_retrieved_at": "2026-11-09T09:00:00+00:00", "content_sha256": "x",
               "first_mention_utc": "20261104090000"}]:
        assert basis(r, DYGN) in BEVISNIVAER


# ---- 4. grinden faller --------------------------------------------------
def test_grinden_slapper_igenom_ett_komplett_dygn():
    gates.gate_evidence_time([_rad(i=i) for i in range(3)], BEVISNIVAER)


def test_grinden_faller_pa_rad_utan_tidsstampel():
    rader = [_rad(i=0), _rad(i=1)]
    rader[1]["evidence_retrieved_at"] = None
    with pytest.raises(gates.GateFailure):
        gates.gate_evidence_time(rader, BEVISNIVAER)


def test_grinden_faller_pa_rad_utan_bevisniva():
    rader = [_rad(i=0), _rad(i=1)]
    del rader[1]["evidence_basis"]
    with pytest.raises(gates.GateFailure):
        gates.gate_evidence_time(rader, BEVISNIVAER)


def test_grinden_faller_pa_niva_utanfor_specen():
    rader = [_rad(i=0)]
    rader[0]["evidence_basis"] = "OBSERVED_AT_CAPTURE_PROBABLY"
    with pytest.raises(gates.GateFailure):
        gates.gate_evidence_time(rader, BEVISNIVAER)


def test_grinden_har_ingen_egen_vokabular():
    """Nivalistan kommer fran den som satter faltet. En egen kopia i gates.py
    ar hur FYND 003 uppstod - tva definitioner av samma sak som glider isar."""
    with pytest.raises(gates.GateFailure):
        gates.gate_evidence_time([_rad()], ("NAGOT_ANNAT",))


# ---- 5. grinden gar fore skrivningen ------------------------------------
def test_ett_avvisat_dygn_lamnar_ingen_fil(tmp_path):
    """En grind som faller efter skrivningen skyddar ingenting: filen finns
    redan nar felet kommer. Provas genom att lata grinden falla och se att
    ingen fil kan ha hunnit skapas i arbetsmappen."""
    rader = [_rad(i=0), _rad(i=1)]
    rader[1]["evidence_retrieved_at"] = None
    with pytest.raises(gates.GateFailure):
        gates.gate_evidence_time(rader, BEVISNIVAER)
        (tmp_path / "manifest.csv").write_text("skrivet", encoding="utf-8")
    assert not list(tmp_path.iterdir())


def test_grinden_anropas_innan_manifestet_skrivs():
    """Ordningen i run_state.step_select ar det som avgor, inte ordningen i
    dokumentationen. Faller om nagon flyttar skrivningen fore grinden."""
    kalla = (ROT / "src" / "run_state.py").read_text(encoding="utf-8")
    kropp = kalla[kalla.index("def step_select"):]
    kropp = kropp[:kropp.index("\ndef ")]
    assert kropp.index("gate_evidence_time") < kropp.index("atomic_write")


# ---- pilotvagen ror vi inte ---------------------------------------------
def test_pilotvagens_basis_kan_inte_na_den_nya_nivan():
    """capture_state.basis() hor till pilotserien och ska inte kompletteras.
    Nar tva funktioner heter samma sak kompletterar nasta lasare fel en."""
    import capture_state
    rec = {"http_status": 200, "archive_url": None, "archive_timestamp": None}
    assert capture_state.basis(rec, DYGN) != "OBSERVED_AT_CAPTURE"
