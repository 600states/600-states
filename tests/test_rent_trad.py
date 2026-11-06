"""Uppladdningsmappen far inte innehalla ett smutsigt bygge.

Felet, 2026-11-06: bygget kordes fore commiten, stampeln blev
"9a1f3ba-dirty", och filerna lag kvar i dist redo att laddas upp. En sida
som pastar sig byggd ur ingen kand commit hor inte hemma pa en sajt vars
hela tes ar sparbarhet.

Ratt ordning ar committa, bygg, ladda upp. Testet finns for att visa att
grinden KAN falla - en regel som inte kan stoppa en korning ar ett onskemal.
"""
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT / "site"))
import pytest
import build

DIST = (ROT / "site" / "dist")


def test_smutsigt_trad_stoppar_bygget_till_dist():
    with pytest.raises(SystemExit) as e:
        build.gate_rent_trad(DIST, "9a1f3ba-dirty")
    assert "smutsigt trad" in str(e.value)
    assert "Committa forst" in str(e.value)


def test_rent_trad_slapps_igenom(tmp_path):
    build.gate_rent_trad(DIST, "53cf395")
    build.gate_rent_trad(tmp_path, "53cf395")


def test_smutsigt_trad_till_annan_mapp_ar_tillatet(tmp_path, capsys):
    """Forhandsgranskning ska ga, men aldrig till uppladdningsmappen."""
    build.gate_rent_trad(tmp_path, "9a1f3ba-dirty")
    assert "ska inte laddas upp" in capsys.readouterr().out


def test_grinden_star_fore_filskrivningen():
    """Upptacks det efter att dist skrivits ligger filerna redan dar."""
    import inspect
    src = inspect.getsource(build.main)
    assert "gate_rent_trad(out, stamp)" in src
    assert src.index("gate_rent_trad") < src.index("io.open(out /")
