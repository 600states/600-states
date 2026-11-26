"""Grind: matpunkt 11, och den DATUMGRANS som skiljer den fran de tio andra.

Bakgrunden ar en matning och inte en farhaga. Den 26 november 2026 lastes
NAS:ens .env inifran en container med kedjans egen image, anvandare och
monteringar: raden ANTHROPIC_API_KEY fanns, och vardet var TOMT. Kedjan hade
alltsa inte kunnat klassificera ett enda dygn - och ingen rapport hade sagt
ifran pa fyra natter, eftersom korning B slutar vid emotionsgrinden med rc 3
och aldrig nar classify.py. Nyckeln kunde ha varit tom sedan 11 november utan
att nagon markt det.

Matpunkt 11 ar svaret. Men den ar den ENDA av de elva som provas mot sitt
VARDE, och det gor den till ett eget fall: de tio andra faller bara nar faltet
saknas, och 1.17 forbjuder malvarden pa dem.

DARFOR PROVAS GRANSEN HAR, inte bara att grinden kan falla:

    falt saknas            -> faller ALLTID, oavsett dygn
    falt false, fore start -> gar igenom. Ett missat observationsfonster ar
                              oaterkalleligt; en tom nyckel ar det inte
    falt false, fran start -> faller
    falt true              -> gar igenom

SKALET TILL ATT GRANSEN TAL ETT EGET PROV: gate_matpost ligger FORE
atomic_write(pre), alltsa fore den fil som gor dygnet permanent. En grind som
foll pa false aven fore seriestarten hade stoppat forvarvet for en sak som
forst behovs timmar senare. Uppmatt: dygnet gar anda inte forlorat av ett
stopp har - en-korning-regeln (test_en_korning.py) knyter sig till
emotionsmanifestets sha256-sidecar, som skrivs langt senare - men ett stoppat
urval ar anda en stillastaende natt, och den som laser loggen 06:40 den 1
december ska se ratt sak.

DATUMET STAR INTE HAR. Proven flyttar pool_evidence.SERIESTART och kraver att
gransen foljer med. Ett prov som skrev "20261201" en andra gang vore FYND 004
i provform: dagen seriestarten andras skulle provet fortsatta vara gront pa
fel datum.

Skriven av den andra parten an den som skrev grinden, enligt AGENTS.md.
"""
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import gates
import measurements
import pool_evidence

FORE = "20261130"
START = pool_evidence.SERIESTART
EFTER = "20261202"


def post(day, **extra):
    """En matpost dar ALLA obligatoriska falt ar skrivna om inget annat sags.

    Vardena ar likgiltiga for det har provet - grinden laser att de finns.
    Matpunkt 11 ar den enda som provas mot sitt varde, och den sätts explicit
    av varje prov nedan.
    """
    p = {k: 1 for k in measurements.OBLIGATORISKA}
    p["day"] = day
    p.update(extra)
    return p


def kor(p):
    gates.gate_matpost("2026/335", p, measurements.OBLIGATORISKA)


# ---------- faltet saknas: faller oavsett dygn ----------

@pytest.mark.parametrize("day", [FORE, START, EFTER, ""])
def test_saknat_falt_faller_oavsett_dygn(day):
    p = post(day)
    del p[measurements.NYCKELN]
    with pytest.raises(gates.GateFailure) as e:
        kor(p)
    assert "obligatoriskt falt" in str(e.value)


# ---------- faltet false: datumet avgor ----------

def test_false_fore_seriestart_stoppar_inte_forvarvet():
    """Det kritiska provet. Faller den har har grinden stoppat en natt for en
    sak som inte var oaterkallelig."""
    kor(post(FORE, **{measurements.NYCKELN: False}))


def test_false_pa_seriestartens_egen_dag_faller():
    """Gransen ar inklusiv: forsta seriedygnet ar redan i serien."""
    with pytest.raises(gates.GateFailure) as e:
        kor(post(START, **{measurements.NYCKELN: False}))
    assert "nyckel" in str(e.value).lower()


def test_false_efter_seriestart_faller():
    with pytest.raises(gates.GateFailure):
        kor(post(EFTER, **{measurements.NYCKELN: False}))


def test_true_gar_igenom_pa_bada_sidor_om_gransen():
    """Kontrollprov. Faller det har ar det inte nyckeln proven mater."""
    for day in (FORE, START, EFTER):
        kor(post(day, **{measurements.NYCKELN: True}))


# ---------- gransen ar pool_evidence.SERIESTART, inte en andra stavning ----------

def test_gransen_foljer_SERIESTART_och_star_inte_i_grinden(monkeypatch):
    """Flyttas seriestarten ska gransen flytta med. Gor den inte det star
    datumet nagonstans en andra gang."""
    monkeypatch.setattr(pool_evidence, "SERIESTART", "20270115")
    # 20261202 lag EFTER den gamla gransen och ligger FORE den nya
    kor(post(EFTER, **{measurements.NYCKELN: False}))
    with pytest.raises(gates.GateFailure):
        kor(post("20270116", **{measurements.NYCKELN: False}))


# ---------- posten utan dygn: grinden gissar inte ----------

def test_post_utan_dygn_faller_INTE_pa_false(capsys):
    """PINNAT, INTE REKOMMENDERAT.

    Grinden valjer att inte gissa att en post utan "day" hor till serien.
    Foljden ar att en post som tappat sitt dygn stanger av matpunkt 11 tyst,
    aven efter seriestarten - "day" star inte i OBLIGATORISKA och inget annat
    prov fangar det. notera() skriver faltet vid varje skrivning, sa en post pa
    disk bar det alltid, och darfor ar halet i dag teoretiskt.

    Provet star har for att valet ska vara SYNLIGT och inte en bieffekt. Andras
    beslutet till att en post utan dygn ska falla, ar det det har provet som
    ska bytas - och da med vett, inte for att det blev rott."""
    kor(post("", **{measurements.NYCKELN: False}))
    assert "stoppar det inte forvarvet" in capsys.readouterr().out


# ---------- vardet lamnar aldrig matningen ----------

def test_nyckeln_syns_aldrig_i_varken_matning_eller_grindutskrift(
        monkeypatch, capsys):
    """En langd ar ocksa en upplysning om en hemlighet, och posten ligger i
    arkivet."""
    hemlis = "sk-ant-PROVVARDE-840913"
    monkeypatch.setenv("ANTHROPIC_API_KEY", hemlis)
    varde = measurements.nyckel_narvarande()
    assert varde is True
    kor(post(EFTER, **{measurements.NYCKELN: varde}))
    ut = capsys.readouterr().out
    for bit in (hemlis, hemlis[:8], hemlis[-4:], str(len(hemlis))):
        assert bit not in ut, f"{bit!r} lackte till grindens utskrift"


@pytest.mark.parametrize("satt,vantat", [
    ("sk-ant-x", True), ("", False), ("   ", False), ("\n", False)])
def test_matningen_sjalv(monkeypatch, satt, vantat):
    monkeypatch.setenv("ANTHROPIC_API_KEY", satt)
    assert measurements.nyckel_narvarande() is vantat


def test_osatt_variabel_ar_false(monkeypatch):
    """Osatt och tom ar samma svar for kedjan: den kan inte klassificera."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert measurements.nyckel_narvarande() is False
