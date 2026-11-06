"""En dag, en korning, ett utfall. Beslut 2026-11-06.

Lasningen fore frysningen ar inte unik (FYND 006). Den egenskapen ar bara
harlig sa lange korningen ar den forsta - annars blir "irreversible" ett
loftesord. Grinden maste kunna stoppa en korning, annars ar regeln ett
onskemal.
"""
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import pytest
import classify, consensus, gates, statepaths as sp


def _frys(tmp, day):
    """Lagg en sha256-sidecar som om dygnet redan blivit ett verk."""
    emo = sp.emotion_manifest(tmp, day)
    emo.parent.mkdir(parents=True, exist_ok=True)
    emo.write_text("tile_index,observation_id\n", encoding="utf-8")
    sp.sha_sidecar(emo).write_text("0" * 64 + f"  {emo.name}\n", encoding="utf-8")
    return emo


def test_klassificering_avvisas_nar_dygnet_ar_fryst(tmp_path):
    day = "20261201"
    _frys(tmp_path, day)
    with pytest.raises(gates.GateFailure) as e:
        classify.gate_dygnet_ar_oppet(day, data=tmp_path)
    assert "en dag, en korning, ett utfall" in str(e.value).lower()


def test_oppet_dygn_slapps_igenom(tmp_path):
    classify.gate_dygnet_ar_oppet("20261201", data=tmp_path)   # ingen sidecar


def test_frysningen_skriver_inte_over_en_frysning(tmp_path):
    day = "20261201"
    _frys(tmp_path, day)
    with pytest.raises(SystemExit) as e:
        consensus.build(day, tmp_path / "passar", data=tmp_path)
    assert "redan fryst" in str(e.value)


def test_grinden_star_fore_anropen():
    """Upptacks det forst efter trettio anrop ar pengarna redan utlagda.

    Textlage i filen sager ingenting - call() definieras langt fore run().
    Det som galler ar ordningen INNE i run()."""
    import inspect
    src = inspect.getsource(classify.run)
    assert "gate_dygnet_ar_oppet(day)" in src
    assert src.index("gate_dygnet_ar_oppet(day)") < src.index("call(")
