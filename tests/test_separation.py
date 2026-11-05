"""Separationen ar en regel, och en regel som inte kan stoppa en korning ar
ingen regel.

Observation Day Rule: fargmodell v0.4 ar otillganglig tills 600-observations-
manifestet ar fryst. Darfor ar urval/klassificering och farg/rendering tva
program som inte importerar varandra. Tidigare drog run_state.py in
color_protocol direkt och korde farg och rendering som steg 6 och 7 i samma
process som urvalet.

Testet importerar varje program i en egen tolkprocess och ser efter vad som
faktiskt hamnade i sys.modules.
"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def dras_in(modul, kandidater):
    code = (f"import sys; sys.path.insert(0,{str(ROOT/'src')!r}); sys.path.insert(0,{str(ROOT)!r});"
            f"import {modul}; print(','.join(m for m in {kandidater!r} if m in sys.modules))")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    return [m for m in r.stdout.strip().split(",") if m]

FARG = ["color_protocol", "render", "run_color"]
URVAL = ["candidates", "select_day", "story_cap", "ranking", "consensus", "run_state"]

def test_urvalsprogrammet_nar_inte_fargen():
    assert dras_in("run_state", FARG) == []

def test_klassificeringen_nar_inte_fargen():
    assert dras_in("consensus", FARG) == []

def test_fargprogrammet_nar_inte_urvalet():
    assert dras_in("run_color", URVAL) == []

def test_grindarna_ar_fargfria():
    assert dras_in("gates", FARG) == []
