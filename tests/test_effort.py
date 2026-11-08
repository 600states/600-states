"""Effort ar utskriven, och den far aldrig hamna over taket.

"disabled" och "between_tools" accepteras bara vid effort high eller lagre. Hojs
ett varde har till xhigh eller max svarar API:et 400 - inte vid nasta andring av
koden, utan vid nasta korning, mitt i serien. Testet ar billigare an det felet.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import classify

TAK = {"low", "medium", "high"}   # xhigh och max stanger av avstangningen


def test_varje_modell_med_avstangt_tankande_ligger_under_taket():
    for m, tank in classify.TANKANDE.items():
        if tank.get("type") in ("disabled", "between_tools"):
            assert classify.effort_for(m) in TAK, (
                f"{m} kor {tank['type']} pa effort {classify.effort_for(m)}; "
                "API:et svarar 400 vid xhigh eller max")


def test_okand_modell_hojer_inte_tyst():
    assert classify.effort_for("claude-finns-inte") in TAK


def test_opus_5_5_star_inte_i_tabellen():
    """Den accepterar bara adaptive - tankandet gar inte att stanga av, och
    beslutet 2026-11-05 ar att det ska vara avstangt."""
    assert "claude-opus-5-5" not in classify.TANKANDE


def test_effort_skrivs_i_korjournalen():
    src = (Path(__file__).resolve().parent.parent / "src" / "classify.py").read_text(encoding="utf-8")
    assert '"effort": effort_for(model)' in src
    # Anropets parametrar byggs pa ETT stalle sedan batchvagen kom till, sa att
    # direktvagen och Batch API inte kan bli tva olika instrument. Effort ska
    # ligga dar, inte pa ett anropsstalle.
    assert '"output_config": {"effort": effort_for(model)}' in src
    assert "def anropsparametrar(" in src
