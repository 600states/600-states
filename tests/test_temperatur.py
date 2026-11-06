"""Temperaturen har en enda definition, och journalen far inte ljuga om den.

Temperaturen stod osatt till 2026-11-06 med noten "ej satt; leverantorens
standardvarde galler; omatt". Noten var HARDKODAD bredvid ett hardkodat null.
Satte nagon temperaturen i anropet skulle journalen fortsatt pasta att den var
osatt - och ett manifest som pastar en parameter koden inte anvande ar precis
FYND 004 en gang till.

Det har testet gor tre pastaenden till grindar:
  1. driftens anrop skickar INTE parametern sa lange den ar osatt
  2. ett satt varde gar oforandrat till API:et
  3. journalens falt och not kommer ur vardet, inte ur en strang i koden
"""
import inspect, sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT / "tools"))
import classify
import calibrate


class _Stream:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self): return "meddelande"

class _Meddelanden:
    def __init__(self): self.kwargs = None
    def stream(self, **kw):
        self.kwargs = kw
        return _Stream()

class _Klient:
    def __init__(self): self.messages = _Meddelanden()


def _anrop(temperature):
    k = _Klient()
    classify.call(k, "claude-opus-5", "prompt", [{"observation_id": "OBS-1"}],
                  temperature)
    return k.messages.kwargs


def test_osatt_temperatur_skickar_ingen_parameter():
    """None ar inte 1.0. Att utelamna parametern ar vad instrumentet gjort i
    varje korning hittills; att skicka ett varde vore ett pastaende om vad
    leverantorens standardvarde ar."""
    assert "temperature" not in _anrop(None)


def test_satt_temperatur_gar_oforandrad_till_anropet():
    for v in (0.0, 0.3, 1.0):
        assert _anrop(v)["temperature"] == v


def test_driften_skickar_den_enda_definitionen():
    """Inte ett eget varde pa anropsstallet - samma varde som journalen skriver."""
    src = inspect.getsource(classify.run)
    assert "call(client, model, prompt, items, TEMPERATUR)" in src
    assert '"temperature": TEMPERATUR' in src
    assert '"temperature_note": temperatur_not()' in src


def test_noten_harleds_ur_vardet():
    assert classify.TEMPERATUR is None, "temperaturen ar beslutad - uppdatera FYND/journal"
    assert "omatt" in classify.temperatur_not()
    gammal = classify.TEMPERATUR
    try:
        classify.TEMPERATUR = 0.0
        assert "omatt" not in classify.temperatur_not()
    finally:
        classify.TEMPERATUR = gammal


def test_matningarna_skriver_inte_over_varandra():
    """Tva temperaturer ar tva matningar. Delar de nyckel forsvinner den
    forsta tyst, vilket ar hur matningen for sonnet och haiku gick forlorad."""
    nycklar = {calibrate.etikett("claude-opus-5", t) for t in (None, 0.0, 1.0)}
    assert len(nycklar) == 3
    assert calibrate.etikett("claude-opus-5", None) == "claude-opus-5"


def test_default_betyder_utelamnad_inte_ett():
    assert calibrate.temp_av("default") is None
    assert calibrate.temp_av("0") == 0.0
    assert calibrate.temp_av("1") == 1.0
