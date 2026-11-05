"""Storytaket ar dar en verklig handelse kan raderas utan spar. Det ska testas.

BESLUT 2026-09-07: N=1, troskel 0,25, band 0,20-0,25 loggas.
Konstanterna ar bevisvarde, inte stallskruvar - andras de sager testet ifran.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from story_cap import apply_cap, near_duplicates, tokens, DEFAULT_N, DEFAULT_THRESHOLD, NEAR_DUPLICATE_BAND

def row(i, text): return {"i": i, "t": text, "ts": f"2026010100{i:04d}"}
TEXT = lambda r: r["t"]
TIME = lambda r: r["ts"]

def test_frysta_konstanter():
    assert (DEFAULT_N, DEFAULT_THRESHOLD) == (1, 0.25)
    assert NEAR_DUPLICATE_BAND == (0.20, 0.25)

def test_identisk_text_slapps_in_en_gang():
    rows = [row(1, "flood destroys bridge in valencia"),
            row(2, "flood destroys bridge in valencia")]
    kept, dropped = apply_cap(rows, TEXT, TIME)
    assert len(kept) == 1 and len(dropped) == 1
    assert kept[0]["i"] == 1          # kronologiskt forst vinner

def test_olika_handelser_behalls_bada():
    rows = [row(1, "flood destroys bridge in valencia"),
            row(2, "central bank raises interest rate in brasilia")]
    kept, _ = apply_cap(rows, TEXT, TIME)
    assert len(kept) == 2

def test_ingen_transitiv_kedjning():
    """A liknar B, B liknar C, men A liknar inte C. C ska slappas in.

    Forsta implementationen kedjade ihop kluster pa 265 orelaterade nyheter.
    Jamforelsen sker alltid mot en faktiskt inslappt rad, aldrig transitivt."""
    rows = [row(1, "alpha beta gamma delta epsilon"),
            row(2, "beta gamma delta epsilon zeta"),      # lik 1 -> ska falla
            row(3, "zeta eta theta iota kappa")]          # olik 1 -> ska in
    kept, dropped = apply_cap(rows, TEXT, TIME)
    kvar = {r["i"] for r in kept}
    assert 1 in kvar and 3 in kvar and 2 not in kvar

def test_deterministiskt():
    rows = [row(i, f"handelse nummer {i} i staden {i*7}") for i in range(1, 60)]
    a, _ = apply_cap(rows, TEXT, TIME)
    b, _ = apply_cap(list(reversed(rows)), TEXT, TIME)
    assert [r["i"] for r in a] == [r["i"] for r in b]     # sorteras pa tid, inte indataordning

def test_gransband_loggas_men_tas_inte_bort():
    rows = [row(1, "alpha beta gamma delta epsilon zeta eta theta"),
            row(2, "alpha beta iota kappa lambda mu nu xi omicron")]
    kept, _ = apply_cap(rows, TEXT, TIME)
    nd = near_duplicates(kept, TEXT)
    lo, hi = NEAR_DUPLICATE_BAND
    for p in nd:
        assert lo <= p["jaccard"] < hi

def test_stoppord_raknas_inte():
    assert "the" not in tokens("the flood and the bridge")
    assert {"flood", "bridge"} <= tokens("the flood and the bridge")
