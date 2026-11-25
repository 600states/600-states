"""Nattens matpost: proven mot postens BETEENDE, aldrig mot dess konstanter.

VARFOR
Matposten finns for att NAS raknade poolens bevisandel for hand tre natter i
rad. Ett prov som laste samma faltnamn ur measurements.py skulle bara upprepa
att raden ar lik sig sjalv. Darfor skriver proven harunder riktiga poster till
disk, kor grinden mot dem, och genererar dodsmatrisen UR OBLIGATORISKA sjalv —
sa att ett nytt obligatoriskt falt far sitt prov utan att nagon minns det.

Inget prov harunder kraver dataarkivet: las() och notera() tar data= och pekas
pa en tmp-katalog.
"""
import json
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))

import gates
import measurements as m
import statepaths as sp

DYGN = "20261201"


def _komplett():
    """En post som grinden ska slappa igenom. Bara obligatoriska falt."""
    return {
        m.KANDIDATER: 3826,
        m.POOLENS_ANDEL: {"av": 3826, "i_fonstret": 3630, "andel": 3630 / 3826},
        m.DE_VALDAS_ANDEL: {"av": 600, "i_fonstret": 570, "andel": 0.95},
        m.DOMANER: 82,
        m.SERIEN: {"series": "CANONICAL", "skal": ""},
        m.EVENTS: {"events_last_404_utc": "2026-12-01T07:25:27Z",
                   "events_frozen_at_utc": "2026-12-01T07:30:29Z"},
    }


def _kor(post):
    """(gick_igenom, text). Grinden kastar GateFailure nar den faller."""
    try:
        gates.gate_matpost("2026/335", post, m.OBLIGATORISKA)
        return True, ""
    except gates.GateFailure as e:
        return False, str(e)


# ------------------------------------------------- de tva storheterna

def test_de_tva_andelarna_ar_skilda_storheter():
    """Matpunkt 2 och 3 far aldrig bli ett tal. FYND 004 i berakningsform."""
    assert m.POOLENS_ANDEL != m.DE_VALDAS_ANDEL
    assert m.POOLENS_ANDEL in m.OBLIGATORISKA
    assert m.DE_VALDAS_ANDEL in m.OBLIGATORISKA

    poolen = m.fonsterandel(["CAPTURED_IN_WINDOW"] * 3630 + ["NO_EVIDENCE"] * 196)
    valda = m.fonsterandel(["CAPTURED_IN_WINDOW"] * 570 + ["NO_EVIDENCE"] * 30)

    assert poolen["av"] == 3826 and valda["av"] == 600
    assert poolen["i_fonstret"] == 3630 and valda["i_fonstret"] == 570
    # UPPMATT 2026-11-25: urvalet HOJDE andelen denna natt. Provet far darfor
    # inte forvanta sig ett tecken — bara att talen ar olika storheter.
    assert poolen["andel"] != valda["andel"]

    post = dict(_komplett(), **{m.POOLENS_ANDEL: poolen, m.DE_VALDAS_ANDEL: valda})
    assert post[m.POOLENS_ANDEL] is not post[m.DE_VALDAS_ANDEL]


def test_obligatoriska_och_valfria_tacker_alla_tio_utan_overlapp():
    alla = set(m.OBLIGATORISKA) | set(m.VALFRIA)
    assert not (set(m.OBLIGATORISKA) & set(m.VALFRIA)), "ett falt ar bade och"
    assert len(alla) == 10, f"{len(alla)} falt, inte tio"
    assert len(m.OBLIGATORISKA) == len(set(m.OBLIGATORISKA)), "dubblett"


# ------------------------------------------------------ dodsmatrisen

@pytest.mark.parametrize("falt", m.OBLIGATORISKA)
def test_grinden_faller_pa_varje_saknat_obligatoriskt_falt(falt):
    """Genererad UR listan. Ett nytt obligatoriskt falt far sitt prov gratis."""
    post = _komplett()
    del post[falt]
    gick, _ = _kor(post)
    assert not gick, f"grinden slappte igenom en post utan {falt}"


@pytest.mark.parametrize("falt", m.OBLIGATORISKA)
def test_grinden_faller_nar_faltet_finns_men_ar_tomt(falt):
    """Ett falt som bara bar None ar inte skrivet."""
    post = _komplett()
    post[falt] = None
    gick, _ = _kor(post)
    assert not gick, f"grinden godtog {falt} = None"


def test_grinden_gar_igenom_pa_en_komplett_post():
    """POSITIVT KONTROLLPROV. Utan det kan proven ovan passera av fel skal:
    en grind som alltid faller klarar varje dodsmatris."""
    gick, text = _kor(_komplett())
    assert gick, f"komplett post foll: {text}"


def test_grinden_faller_pa_en_tom_post():
    gick, _ = _kor({})
    assert not gick


