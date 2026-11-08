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
    # Sedan 2026-11-07 ligger sjalva anropen i kor_i_batch och kor_direkt.
    # Grinden ska sta fore bada, och ingen av dem far anropas nagon annanstans
    # ifran - annars kan ett dygn na API:et utan att ha passerat grinden.
    for utforare in ("kor_i_batch(", "kor_direkt("):
        assert utforare in src, f"{utforare} anropas inte ur run()"
        assert src.index("gate_dygnet_ar_oppet(day)") < src.index(utforare)
    for namn in ("kor_i_batch", "kor_direkt"):
        kallor = (ROT / "src").glob("*.py")
        for f in kallor:
            if f.name == "classify.py":
                continue
            assert f"{namn}(" not in f.read_text(encoding="utf-8"), (
                f"{namn} anropas fran {f.name}, utanfor grindens rackvidd")
