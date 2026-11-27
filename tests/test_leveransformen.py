"""Grind: ett seriedygn far inte klassificeras i femtioform. FYND 025.

BAKGRUNDEN AR ETT HAVERI, inte en farhaga. Natten till 27 november foll
batch 07 i 2026/329 i alla tre passen, i alla tre ronderna, med identiskt fel
i atta forsok av atta: modellen klassificerade rubriken pa position 35 under
position 49:s ID. I enformen kan det felet inte uppsta - identiteten kommer ur
begaran, inte ur en rad modellen ska halla reda pa. Felklassen ar alltsa en
foljd av formen.

Och formen stod pa tva stallen som sa olika saker. PARAMETER_REGISTER 1.11
bokforde en observation per begaran som beslutad sedan 2026-11-10;
src/classify.py hade femtio per anrop som standard och kallade den beslutade
formen "ej beslutad leveransform" i korjournalen. I sjutton dagar har ett FRYST
krav - row_independence_required i exekveringsspecen - berott pa att nagon kom
ihag en flagga.

GRINDEN AR ASYMMETRISK, och det ar avsiktligt:

    seriedygn, femtioform       -> FALLER
    seriedygn, enform           -> gar igenom
    fore SERIESTART, femtioform -> gar igenom, noteras i journalen
    fore SERIESTART, enform     -> gar igenom

Inkorningsdygn blir aldrig ett av de 600, sa de far koras i vilken form som
helst sa lange journalen sager vilken. Ett seriedygn kors en gang, och ett
dygn kort i fel form uppfyller inte ett fryst krav - det gar inte att rata i
efterhand. Darfor faller grinden i stallet for att varna.

--LIVE AR FEMTIOFORM UTAN ATT HETA DET. Direktvagen skickar hela batchar i ett
anrop. Hade formen avgjorts av flaggan i stallet for av vad en begaran faktiskt
bar, hade vagen till fel form statt oppen under ett annat namn. Code lade den
klausulen utan att bli ombedd och flaggade den; den provas har.

DODSMATRIS, korda mutationer:
  LEVERANSFORM = FORM_FEMTIO          -> beslutad_form_ar_enformen   FALLER
  grinden: "or not i_serien" bort     -> fore_seriestart_*           FALLER
  grinden: i_serien alltid sann       -> fore_seriestart_*           FALLER
  --live ger inte langre FORM_FEMTIO  -> live_ar_femtioform          FALLER
  FORM_NOT tom for avvikelsen         -> (test_en_i_taget)           FALLER

Skrivet av den andra parten an den som byggde grinden, enligt AGENTS.md.
"""
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))
import classify
import gates
import pool_evidence

FORE = "20261130"
START = pool_evidence.SERIESTART
EFTER = "20261202"


# ---------- den beslutade formen ----------

def test_beslutad_form_ar_enformen():
    """PARAMETER_REGISTER 1.11. Star det nagot annat har har koden bytt
    metod utan att registret vet om det."""
    assert classify.LEVERANSFORM == classify.FORM_EN


def test_formen_star_pa_ETT_stalle():
    """FYND 004:s form. Grinden, journalen och anropsbyggandet ska lasa samma
    konstant - inte var sin literal."""
    import re
    kod = (ROT / "src" / "classify.py").read_text(encoding="utf-8")
    # Strangvardena far forekomma dar de DEFINIERAS och i FORM_NOT-nycklarna,
    # aldrig som literal i en jamforelse eller en tilldelning langre ned.
    for namn, varde in (("FORM_EN", classify.FORM_EN),
                        ("FORM_FEMTIO", classify.FORM_FEMTIO)):
        rader = [n for n, r in enumerate(kod.splitlines(), 1)
                 if f'"{varde}"' in r]
        assert len(rader) == 1, (
            f"strangen {varde!r} star pa rad {rader} - den ska bara sta dar "
            f"{namn} definieras, och lasas darifran")


# ---------- grinden, fyra lagen ----------

def test_seriedygn_i_femtioform_FALLER():
    with pytest.raises(gates.GateFailure) as e:
        classify.gate_leveransform(START, classify.FORM_FEMTIO)
    assert "leveransform" in str(e.value).lower()


def test_seriedygn_i_enform_gar_igenom():
    classify.gate_leveransform(START, classify.FORM_EN)


def test_fore_seriestart_i_femtioform_gar_igenom(capsys):
    """Inkorningsdygn blir aldrig ett av de 600. Men journalen ska saga det."""
    classify.gate_leveransform(FORE, classify.FORM_FEMTIO)
    assert "inkorning" in capsys.readouterr().out


def test_fore_seriestart_i_enform_gar_igenom():
    classify.gate_leveransform(FORE, classify.FORM_EN)


def test_efter_seriestart_faller_ocksa():
    """Gransen ar inte bara startdagen."""
    with pytest.raises(gates.GateFailure):
        classify.gate_leveransform(EFTER, classify.FORM_FEMTIO)


def test_gransen_foljer_SERIESTART_och_star_inte_i_grinden(monkeypatch):
    """Flyttas seriestarten ska gransen flytta med."""
    monkeypatch.setattr(pool_evidence, "SERIESTART", "20270115")
    classify.gate_leveransform(EFTER, classify.FORM_FEMTIO)       # nu fore
    with pytest.raises(gates.GateFailure):
        classify.gate_leveransform("20270116", classify.FORM_FEMTIO)


# ---------- --live ar femtioform utan att heta det ----------

def test_live_ar_femtioform_aven_utan_flagga():
    """Formen ar vad en begaran BAR, inte vad den heter.

    Provet kor run() mot ett seriedygn med leverans="direkt" och utan
    femtio-flaggan. Grinden ligger fore batches(), sa inga indatafiler behovs
    och inget betalt anrop sker - faller den, har klausulen gjort sitt."""
    with pytest.raises(gates.GateFailure) as e:
        classify.run(START, dry=True, leverans="direkt")
    assert classify.FORM_FEMTIO in str(e.value), (
        "--live pa ett seriedygn gick inte igenom grinden som femtioform. "
        "Da star vagen till fel form oppen under ett annat namn.")


def test_kontrollprov_batchvagen_pa_samma_dygn_faller_INTE_pa_formen():
    """Utan detta kan provet ovan inte skilja 'live ar femtioform' fran
    'run() faller alltid pa det dygnet'."""
    try:
        classify.run(START, dry=True)
    except gates.GateFailure as e:
        assert classify.FORM_FEMTIO not in str(e.value), (
            "batchvagen foll ocksa pa leveransformen - da mater provet ovan "
            "inte klausulen utan nagot annat")
    except SystemExit:
        pass          # saknade indatafiler, en annan grind - ratt utfall har
