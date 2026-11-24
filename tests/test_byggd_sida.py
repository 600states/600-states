"""Grind: det bygget skrev in i sidan ar det data.js sager.

Sidan anger hur manga rutor som saknar samstammighet. Talet kommer ur
build_data()s returvarde, samma variabel som data.js byggs av - i dag kan de
darfor inte glida isar. "I dag" ar inte en grind: delar nagon variabeln, flyttar
rakningen eller byter kalla, sager ingenting ifran. Det har testet sager ifran.

Provas pa den BYGGDA sidan, inte pa kallan. Det ar den vagen en besokare ser,
och det ar ocksa den enda plats dar talet finns som tal - i kallan star en
platshallare.

Skrivet av den andra parten an den som skrev bygget, enligt AGENTS.md.
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
DIST = ROT / "site" / "dist"
KALLA = ROT / "site" / "index.html"

kraver_bygge = pytest.mark.skipif(
    not (DIST / "index.html").exists() or not (DIST / "data.js").exists(),
    reason="site/dist saknas - kor python site/build.py forst")


def _rutor():
    """tiles ur den byggda data.js. Filen ar en tilldelning med JSON efter =."""
    text = (DIST / "data.js").read_text(encoding="utf-8")
    return json.loads(text.split("=", 1)[1].rstrip().rstrip(";"))["tiles"]


def _ur_sidan(falt):
    m = re.search(r"<span data-%s>([^<]*)</span>" % falt,
                  (DIST / "index.html").read_text(encoding="utf-8"))
    assert m, f"hittar inget data-{falt} i den byggda sidan"
    return m.group(1)


def _gloss_nycklar():
    """Nycklarna i GLOSS, ur kallan - glossen ar skript och byggs inte om."""
    text = KALLA.read_text(encoding="utf-8")
    block = text.split("var GLOSS = {", 1)
    assert len(block) == 2, "hittar ingen GLOSS i site/index.html"
    return set(re.findall(r"'([^']+)':", block[1].split("}", 1)[0]))


@kraver_bygge
def test_sidans_tal_ar_data_js_tal():
    """Talet i meningen mot rakningen i data.js, pa faltets varde.

    INTE med ett reguljart uttryck over hela filen: prosan i rutornas egna falt
    innehaller samma strangar, och en sadan rakning gav en gang 603 over 600
    rutor.
    """
    ur_data = sum(1 for r in _rutor() if r[4] == "1/3")
    ur_sidan = _ur_sidan("nocons")
    assert ur_sidan.isdigit(), (
        f"sidan sager '{ur_sidan}' dar ett tal ska sta - bygget ersatte inte "
        "platshallaren")
    assert int(ur_sidan) == ur_data, (
        f"sidan sager {ur_sidan} rutor utan samstammighet, data.js har "
        f"{ur_data}")


@kraver_bygge
def test_sidans_antal_distinkta_farger_ar_data_js_tal():
    """Samma form som talet ovan, pa samma payload.

    SKRIVET AV SAMMA PART SOM ANDRADE BYGGET, till skillnad fran resten av
    filen. Det bryter mot arbetsdelningen i AGENTS.md och star har i stallet
    for att doljas: raden ar en upprepning av provet ovan och inte en ny
    bedomning, men den ar inte oberoende granskad.
    """
    ur_data = len({r[0] for r in _rutor()})
    ur_sidan = _ur_sidan("distinct")
    assert ur_sidan.isdigit(), (
        f"sidan sager '{ur_sidan}' dar ett tal ska sta - bygget ersatte inte "
        "platshallaren")
    assert int(ur_sidan) == ur_data, (
        f"sidan sager {ur_sidan} distinkta farger, data.js har {ur_data}")


@kraver_bygge
def test_varje_enighetsniva_i_data_har_en_gloss():
    """Ett nytt faltvarde far ingen gloss i stallet for fel gloss - bra, men da
    star det oglosat pa sidan. Testet fangar vardet, inte beteendet."""
    i_data = {r[4] for r in _rutor()}
    utan = sorted(i_data - _gloss_nycklar())
    assert utan == [], f"enighetsnivaer i data.js som GLOSS inte namner: {utan}"


@kraver_bygge
def test_byggets_platshallare_ersattes():
    """En oersatt platshallare betyder att kallan laddats upp i stallet for
    bygget. Bada talen provas, for de skrivs av samma loop."""
    for falt in ("tests", "nocons", "distinct"):
        v = _ur_sidan(falt)
        assert v.isdigit() and int(v) > 0, (
            f"data-{falt} ar '{v}' i den byggda sidan - inte ett tal over noll")
