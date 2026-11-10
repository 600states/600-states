"""Acceptanstest for lasvagen: frozen() ska saga vilken form den laste.

Ett dygn fryst under v3.2 ska fortfarande ga att revidera under v3.3-kod. Men
en TYST substitution ar FYND 011:s form igen - posten sager inte vilken form
den laste, och lasaren far gissa. Och tva versioner av samma fil i ett dygn ar
ett fel, inte ett val: da har nagon kort om halva kedjan.

Skrivet av den andra parten an den som atgardade, enligt AGENTS.md. Testerna
provar beteende i en egen temporarkatalog och ror aldrig arkivet.
"""
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import statepaths as sp

DAG = "20261201"


def _katalog(tmp_path, *versioner):
    """Bygger ett dygn med pre-manifestet i de versioner som anges."""
    d = sp.outdir(tmp_path, DAG)
    d.mkdir(parents=True, exist_ok=True)
    for v in versioner:
        namn = sp.pre_manifest(tmp_path, DAG).name.replace(sp.V, v)
        (d / namn).write_text("state_id\n", encoding="utf-8")
    return sp.pre_manifest(tmp_path, DAG)


# ---- dygnets egen fil ----------------------------------------------------
def test_dygn_i_kodens_egen_version_lases_rakt_av(tmp_path, capsys):
    p = _katalog(tmp_path, sp.V)
    assert sp.frozen(p) == p
    assert "LASER ANNAN VERSION" not in capsys.readouterr().out


def test_ett_aldre_dygn_gar_fortfarande_att_lasa(tmp_path):
    p = _katalog(tmp_path, "v3.2")
    assert sp.frozen(p).name.endswith("_v3.2.csv")


def test_substitutionen_syns_i_utskriften(tmp_path, capsys):
    """En tyst substitution ar FYND 011:s form: posten sager inte vad den laste."""
    p = _katalog(tmp_path, "v3.2")
    sp.frozen(p)
    ut = capsys.readouterr().out
    assert "LASER ANNAN VERSION" in ut
    assert sp.V in ut and "v3.2" in ut          # bade det begarda och det lasta


# ---- tva versioner ar ett fel -------------------------------------------
def test_tva_versioner_stannar_i_stallet_for_att_valjas(tmp_path):
    p = _katalog(tmp_path, "v3.2", sp.V)
    with pytest.raises(ValueError) as e:
        sp.frozen(p)
    assert "v3.2" in str(e.value) and sp.V in str(e.value)   # bada namnda


def test_tva_versioner_stannar_aven_nar_den_begarda_finns(tmp_path):
    """Den forra versionen tog sorted()[-1] och gick vidare. Att den begarda
    filen rakar finnas gor inte katalogen entydig."""
    p = _katalog(tmp_path, sp.V, "v3.2")
    with pytest.raises(ValueError):
        sp.frozen(p)


def test_inget_dygn_alls_ar_filen_saknas(tmp_path):
    d = sp.outdir(tmp_path, DAG); d.mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError):
        sp.frozen(sp.pre_manifest(tmp_path, DAG))


# ---- rapporten bar formen -----------------------------------------------
def test_versionen_lases_ur_filnamnet_inte_ur_koden(tmp_path):
    p = _katalog(tmp_path, "v3.2")
    assert sp.version_of(sp.frozen(p)) == "v3.2" != sp.V


def test_versionen_av_dygnets_egen_fil_ar_kodens(tmp_path):
    p = _katalog(tmp_path, sp.V)
    assert sp.version_of(sp.frozen(p)) == sp.V


def test_ett_namn_utan_version_gissas_inte(tmp_path):
    assert sp.version_of(Path("nagot_utan_version.csv")) == "OKAND"


# ---- skrivvagen far aldrig fallbacken -----------------------------------
def test_produktionsstegen_skriver_aldrig_genom_frozen():
    """Strukturell grind, med avsikt: gar inte att observera utifran. Far
    lasvagens fallback styra skrivningen avgor arkivet vilken form som skrivs,
    och versionsnumret slutar betyda nagot."""
    for namn in ["run_state.py", "run_color.py", "consensus.py", "render.py"]:
        kalla = (ROT / "src" / namn).read_text(encoding="utf-8")
        assert "frozen(" not in kalla, f"{namn} skriver genom lasvagens fallback"
