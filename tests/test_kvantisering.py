"""Kvantiseringsforbudet ska kunna falla en korning, inte bara sta i specen.

Specen satter intensity_confidence_template_quantization_prohibited och
prompten sager det i klartext. Till 2026-11-06 provade ingenting det, och en
regel som inte kan stoppa en korning ar ett onskemal.
"""
import importlib.util, sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src")); sys.path.insert(0, str(ROT))
_s = importlib.util.spec_from_file_location("cal", ROT / "tools" / "calibrate.py")
cal = importlib.util.module_from_spec(_s); _s.loader.exec_module(cal)


def test_rutnatsvarden_faller():
    """Haikus uppmatta beteende: vartenda varde pa 0,05-rutnatet."""
    v = [0.55, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90] * 10
    assert cal.kvantiserad(v, 2) is not None


def test_full_upplosning_slipper_igenom():
    """Opus uppmatta beteende: andra decimalen anvands."""
    v = [0.74, 0.68, 0.76, 0.73, 0.52, 0.47, 0.33, 0.61, 0.58, 0.42] * 3
    assert cal.kvantiserad(v, 2) is None


def test_ett_enda_varde_utanfor_rutnatet_racker():
    """Mattet ar 'nagot alls', inte 'hur manga' - ingen troskel att valja."""
    v = [0.50] * 49 + [0.47]
    assert cal.kvantiserad(v, 2) is None


def test_for_fa_varden_ger_inget_utslag():
    assert cal.kvantiserad([0.5, 0.6], 2) is None


def test_grinden_laser_specens_flagga():
    """Star forbudet inte i specen provas det inte."""
    P = [{"a": {"scores": {}, "intensity": 0.5, "confidence": 0.8}} for _ in range(3)] * 10
    utan = cal.grind_ur_spec(P, {}, [])
    assert utan[0] is True
