"""Delad riggning. Sviten ska svara likadant med och utan dataarkivet.

TVA ARKIVLASNINGAR LIGGER MITT I KODVAGAR SOM PROVAS FOR NAGOT ANNAT:

    classify.validate()   laser decimalkravet ur den frysta specen vid VARJE
                          anrop, aven nar testet handlar om sexton nycklar
                          eller om id-matchningen
    leveransvagen         hashar den frysta prompten for att ge ett jobb
                          identitet, aven nar testet handlar om jobbfilen

De tva raderna fallde 35 tester i en klon utan arkivet. Inte for att testerna
behovde arkivet - for att kodvagen rakar rora det pa vagen.

Funktionerna nedan satter bada till kanda varden, I ALLA MILJOER. En svit som
provar en sak har och en annan dar ar ingen kontroll, och ett pinnat varde som
bara galler pa maskinen utan arkiv ar precis det. Att det pinnade decimalkravet
ar specens eget provas separat, av ett test som hoppas over utan arkivet:
test_classify.test_pinnade_decimalkravet_ar_specens.

ETT TEST SOM BEHOVER ARKIVET FOR ATT BETYDA NAGOT HOPPAS OVER, med
kraver_arkiv. Det vattnas inte ur till att prova nagot annat: instrumentgrinden
och kalibreringsgrindens harledning ur specens egna falt sager ingenting alls
mot en pahittad spec.
"""
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))
import classify

# Specens score/intensity/confidence_precision. Talet star har EN gang och
# knyts till den frysta filen av testet som namns ovan.
SPEC_PRECISION = 2

kraver_arkiv = pytest.mark.skipif(
    not classify.SPEC_FILE.exists(),
    reason="dataarkivet saknas - satt STATES_DATA (se README)")


def pinna_specens_decimalkrav(monkeypatch):
    monkeypatch.setattr(classify, "spec_precision", lambda: SPEC_PRECISION)


def pinna_prompten(monkeypatch, tmp_path):
    """En stand-in for den frysta exekveringsprompten.

    Leveransvagen hashar filen for att ge ett jobb identitet. VILKEN fil det ar
    spelar ingen roll for den fragan - bara att hashen ar densamma genom hela
    korningen, vilket ar precis vad testerna provar. Den som vill veta att
    prompten ar ratt fil fragar instrumentgrinden, som kraver arkivet.
    """
    p = tmp_path / "prompt_standin.txt"
    p.write_text("standin for den frysta exekveringsprompten\n", encoding="utf-8")
    monkeypatch.setattr(classify, "PROMPT_FILE", p)
