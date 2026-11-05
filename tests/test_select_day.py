"""Kvotmotorn. Den avgor vilka 600 observationer som blir verket.

Testet anvander syntetiska kandidater: vi provar reglerna, inte ett dygn.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import select_day
from select_day import select, REGIONS, PER_REGION, PUBLISHER_CAP, N_TOTAL

def make(n_per_region=130, n_domains=120):
    """Lexikaliskt helt distinkta kandidater: storytaket ska inte sla ihop nagot.

    Delar titlarna ord slar taket ihop dem och urvalet kollapsar - det ar taket
    som gor sitt jobb, inte ett fel i kvotmotorn."""
    cands = []
    k = 0
    for ri, reg in enumerate(REGIONS):
        for j in range(n_per_region):
            k += 1
            cands.append({
                "url": f"https://pub{k % n_domains}.example/qaz{k}/wsx{k*3}-edc{k*7}",
                "domain": f"pub{k % n_domains}.example",
                "source_tier": "A" if k % 3 else "B",
                "review_region": reg,
                "mention_rows": 300 - (j % 300),
                "first_mention_utc": f"202612010{k % 8}{k % 60:02d}{k % 60:02d}",
                "page_title": f"qaz{k} wsx{k*3} edc{k*7} rfv{k*11} tgb{k*13}",
            })
    return cands

CH, REP, _ = select(make(), "2026/335")

def test_exakt_600():
    assert len(CH) == N_TOTAL == 600

def test_regionkvoter_uppfyllda():
    for reg in REGIONS:
        assert REP["regional_per_region"][reg] == PER_REGION == 30

def test_lagren_summerar():
    assert REP["per_layer"] == {"GLOBAL": 300, "REGIONAL": 240, "DISCOVERY": 60}

def test_publisher_cap_halls():
    assert REP["max_per_publicist"] <= PUBLISHER_CAP

def test_unika_url_och_id():
    assert REP["unika_urler"] == 600 and REP["unika_observation_id"] == 600

def test_rutnatet_ar_kronologiskt_och_fullt():
    idx = [c["tile_index"] for c in CH]
    assert idx == list(range(1, 601))
    ts = [c["first_mention_utc"] for c in CH]
    assert ts == sorted(ts)
    for c in CH:
        i = c["tile_index"] - 1
        assert c["grid_row"] == i // 30 + 1 and c["grid_column"] == i % 30 + 1
        assert 1 <= c["grid_column"] <= 30 and 1 <= c["grid_row"] <= 20

def test_state_id_skrivs_in_rakt_av():
    assert {c["state_id"] for c in CH} == {"2026/335"}

def test_observation_id_beror_pa_state_id():
    """state_id ingar i hashen - byter formatet byter varje ID. Se FYND om v3.1."""
    a, _, _ = select(make(), "2026/335")
    b, _, _ = select(make(), "2026-335")
    assert {c["observation_id"] for c in a} != {c["observation_id"] for c in b}

def test_deterministiskt():
    a, _, _ = select(make(), "2026/335")
    b, _, _ = select(make(), "2026/335")
    assert [c["observation_id"] for c in a] == [c["observation_id"] for c in b]
