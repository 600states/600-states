"""Dygnets identitet far aldrig bli en strang som byggs pa flera stallen.

v3.1 skrev state_id som "2026-001" medan fryst protokoll sager "2026/001".
state_id ingar i observation_id-hashen, sa avvikelsen andrade varje ID i hela
verket. Detta test ar vakten mot att det hander igen.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import statepaths as sp

def test_state_id_foljer_fryst_protokoll():
    assert sp.state_id("20260101") == "2026/001"      # Observation Day Rule v1.0
    assert sp.state_id("20261201") == "2026/335"
    assert "-" not in sp.state_id("20260101")

def test_aret_ar_aldrig_hardkodat():
    assert sp.state_id("20270101") == "2027/001"
    assert sp.state_key("20270101") == "2027_001"

def test_skottar():
    assert sp.ordinal("20241231") == 366
    assert sp.ordinal("20261231") == 365

def test_ogiltigt_dygn_stoppas():
    for bad in ("2026-12-01", "20261", "", "abcdefgh", "20261301"):
        try:
            sp.state_id(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} borde ha avvisats")

def test_pilotkatalogerna_ror_vi_inte():
    """En efterhandskorning av 2 januari far inte skriva i STATE_002."""
    d = sp.outdir(Path("/DATA"), "20260102")
    assert d.name == "STATE_2026_002"

def test_alla_filnamn_bar_samma_nyckel():
    D = Path("/DATA")
    for f in (sp.pre_manifest, sp.emotion_manifest, sp.color_manifest,
              sp.near_duplicate, sp.selection_report, sp.png):
        assert "600_STATES_2026_335_" in f(D, "20261201").name
        assert sp.MANIFEST_VERSION in f(D, "20261201").name
