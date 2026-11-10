"""Referensen ar en fast punkt, och vilken punkt det var ska gå att se.

Batteriet mater en kandidat mot en referens. Fram till 2026-11-10 stod det
ingenstans i resultatet VILKEN referens matningen gjorts mot - och den 10:e
byggdes en ny, under formen en observation per begaran. Tva poster i samma
fil kan darmed vara matta mot olika nollpunkter.

En post som inte sager vilken referens den matts mot gar inte att jamfora med
en annan post. Det ar samma tysta lucka som kostat projektet mest: ett varde
vars harkomst inte star nagonstans.
"""
import inspect, sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src")); sys.path.insert(0, str(ROT / "tools"))
import calibrate, bygg_referens


def test_varje_resultat_bar_sin_referens():
    src = inspect.getsource(calibrate.kor)
    assert '"referens": REFERENS.name' in src
    assert '"referens_sha256"' in src


def test_nyaste_referensen_valjs_och_den_gamla_ligger_kvar():
    src = inspect.getsource(calibrate.referensfil)
    assert "REFERENS_v2.0" in src
    assert "600_STATES_KALIBRERINGSBATTERI_v1.0_REFERENS.json" in src, \
        "fallbacken till v1.0 maste finnas kvar"


def test_referensen_skrivs_en_gang():
    """Samma regel som for ett fryst dygn: det ar inte korningens sak att
    avgora om en referens ska ersattas."""
    src = inspect.getsource(bygg_referens.main)
    assert "if NY.exists():" in src
    assert src.index("if NY.exists():") < src.index("import os, anthropic"), \
        "grinden star efter anropen — pengarna ar da redan utlagda"


def test_referensen_byggs_inte_ur_matkorningen():
    """Byggdes den ur samma svar som jamforelsen skulle en rad i tabellen
    samtidigt vara tabellens nollpunkt."""
    assert "kor_en_i_taget" in inspect.getsource(bygg_referens.main), \
        "referensen ska koras fram, inte lasas ur en tidigare matning"
    doc = bygg_referens.__doc__
    assert "REFERENSEN AR INTE MATKORNINGEN" in doc


def test_formen_star_i_referensens_meta():
    src = inspect.getsource(bygg_referens.main)
    for falt in ('"form"', '"pass"', '"prompt_sha256"', '"ersatter"', '"byggd"'):
        assert falt in src, f"{falt} saknas i referensens meta"
