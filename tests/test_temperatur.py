"""Temperaturen finns inte, och en matning far inte radera en annan.

2026-11-06 byggdes kalibreringsbatteriet ut for att mata temperaturen, som
stod som projektets sista osatta parameter. Anropet foll innan det lamnade
maskinen: varken temperature eller top_p finns i API:ets kropp for den har
modellgenerationen. Fragan ar stangd, men inte genom en matning - det fanns
ingenting att mata.

Samma korning avslojade ett andra fel. Morgonens matning av samma modell
skrevs over, bade i resultatfilen och bland rasvaren, trots att filen sedan
tidigare slas samman i stallet for att ersattas. Sammanslagningen skyddade
mot en annan modell, inte mot samma modell en gang till.

Testet laser bada: ingen samplingsparameter nagonstans i anropsvagen, och
ingen nyckel som kan ta en annan matnings plats.
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


def test_anropet_skickar_ingen_samplingsparameter():
    k = _Klient()
    classify.call(k, "claude-opus-5", "prompt", [{"observation_id": "OBS-1"}])
    assert "temperature" not in k.messages.kwargs
    assert "top_p" not in k.messages.kwargs


def test_call_tar_inte_emot_nagot_som_anda_inte_gar_att_skicka():
    """Ett argument som bara kan ge TypeError ar en falla, inte en mojlighet."""
    assert list(inspect.signature(classify.call).parameters) == [
        "client", "model", "prompt", "items"]


def test_korjournalen_sager_vad_som_faktiskt_galler():
    """Faltet star kvar - ett falt som forsvinner ur provenienskedjan laser som
    om fragan aldrig stallts - men noten far inte pasta ett standardvarde som
    ingen kan satta."""
    assert classify.TEMPERATUR is None
    not_ = classify.TEMPERATUR_NOT.lower()
    assert "ingen temperatur" in not_ and "effort" in not_
    assert "omatt" not in not_
    src = inspect.getsource(classify.run)
    assert '"temperature": TEMPERATUR' in src
    assert '"temperature_note": TEMPERATUR_NOT' in src


def test_en_matning_tar_aldrig_en_annans_nyckel():
    upptagna = {"claude-opus-5": {}, "claude-sonnet-5-5": {}}
    assert calibrate.ledig_nyckel("claude-haiku-5-5", upptagna) == "claude-haiku-5-5"
    assert calibrate.ledig_nyckel("claude-opus-5", upptagna) == "claude-opus-5#kor2"
    upptagna["claude-opus-5#kor2"] = {}
    assert calibrate.ledig_nyckel("claude-opus-5", upptagna) == "claude-opus-5#kor3"


def test_rasvaren_bar_korningens_stampel():
    """Utan stampeln skriver nasta korning av samma modell over svaren, och da
    gar varken matningen eller brusgolvet att rakna om."""
    src = inspect.getsource(calibrate.kor)
    assert 'f"{m}_{stampel}_pass{p}.txt"' in src
    assert "stampel = time.strftime" in src
