"""Acceptanstest for FYND 011: tidsstampeln ska overleva frysningen.

Beviset samlades in - fetch_one stamplade varje hamtning - och tappades i det
ogonblick som gor en post permanent. I den publicerade posten sag ett dygn
fangat samma dygn darfor identiskt ut som ett fangat tva veckor senare.

Testet ar skrivet av den andra parten an den som atgardade, enligt AGENTS.md.
Det provar BETEENDE, inte kallkod: varje pastaende har ska kunna falla om
funktionen andras, och inget har far ga gront for att ett ord finns i en fil.

  1. gransen for "under observationsdygnet" ligger pa UTC-dygnet, utan tolerans
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


def _rad(tid="2026-11-04T09:00:00+00:00", sha="a" * 64, i=1):
    return {"tile_index": i, "evidence_retrieved_at": tid, "content_sha256": sha,
            "evidence_basis": basis({"evidence_retrieved_at": tid,
                                     "content_sha256": sha}, DYGN)}


# ---- 1. gransen ----------------------------------------------------------
@pytest.mark.parametrize("tid,vantat", [
    ("2026-11-04T00:00:00+00:00", "OBSERVED_AT_CAPTURE"),   # forsta sekunden
    ("2026-11-04T23:59:59+00:00", "OBSERVED_AT_CAPTURE"),   # sista sekunden
    ("2026-11-05T00:00:00+00:00", "RETROSPECTIVE"),         # en sekund efter
    ("2026-11-03T23:59:59+00:00", "RETROSPECTIVE"),         # en sekund fore
    ("2026-11-05T00:30:00+01:00", "OBSERVED_AT_CAPTURE"),   # = 23:30 UTC den 4:e
    ("2026-11-04T23:30:00-01:00", "RETROSPECTIVE"),         # = 00:30 UTC den 5:e
])
def test_gransen_ligger_pa_utc_dygnet(tid, vantat):
    assert basis({"evidence_retrieved_at": tid, "content_sha256": "x"}, DYGN) == vantat


# ---- 2. ingen gissad tidszon --------------------------------------------
def test_stampel_utan_tidszon_avbryter():
    """astimezone() pa en naiv stampel tolkar den i maskinens lokala tid, och
    da beror bevisnivan pa var programmet kordes. Hellre stopp an ett svar som
    inte gar att reproducera."""
    with pytest.raises(ValueError):
        basis({"evidence_retrieved_at": "2026-11-04T12:00:00",
               "content_sha256": "x"}, DYGN)


# ---- 3. beviset ar sidan, inte forsoket ---------------------------------
def test_utan_hashad_sida_finns_inget_bevis_att_datera():
    snabbt = {"evidence_retrieved_at": "2026-11-04T00:00:01+00:00",
              "content_sha256": None}
    assert basis(snabbt, DYGN) == "NO_EVIDENCE"
    assert basis({"evidence_retrieved_at": None, "content_sha256": "x"}, DYGN) == "NO_EVIDENCE"


def test_alla_nivaer_basis_kan_returnera_star_i_specens_lista():
    for r in [{"evidence_retrieved_at": None, "content_sha256": None},
              {"evidence_retrieved_at": "2026-11-04T09:00:00+00:00", "content_sha256": "x"},
              {"evidence_retrieved_at": "2026-11-09T09:00:00+00:00", "content_sha256": "x"}]:
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
