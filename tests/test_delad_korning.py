"""Acceptanstest for den delade korningen.

Skrivet av den andra parten an den som implementerade 5905bce, enligt
AGENTS.md.

Events-dagsfilen publiceras timmar efter att dygnet stangde - uppmatt
2026-11-21: 404 till 07:45 UTC, forsta 200 kl. 08:00, stampel 07:00.
Bevisfonstret stanger 03:00. Sa lange nagot i korning A ror Events kan kedjan
aldrig fanga ett bevis inom fonstret, och varje dygn i serien blir UNQUALIFIED.

Tre pastaenden provas:

1. KORNING A ROR INTE EVENTS. Det ar hela delningen. Smyger ett anrop tillbaka
   in i build() ar fonstret stangt igen, och ingenting i en korning sager
   ifran - dygnet blir bara tyst okvalificerat, varje natt.

2. REGIONRAKNINGEN AR DETERMINISTISK. Fore 5905bce raknades lander medan
   event_ids var en set: 198 oavgjorda av 3 786, och tva processer gav olika
   land for 111 dokument. Regionen styr kvoterna, sa hashseeden avgjorde vilka
   600 som valdes. Det provas har genom att kora samma anrop under flera
   PYTHONHASHSEED och krava identiskt utfall.

3. KORNING B VANTAR IN FILEN, FALLER INTE PA DEN. Filen blev atkomlig en timme
   efter sin egen tidsstampel. En korning som fragar en gang och ger upp hade
   misslyckats den natten.
"""
import ast
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import acquire
import candidates
import run_state


def _funktion(fil, namn):
    for nod in ast.walk(ast.parse(Path(fil).read_text(encoding="utf-8"))):
        if isinstance(nod, ast.FunctionDef) and nod.name == namn:
            return nod
    raise AssertionError(f"{namn} finns inte i {Path(fil).name}")


def _anropade_namn(nod):
    ut = set()
    for n in ast.walk(nod):
        if isinstance(n, ast.Call):
            f = n.func
            ut.add(f.id if isinstance(f, ast.Name)
                   else f.attr if isinstance(f, ast.Attribute) else "")
    return ut


# ---- 1. korning A ror inte Events ---------------------------------------
def test_stegen_star_i_ratt_ordning():
    assert run_state.STAGES == ["candidates", "pool", "regioner",
                                "select", "input", "emotion"]


def test_regioner_ligger_efter_bevisfangsten():
    """BEVISFANGSTEN MASTE LIGGA FORE REGIONERNA.

    Flyttas regioner fore pool hamtas bevisen forst efter att Events kommit,
    alltsa efter 08:00, och fonstret stangde 03:00. Hela delningen ar den har
    ordningen."""
    s = run_state.STAGES
    assert s.index("pool") < s.index("regioner") < s.index("select")


def test_kandidatbygget_ror_inte_events():
    """build() far inte lasa Events-filen. Gor den det kan ingenting goras
    fore morgonen, och bevisen hamnar utanfor fonstret varje natt."""
    kalla = ROT / "src" / "candidates.py"
    assert "load_events" not in _anropade_namn(_funktion(kalla, "build")), (
        "candidates.build() anropar load_events igen - korning A ror da Events "
        "och bevisen kan inte fangas innan fonstret stanger")


def test_regionsteget_ar_det_som_laser_events():
    kalla = ROT / "src" / "candidates.py"
    assert "load_events" in _anropade_namn(_funktion(kalla, "regioner"))


def test_kandidaterna_bar_inga_regionfalt():
    """Nycklarna ska inte finnas alls efter build. En tom strang ser ut som ett
    svar; en saknad nyckel ar en fraga som inte stallts an - och run_state
    skiljer pa dem med felkod 5."""
    kalla = (ROT / "src" / "candidates.py").read_text(encoding="utf-8")
    kropp = ast.get_source_segment(kalla, _funktion(ROT / "src" / "candidates.py", "build"))
    for falt in ("action_geo_country", "review_region"):
        assert falt not in kropp, f"build() satter {falt}"


