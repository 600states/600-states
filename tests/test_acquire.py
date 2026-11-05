"""Forvarvssteget. Dygnets 96 slots ar harledda, inte hamtade."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import acquire

def test_exakt_96_slots_per_dygn():
    s = acquire.slots("20261201")
    assert len(s) == acquire.SLOTS == 96
    assert s[0] == "20261201000000" and s[-1] == "20261201234500"

def test_slots_ar_kvartar_och_ligger_i_dygnet():
    s = acquire.slots("20260101")
    assert all(x.startswith("20260101") for x in s)
    assert sorted({x[10:12] for x in s}) == ["00", "15", "30", "45"]
    assert len(set(s)) == 96

def test_slots_laser_inte_klockan():
    """Samma dygn ger samma lista oavsett nar den begars."""
    assert acquire.slots("20240229") == acquire.slots("20240229")
    assert acquire.slots("20240229")[0] == "20240229000000"

def test_url_byggs_av_stampeln():
    assert acquire.mentions_url("20261201061500").endswith("/20261201061500.mentions.CSV.zip")
    assert acquire.events_url("20261201").endswith("/20261201.export.CSV.zip")

def test_ogiltigt_dygn_stoppas():
    import statepaths as sp
    for bad in ("2026-12-01", "20261", ""):
        try:
            sp.state_id(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} borde ha avvisats")