def test_kontrollen_att_posten_FINNS_kan_falla_ensam():
    """ISOLERAR grindens forsta kontroll.

    En tom post faller ocksa pa den andra kontrollen — varje obligatoriskt falt
    saknas — sa test_grinden_faller_pa_en_tom_post bevisar inte att den FORSTA
    kontrollen gor nagot. Uppmatt: stangs den av passerar sviten anda.
    Med en tom lista obligatoriska hittar den andra kontrollen ingenting, och
    da ar den forsta det enda som kan falla.

    En kontroll som aldrig kan vara ensam orsak till ett stopp ar en utskrift,
    inte en grind.
    """
    try:
        gates.gate_matpost("2026/335", {}, ())
        pytest.fail("grinden slappte igenom en post som inte finns")
    except gates.GateFailure:
        pass

    # Positivt kontrollprov: samma anrop med en post SKA ga igenom.
    gates.gate_matpost("2026/335", {m.KANDIDATER: 0}, ())


# -------------------------------------------- de tva avsiktliga fallen

def test_noll_ar_ett_tal():
    """Ett dygn med noll kandidater ar MATT, inte omatt."""
    post = dict(_komplett(), **{m.KANDIDATER: 0})
    gick, text = _kor(post)
    assert gick, f"noll kandidater lastes som omatt: {text}"


def test_events_en_tid_racker_men_bada_None_gor_det_inte():
    """events_last_404_utc = None betyder 'ingen 404 sags' och ar en matning.
    Ar BADA None har ingen last snapshotmanifestet."""
    en = dict(_komplett(), **{m.EVENTS: {
        "events_last_404_utc": None,
        "events_frozen_at_utc": "2026-12-01T07:30:29Z"}})
    gick, text = _kor(en)
    assert gick, f"en satt tid avvisades: {text}"

    ingen = dict(_komplett(), **{m.EVENTS: {
        "events_last_404_utc": None, "events_frozen_at_utc": None}})
    gick, _ = _kor(ingen)
    assert not gick, "bada tiderna None godtogs"


# --------------------------------------------------- inga malvarden

def test_grinden_provar_aldrig_om_talet_ar_BRA():
    """1.17 forbjuder malvarden. En post med usla tal ska GA IGENOM: grinden
    provar att talet finns, aldrig att det duger. Faller det har provet har
    nagon byggt in en troskel, och det ar avsnitt 0:s forbud."""
    uselt = dict(_komplett(), **{
        m.KANDIDATER: 1,
        m.POOLENS_ANDEL: {"av": 1, "i_fonstret": 0, "andel": 0.0},
        m.DE_VALDAS_ANDEL: {"av": 1, "i_fonstret": 0, "andel": 0.0},
        m.DOMANER: 1,
        m.SERIEN: {"series": "UNQUALIFIED", "skal": "under golvet"},
    })
    gick, text = _kor(uselt)
    assert gick, f"grinden domde kvaliteten i stallet for att lasa: {text}"


# ------------------------------------------------- posten pa disk

def test_notera_slar_ihop_och_skriver_aldrig_over(tmp_path):
    """Korning A:s falt ska finnas kvar efter att B skrivit sina."""
    (tmp_path / sp.GENERATION_DIR).mkdir(parents=True, exist_ok=True)
    sp.outdir(tmp_path, DYGN).mkdir(parents=True, exist_ok=True)

    m.notera(DYGN, "pool", data=tmp_path, **{
        m.KANDIDATER: 3826,
        m.POOLENS_ANDEL: {"av": 3826, "i_fonstret": 3630, "andel": 0.94885}})
    m.notera(DYGN, "select", data=tmp_path, **{
        m.DOMANER: 82, m.SERIEN: {"series": "CANONICAL", "skal": ""}})

    post = m.las(DYGN, data=tmp_path)
    assert post[m.KANDIDATER] == 3826, "korning A:s falt forsvann"
    assert post[m.POOLENS_ANDEL]["i_fonstret"] == 3630
    assert post[m.DOMANER] == 82


def test_las_speglar_disken_och_cachar_inte(tmp_path):
    """Grinden laser posten FRAN DISK. Cachade las() skulle gora den till en
    grind pa minnet, och da provas inte att skrivningen skedde."""
    sp.outdir(tmp_path, DYGN).mkdir(parents=True, exist_ok=True)
    m.notera(DYGN, "pool", data=tmp_path, **{m.KANDIDATER: 111})
    assert m.las(DYGN, data=tmp_path)[m.KANDIDATER] == 111

    traff = list(sp.outdir(tmp_path, DYGN).glob("*MEASUREMENTS.json"))
    assert len(traff) == 1, f"{len(traff)} matposter pa disk"
    d = json.loads(traff[0].read_text(encoding="utf-8"))
    d[m.KANDIDATER] = 222
    traff[0].write_text(json.dumps(d), encoding="utf-8")

    assert m.las(DYGN, data=tmp_path)[m.KANDIDATER] == 222, "las() cachar"


def test_matposten_ligger_i_dygnets_katalog(tmp_path):
    sp.outdir(tmp_path, DYGN).mkdir(parents=True, exist_ok=True)
    m.notera(DYGN, "pool", data=tmp_path, **{m.KANDIDATER: 1})
    traff = list(sp.outdir(tmp_path, DYGN).glob("*MEASUREMENTS.json"))
    assert traff, "matposten hamnade inte i dygnets katalog"
    assert sp.state_key(DYGN).replace("/", "_") in traff[0].name