# ---- 2. determinismen ----------------------------------------------------
SKRIPT = textwrap.dedent('''
    import json, sys
    sys.path.insert(0, %r)
    import candidates
    # Ett oavgjort fall: lika manga handelser i SE som i PL, och event_ids
    # sorterade som build() lamnar dem.
    geo = {"1": "SE", "2": "PL", "3": "SE", "4": "PL"}
    candidates.load_events = lambda day: geo
    docs = [{"event_ids": ["1", "2", "3", "4"]},
            {"event_ids": ["4", "3", "2", "1"]},
            {"event_ids": ["2", "4"]},
            {"event_ids": []},
            {"event_ids": ["1", "3", "2"]}]
    candidates.regioner(docs, "20261111")
    print(json.dumps([d["action_geo_country"] for d in docs]))
''')


def _kor_under_hashseed(seed):
    ut = subprocess.run([sys.executable, "-c", SKRIPT % str(ROT / "src")],
                        capture_output=True, text=True,
                        env={**os.environ, "PYTHONHASHSEED": str(seed)})
    assert ut.returncode == 0, ut.stderr
    return json.loads(ut.stdout.strip().splitlines()[-1])


def test_regionerna_beror_inte_av_hashseeden():
    """REGRESSIONEN FRAN 5905bce.

    Fore den raknades lander medan event_ids var en set, och tva processer gav
    olika land for 111 av 3 786 dokument pa samma snapshot. Regionen styr
    regionkvoterna, sa seeden avgjorde vilka 600 observationer som blev verket.

    Korningen gors i egna processer: PYTHONHASHSEED lases vid tolkstart och gar
    inte att satta i efterhand."""
    utfall = [_kor_under_hashseed(s) for s in (0, 1, 7, 42, 12345)]
    assert len(set(map(tuple, utfall))) == 1, (
        f"regionerna varierar med PYTHONHASHSEED: {utfall}")


def test_oavgjort_bryts_likadant_oavsett_dokumentets_ordning():
    """Samma handelser i omvand ordning i event_ids ska ge samma land. Gor de
    inte det beror utfallet pa nagot annat an innehallet."""
    utfall = _kor_under_hashseed(0)
    assert utfall[0] == utfall[1], (
        f"samma handelser i omvand ordning gav {utfall[0]} och {utfall[1]}")
    assert utfall[3] == "", "ett dokument utan handelser ska ha tomt land"


def test_oavgjort_vinns_av_lagsta_landskoden():
    """REGELN, inte bara dess determinism.

    Mitt forsta test provade bara att utfallet ar order-oberoende. Bade lagsta
    och hogsta landskod ar order-oberoende, sa en andring fran min till max hade
    passerat - och den flyttar landet pa ungefar hundra dokument per dygn
    (uppmatt 101 av 3 786 pa 20261111, 82 av 4 245 pa 20261104).

    SE och PL star lika i dokument 0. PL ar lagre alfabetiskt och ska vinna."""
    utfall = _kor_under_hashseed(0)
    assert utfall[0] == "PL", (
        f"oavgjort mellan PL och SE ska ge PL, fick {utfall[0]}")


def test_en_majoritet_slar_landskoden():
    """Landskoden bryter LIKA. Den far aldrig sla en majoritet - da vore det
    inte en skiljeregel utan en sortering."""
    utfall = _kor_under_hashseed(0)
    assert utfall[4] == "SE", (
        f"SE har tva mot PL:s en och ska vinna trots att PL sorterar forst, "
        f"fick {utfall[4]}")


