"""Acceptanstest for dag ettens sida, 2026/335. A19.

Skrivet av den andra parten an den som byggde sidan, enligt AGENTS.md.

KRAVET SOM SIDAN BYGGDES FOR: SIDAN MASTE KUNNA SAGA BADA SAKERNA. Ett
seriedygn kan bli CANONICAL eller UNQUALIFIED, och vilket det blir vet ingen i
forvag - det avgors av varlden den natten. En sida som forutsatter CANONICAL
publicerar ett osant pastaende den dag dygnet inte kvalificerar, och det ar
dag ett den risken ar storst: det finns ingen tidigare sida att jamfora med.

Tre saker provas, valda for att de kan ga sonder TYST:

1. ATT BADA TEXTERNA FINNS I KALLFILEN. Tas den ena bort kan sidan inte langre
   uttrycka det utfallet, och bygget ska stanna i stallet for att publicera
   det kvarvarande.

2. ATT DET BORTVALDA FORSVINNER HELT. Utfallen star pa tva stallen var -
   ingressen och brodtexten. Tas bara den forsta forekomsten bort pastar sidan
   bada utfallen samtidigt, vilket ar varre an att pasta fel.

3. ATT SIDAN INTE BYGGS AV ETT HALVKORT DYGN. Tre filer ur tre olika steg
   kravs. En sida av tomma falt ar samre an ingen sida.
"""
import json
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
KALLA = ROT / "site" / "state-2026-335.html"
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT / "site"))
import statepaths as sp
import build


# ---- 1. kallfilen bar varje utfall sidan kan hamna i ---------------------
UTFALL = ("canonical", "unqualified",          # serien
          "unstamped", "stamped", "anchored",  # bevislaget, tre tillstand
          "signed", "unsigned")                # signaturen


@pytest.mark.parametrize("namn", UTFALL)
def test_kallfilen_bar_blocket_for_varje_utfall(namn):
    """Varje tillstand dygnet kan hamna i ska ga att LASA i kallfilen. En
    mening som bara finns i bygget gar inte att granska dar sidan skrivs."""
    assert build._block(KALLA.read_text(encoding="utf-8"), namn), (
        f"kallfilen saknar data-when-{namn} - sidan kan inte saga det utfallet")


def test_bevislaget_ar_tre_tillstand_och_inte_tva():
    """Ostamplat, stamplat och forankrat ar tre olika pastaenden. Slas de
    tva senare ihop pastar sidan en forankring som annu inte finns."""
    html = KALLA.read_text(encoding="utf-8")
    assert len({build._block(html, n).group(0)
                for n in ("unstamped", "stamped", "anchored")}) == 3


# ---- 2. det bortvalda forsvinner HELT ------------------------------------
def sida(kanonisk=2, okvalificerad=2):
    """En minimal sida med samma markup som kallfilen, med valbart antal
    forekomster av varje utfall."""
    rader = ["<html><body>"]
    rader += ['  <p class="kind" data-when-canonical>EN AV 600</p>'] * kanonisk
    rader += ['  <div data-when-unqualified>INTE EN AV 600</div>'] * okvalificerad
    rader.append("</body></html>")
    return "\n".join(rader) + "\n"


def test_varje_forekomst_av_det_bortvalda_tas_bort():
    """Utfallen star pa tva stallen var i den riktiga sidan. Tas bara den
    forsta bort star den andra kvar och sidan sager bada sakerna."""
    ut = build.valj(sida(), "prov", "canonical", ("canonical", "unqualified"))
    assert "INTE EN AV 600" not in ut
    assert ut.count("EN AV 600") == 2


def test_samma_at_andra_hallet():
    """Riktningen far inte vara inbyggd. Faller bara det ena hallet ar
    provet ovan ett prov pa ordningen i tupeln."""
    ut = build.valj(sida(), "prov", "unqualified", ("canonical", "unqualified"))
    assert "EN AV 600" not in ut.replace("INTE EN AV 600", "")
    assert ut.count("INTE EN AV 600") == 2


def test_aktiv_none_tar_bort_alla_utfall():
    """Startsidans lank till ett dygn som inte finns. Inget block kvar."""
    ut = build.valj(sida(), "prov", None, ("canonical", "unqualified"))
    assert "EN AV 600" not in ut and "INTE EN AV 600" not in ut


def test_bygget_stannar_nar_ett_utfall_saknas():
    """Ett bortfallet block ar ett utfall sidan inte langre kan uttrycka,
    och det ska inte ga att tappa bort tyst."""
    with pytest.raises(SystemExit) as e:
        build.valj(sida(okvalificerad=0), "prov", "canonical",
                   ("canonical", "unqualified"))
    assert "unqualified" in str(e.value)


def test_kontrollprov_bygget_gar_igenom_nar_bada_finns():
    """Provet ovan ar vardelost om valj() stannar pa allt."""
    build.valj(sida(), "prov", "canonical", ("canonical", "unqualified"))


# ---- 3. inget span lamnas otomt, ingen plats saknas ----------------------
def test_fyll_skriver_in_vardet():
    ut = build.fyll("<span data-window></span>", "prov", "window", "571 of 600")
    assert ut == "<span data-window>571 of 600</span>"


def test_fyll_stannar_nar_platsen_saknas():
    """Byts ett span om i kallfilen utan att bygget foljer med, ska bygget
    stanna - inte publicera en sida dar talet aldrig skrevs in."""
    with pytest.raises(SystemExit) as e:
        build.fyll("<p>ingen plats har</p>", "prov", "sha", "abc")
    assert "sha" in str(e.value)


# ---- 4. sidan byggs inte av ett halvkort dygn ----------------------------
DAG = "20261201"


def las_dygn(rot):
    """Nyckeln och dygnstalet ur statepaths, inte skrivna 2026_335 har."""
    nyckel = sp.state_key(DAG)
    return nyckel, nyckel.split("_")[-1]


def gor_filerna(rot, utelamna=None):
    """De tre filer tre olika steg skriver. En kan utelamnas."""
    nyckel, dygn = las_dygn(rot)
    st = rot / "08_V3_STATES" / ("STATE_" + nyckel)
    st.mkdir(parents=True, exist_ok=True)
    if utelamna != "pre":
        sp.pre_manifest(rot, DAG).write_text("x", encoding="utf-8")
    if utelamna != "farg":
        (st / f"600_STATES_{nyckel}_EMOTION_COLOR_MANIFEST_v3.4_CONSENSUS.csv"
         ).write_text("x", encoding="utf-8")
    if utelamna != "site":
        (st / f"site_{nyckel}.json").write_text("{}", encoding="utf-8")
    return nyckel, dygn


def test_alla_tre_filerna_ger_ett_dygn_som_finns(tmp_path):
    nyckel, dygn = gor_filerna(tmp_path)
    assert build.dygnet_finns(tmp_path, DAG, nyckel, dygn) is True


@pytest.mark.parametrize("saknas", ["pre", "farg", "site"])
def test_en_saknad_fil_racker_for_att_dygnet_inte_finns(tmp_path, saknas):
    """Tre steg skriver var sin fil. Finns tva av tre har natten stannat
    mitt i, och en sida byggd pa det bar falt som aldrig fylldes."""
    nyckel, dygn = gor_filerna(tmp_path, utelamna=saknas)
    assert build.dygnet_finns(tmp_path, DAG, nyckel, dygn) is False
