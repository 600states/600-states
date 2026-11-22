"""Acceptanstest for det harledda dygnet, korningsfonstret och frirymden.

Skrivet av den andra parten an den som implementerade b152e12 och 73537b4,
enligt AGENTS.md.

Tre pastaenden provas:

1. DYGNET HARLEDS UR KLOCKAN, EN GANG, OCH RATT. Ett dygn fel ger ett helt
   felaktigt verk, och den sortens fel syns inte i nagon utskrift - manifestet
   ser lika korrekt ut som ett riktigt.

2. KORNING_START_UTC LASES, DEN KOPIERAS INTE. Konstanten flyttas i ett test
   och gransen ska folja med. Vardet stod i pool_evidence och lastes ingenstans
   i hela src/ i veckor: det sag ut som en regel och var ett onskemal.

3. GRINDEN HINDRAR FOR TIDIGT, ALDRIG FOR SENT. Ett dygn vars bevisfonster
   hunnit stanga ska fortfarande ga att kora - det landar under golvet och blir
   UNQUALIFIED av sig sjalvt. En ovre grans har skulle gora ett missat dygn
   till ett dygn som aldrig funnits, och den skulle dessutom omojliggora
   inkorningen, som kors med flit efter fonstret.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import acquire
import gates
import pool_evidence as pe
import run_state
import statepaths as sp


def nu(text):
    """'2026-11-20 00:05' -> aware datetime i UTC."""
    return datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)


# ---- 1. harledningen -----------------------------------------------------
@pytest.mark.parametrize("klockan, vantat", [
    ("2026-11-20 00:00", "20261119"),   # dygnet stangde i samma sekund
    ("2026-11-20 00:05", "20261119"),   # seriens tid
    ("2026-11-20 04:00", "20261119"),   # inkorningens tid
    ("2026-11-20 23:59", "20261119"),   # sent samma dygn, fortfarande gardagen
    ("2027-01-01 00:05", "20261231"),   # arsskiftet
    ("2026-03-01 00:05", "20260228"),   # 2026 ar inget skottar
    ("2024-03-01 00:05", "20240229"),   # 2024 ar det
])
def test_senast_stangda_dygnet(klockan, vantat):
    assert run_state.senast_stangda_dygnet(nu(klockan)) == vantat


def test_harledningen_ger_aldrig_dagens_dygn():
    """Ett dygn som inte stangt gar inte att observera. Harledningen far darfor
    aldrig ge dagens datum, nar pa dygnet den an anropas."""
    for timme in range(24):
        assert run_state.senast_stangda_dygnet(nu(f"2026-11-20 {timme:02d}:00")) != "20261120"


# ---- 2. fonstret ---------------------------------------------------------
def test_dygn_som_inte_stangt_stoppas():
    with pytest.raises(gates.GateFailure):
        gates.gate_korningsfonster(nu("2026-11-19 23:59"), "20261119")


@pytest.mark.parametrize("klockan", ["2026-11-20 00:00", "2026-11-20 00:04"])
def test_fore_starttiden_stoppas(klockan):
    with pytest.raises(gates.GateFailure):
        gates.gate_korningsfonster(nu(klockan), "20261119")


def test_exakt_pa_starttiden_slapps_igenom():
    """Gransen ar inklusiv. Den som star pa den ar inne."""
    gates.gate_korningsfonster(nu("2026-11-20 00:05"), "20261119")


@pytest.mark.parametrize("klockan", [
    "2026-11-20 00:06",
    "2026-11-20 03:00",   # bevisfonstret stanger har
    "2026-11-20 03:30",   # efter det - tillatet, dygnet blir UNQUALIFIED
    "2026-11-20 04:00",   # inkorningen kors med flit har
    "2026-11-30 09:00",   # tio dygn sent
])
def test_sent_ar_alltid_tillatet(klockan):
    gates.gate_korningsfonster(nu(klockan), "20261119")


def test_gransen_foljer_konstanten_och_inte_ett_tal_i_koden(monkeypatch):
    """Utan det har testet kan sviten inte skilja en implementation som laser
    KORNING_START_UTC fran en som jamfor mot 00:05 skrivet i grinden."""
    monkeypatch.setattr(pe, "KORNING_START_UTC", "02:30")
    with pytest.raises(gates.GateFailure):
        gates.gate_korningsfonster(nu("2026-11-20 02:29"), "20261119")
    gates.gate_korningsfonster(nu("2026-11-20 02:30"), "20261119")


def test_klockan_kommer_fran_anroparen():
    """Samma dygn, tva klockslag, tva utfall. Laste grinden klockan sjalv vore
    argumentet verkningslost och bada anropen ge samma svar."""
    with pytest.raises(gates.GateFailure):
        gates.gate_korningsfonster(nu("2026-11-20 00:04"), "20261119")
    gates.gate_korningsfonster(nu("2026-11-20 00:05"), "20261119")


# ---- 3. frirymden --------------------------------------------------------
def test_frirymden_faller_strax_under_behovet():
    with pytest.raises(gates.GateFailure):
        gates.gate_frirymd(1000, 999, "testets tal")


def test_frirymden_slapper_igenom_pa_exakt_behovet():
    gates.gate_frirymd(1000, 1000, "testets tal")


def test_overhoppad_kontroll_faller_inte(capsys):
    """Finns inget fardigt dygn att mata pa provas ingenting - men det ska STA
    i utskriften. En kontroll som tyst hoppas over ser ut som en som gick
    igenom, och det ar den enda sorts tystnad som ar farlig har."""
    gates.gate_frirymd(None, 123, "inget fardigt dygn att mata pa")
    ut = capsys.readouterr().out
    assert "PROVADES INTE" in ut
    assert "inget fardigt dygn" in ut


def test_behovet_ar_tre_ganger_det_storsta_av_de_fem_senaste(monkeypatch):
    """Tre ganger, inte en: en grind som kraver exakt ett dygn slapper igenom
    den sista korning som far plats och faller forst nar arkivet ar fullt.
    Och det STORSTA av de fem, inte snittet - ett dygn kan vaxa."""
    # d1 ar storst och ligger utanfor fonstret pa fem - tas den med ar
    # fonstret inte ett fonster.
    avtryck = {"d1": 999, "d2": 20, "d3": 30, "d4": 40, "d5": 10, "d6": 50}
    monkeypatch.setattr(run_state, "_fardiga_dygn", lambda: list(avtryck))
    monkeypatch.setattr(run_state, "_bevisandel", lambda n: 0)
    monkeypatch.setattr(run_state, "_dygnets_avtryck", lambda d, m, a: avtryck[d])
    monkeypatch.setattr(run_state.shutil, "disk_usage",
                        lambda p: type("D", (), {"free": 10**12})())
    behov, fri, matt_pa = run_state._frirymdsbehov()
    assert behov == 150, f"forvantade 3 x 50 (d6), fick {behov}"
    assert "tre ganger" in matt_pa


def test_inget_fardigt_dygn_ger_inget_behov(monkeypatch):
    monkeypatch.setattr(run_state, "_fardiga_dygn", lambda: [])
    monkeypatch.setattr(run_state.shutil, "disk_usage",
                        lambda p: type("D", (), {"free": 7})())
    behov, fri, matt_pa = run_state._frirymdsbehov()
    assert behov is None
    assert fri == 7


# =========================================================================
# 4. HARLEDNINGEN HAR ETT ENDA HEM  (tillagt for 6f8d485)
#
# Tva program harleder nu dygnet: acquire och run_state. Korning A anropar
# dem minuter isar. Harleder de pa var sitt satt kan de hamna pa olika dygn
# av andra skal an klockan, och det syns ingenstans - acquire fryser ett
# dygn och run_state bygger kandidater ur ett annat.
#
# Implementationen svarade pa midnattsfragan med ett resonemang ur koden,
# inte med en korning. Testerna nedan gor om det till en matning.
# =========================================================================


def test_bada_programmen_harleder_genom_samma_funktion():
    """EN DEFINITION, ETT STALLE. run_state.senast_stangda_dygnet ska vara en
    bindning till statepaths funktion, aldrig en andra implementation."""
    assert run_state.senast_stangda_dygnet is sp.senast_stangda_dygnet


def test_acquire_harleder_samma_dygn_som_run_state_hela_dygnet_runt():
    """Provat timme for timme over ett dygnsskifte. Ett avsteg pa en enda
    timme racker: korning A startar 00:05 och en avvikelse dar ger ett
    snapshot av ett dygn och kandidater ur ett annat."""
    for d in (19, 20, 21):
        for t in range(24):
            klockan = nu(f"2026-11-{d:02d} {t:02d}:30")
            assert sp.senast_stangda_dygnet(klockan) == run_state.senast_stangda_dygnet(klockan)


def test_harledningen_byter_dygn_exakt_en_gang_per_dygn_och_vid_midnatt():
    """Fangar en forskjutning eller en tidszonsglidning: byter vardet vid
    01:00 i stallet for 00:00 ar NAS:ens lokala tid inblandad nagonstans."""
    start = nu("2026-11-20 00:00")
    byten = []
    forra = None
    for t in range(48):
        klockan = start + timedelta(hours=t)
        v = sp.senast_stangda_dygnet(klockan)
        if forra is not None and v != forra:
            byten.append(klockan.strftime("%Y-%m-%d %H:%M"))
        forra = v
    assert byten == ["2026-11-21 00:00"], f"bytte vid {byten}"


def test_midnattsfallet_ar_hogljutt_fore_starttiden():
    """MIDNATTSFALLET, HALVA ETT.

    Hamnar acquire och run_state pa var sin sida om midnatt harleder
    run_state ett dygn senare an det acquire frös. Sker dess anrop fore
    00:05 stoppar fonstergrinden det: dygnet den harledde stangde nyss.

    Implementationen laste sig till detta. Har kors det."""
    frost_av_acquire = sp.senast_stangda_dygnet(nu("2026-11-21 23:58"))
    harlett_av_run_state = sp.senast_stangda_dygnet(nu("2026-11-22 00:02"))
    assert frost_av_acquire != harlett_av_run_state, "testet provar fel sak"
    with pytest.raises(gates.GateFailure):
        gates.gate_korningsfonster(nu("2026-11-22 00:02"), harlett_av_run_state)


def test_efter_starttiden_ar_det_inte_fonstret_som_stoppar():
    """MIDNATTSFALLET, HALVA TVA - OCH DEN HAR HALVAN AR INTE HELT PROVAD.

    Efter 00:05 slapper fonstergrinden igenom. Da ar det rasnapshotet som far
    stoppa: run_state letar efter det senare dygnets mentions-zip, och den kan
    inte finnas, for det dygnet stangde i samma ogonblick.

    Det HAR testet provar bara forsta ledet: att grinden inte ar det som
    stoppar efter 00:05. Att run_state darefter avslutar med felkod 4 ar inte
    kort av nagon part - det vilar pa lasning av koden, hos bade den som
    byggde och den som provar."""
    harlett = sp.senast_stangda_dygnet(nu("2026-11-22 00:06"))
    assert harlett == "20261121"
    gates.gate_korningsfonster(nu("2026-11-22 00:06"), harlett)


# ---- acquires kommandorad ------------------------------------------------
def _kor_acquire(monkeypatch, argv):
    """Anropar acquire.main() med stubbad acquire(). Ror aldrig natet.

    Provar KOMMANDORADEN, inte harledningen. Skillnaden ar inte akademisk:
    en svit som bara provar statepaths.senast_stangda_dygnet slapper igenom
    en acquire som slutat anropa den - och det var exakt felet som stoppade
    inkorningens forsta natt 2026-11-22.
    """
    sett = {}
    def stubb(day, budget=None, force=False, vanta_events=False):
        sett.update(day=day, budget=budget, force=force, vanta=vanta_events)
        return 0
    monkeypatch.setattr(acquire, "acquire", stubb)
    monkeypatch.setattr(sys, "argv", ["acquire.py"] + argv)
    with pytest.raises(SystemExit):
        acquire.main()
    return sett


def test_acquire_utan_argument_harleder_dygnet(monkeypatch):
    sett = _kor_acquire(monkeypatch, [])
    assert sett["day"] == sp.senast_stangda_dygnet(datetime.now(timezone.utc))


def test_acquire_med_bara_en_flagga_harleder_anda(monkeypatch):
    """REGRESSIONEN. --vanta-events tolkades som ett datum, och korning B
    foll med felkod 1 innan den hunnit fraga GDELT om nagot."""
    sett = _kor_acquire(monkeypatch, ["--vanta-events"])
    assert sett["day"] == sp.senast_stangda_dygnet(datetime.now(timezone.utc))
    assert sett["vanta"] is True


def test_acquire_med_flera_flaggor_harleder_anda(monkeypatch):
    sett = _kor_acquire(monkeypatch, ["--budget", "40", "--force"])
    assert sett["day"] == sp.senast_stangda_dygnet(datetime.now(timezone.utc))
    assert (sett["budget"], sett["force"]) == (40, True)


def test_acquire_med_dygn_tar_dygnet(monkeypatch):
    """Arkivvagen ska vara oforandrad."""
    sett = _kor_acquire(monkeypatch, ["20261111"])
    assert sett["day"] == "20261111"


def test_acquire_med_dygn_och_flaggor(monkeypatch):
    sett = _kor_acquire(monkeypatch, ["20261111", "--vanta-events", "--budget", "7"])
    assert sett["day"] == "20261111"
    assert (sett["vanta"], sett["budget"]) == (True, 7)


def test_acquire_avvisar_ett_felaktigt_dygnsformat(monkeypatch):
    """Ett trasigt datum ska kasta, aldrig harledas bort. Harleds det i tysthet
    kor arkivvagen fel dygn utan att nagon ser det."""
    monkeypatch.setattr(acquire, "acquire", lambda *a, **k: 0)
    monkeypatch.setattr(sys, "argv", ["acquire.py", "2026-11-11"])
    with pytest.raises(ValueError):
        acquire.main()