def test_event_ids_lamnas_sorterade_av_bygget():
    """Mekanismen bakom determinismen. Blir event_ids en set igen bryts
    oavgjorda fall av mangdens iterationsordning, och det ar exakt felet."""
    kalla = ROT / "src" / "candidates.py"
    kropp = ast.get_source_segment((kalla).read_text(encoding="utf-8"),
                                   _funktion(kalla, "build"))
    assert "sorted(d[\"event_ids\"])" in kropp or "sorted(d['event_ids'])" in kropp, (
        "build() sorterar inte langre event_ids - oavgjorda landrakningar "
        "avgors da av iterationsordningen, vilket var felet i 5905bce")


# ---- 3. vantan pa Events -------------------------------------------------
class _Klocka:
    def __init__(self): self.t = 0.0
    def monotonic(self): return self.t
    def sleep(self, s): self.t += s


@pytest.fixture
def stängd_klocka(monkeypatch):
    k = _Klocka()
    monkeypatch.setattr(acquire.time, "monotonic", k.monotonic)
    monkeypatch.setattr(acquire.time, "sleep", k.sleep)
    return k


def test_utan_vanta_gors_ett_enda_forsok(monkeypatch, stängd_klocka):
    n = []
    monkeypatch.setattr(acquire, "fetch", lambda u: (n.append(1), (None, "404"))[1])
    data, sista404, fel = acquire.hamta_events("20261120", vanta=False)
    assert (data, sista404) == (None, None)
    assert fel == "404"
    assert len(n) == 1


def test_antalet_forsok_foljer_taket_och_intervallet(monkeypatch, stängd_klocka):
    """Konstanterna ska lasas, inte vara tal i en slinga. Flyttas de ska
    antalet forsok folja med."""
    monkeypatch.setattr(acquire, "EVENTS_TAK_S", 1800)        # 30 min
    monkeypatch.setattr(acquire, "EVENTS_INTERVALL_S", 300)   # 5 min
    n = []
    monkeypatch.setattr(acquire, "fetch", lambda u: (n.append(1), (None, "404"))[1])
    data, sista404, fel = acquire.hamta_events("20261120", vanta=True)
    assert data is None
    assert len(n) == 7, f"30 min / 5 min + 1 = 7 forsok, fick {len(n)}"
    assert sista404 is not None


def test_ett_kortare_intervall_ger_fler_forsok(monkeypatch, stängd_klocka):
    monkeypatch.setattr(acquire, "EVENTS_TAK_S", 1800)
    monkeypatch.setattr(acquire, "EVENTS_INTERVALL_S", 60)
    n = []
    monkeypatch.setattr(acquire, "fetch", lambda u: (n.append(1), (None, "404"))[1])
    acquire.hamta_events("20261120", vanta=True)
    assert len(n) == 31, f"30 min / 1 min + 1 = 31 forsok, fick {len(n)}"


def test_filen_som_dyker_upp_ger_sista_404_tiden(monkeypatch, stängd_klocka):
    """sista_404_utc och events_frozen_at_utc bracketar nar filen blev
    atkomlig. Det ar sa nara en matning av publiceringstiden vi kommer
    utifran, och den 21 november skilde de en timme."""
    svar = [(None, "404"), (None, "404"), (b"zipdata", None)]
    monkeypatch.setattr(acquire, "fetch", lambda u: svar.pop(0))
    data, sista404, fel = acquire.hamta_events("20261120", vanta=True)
    assert data == b"zipdata"
    assert fel is None
    assert sista404 is not None, "sista 404-tiden ska finnas kvar efter traffen"


def test_en_traff_sover_inte(monkeypatch, stängd_klocka):
    monkeypatch.setattr(acquire, "fetch", lambda u: (b"zip", None))
    acquire.hamta_events("20261120", vanta=True)
    assert stängd_klocka.t == 0, "en traff pa forsta forsoket ska inte sova"


# ---- somen i snapshotet --------------------------------------------------
def test_de_tre_statusvardena_ar_skilda():
    kalla = (ROT / "src" / "acquire.py").read_text(encoding="utf-8")
    for s in ("MENTIONS_FROZEN", "COMPLETE", "INCOMPLETE_SOURCE"):
        assert s in kalla, f"statusvardet {s} finns inte i acquire.py"
