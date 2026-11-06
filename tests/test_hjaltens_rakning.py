"""Grinden mot hjaltens rakning.

Sidan pastod "wrong eleven times" och listade tio kapitel. Felet var inte
siffran utan att ingen kontroll kunde fanga den - samma form som kapitel IV
pa sidan sjalv, "The check that could not fail". Testet finns for att visa
att den har grinden KAN falla.
"""
import io, sys
from pathlib import Path
ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT / "site"))
import pytest
import build

SIDA = ROT / "site" / "labs.html"

def kapitel(n):
    return "".join('<p class="ch-num">%s</p>' % r for r in
                   ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
                    "XI", "XII"][:n])

def sida(ord_, n):
    return '<p class="lead">The instrument has been wrong %s times.</p>%s' % (ord_, kapitel(n))

def test_den_riktiga_sidan_passerar():
    html = io.open(SIDA, encoding="utf-8").read()
    assert build.gate_hjaltens_rakning(html) == 10

def test_fel_siffra_stoppar_bygget():
    with pytest.raises(SystemExit) as e:
        build.gate_hjaltens_rakning(sida("eleven", 10))
    assert "10 kapitel" in str(e.value)

def test_ratt_siffra_slapper_igenom():
    assert build.gate_hjaltens_rakning(sida("twelve", 12)) == 12

def test_talord_utanfor_ordboken_stoppar():
    with pytest.raises(SystemExit):
        build.gate_hjaltens_rakning(sida("nine", 9))
