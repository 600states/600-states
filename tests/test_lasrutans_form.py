"""Grind: pastaendet och anteckningen ligger UTANFOR lasrutan.

Den 25 november var lasrutan hogre an verket och de rymdes inte pa en skarm.
Botemedlet var inte en bredare panel - det matte sig sjalvt som samre, bredd
tar hojd ur verket fortare an ur panelen. Botemedlet var att flytta bordan:
.txt och .note ar de ENDA tva element vars hojd beror pa observationen, och de
star nu under verket i stallet for i panelen. Foljden ar en egenskap och inte
ett tal: lasrutans hojd ar storsta = minsta over alla 600 rutor, pa varje
bredd.

Det ar den egenskapen som grindas har, inte pixlarna. En pixelmatning kraver
en webblasare, en viss bredd och ett visst innehall, och sager ingenting pa en
annan maskin. Det har provet laser kallan och kan falla overallt.

TVA RIKTNINGAR, bada maste halla, annars ar provet halvt:
  - .txt, .note och .lock ar INTE attlingar till .readout
  - .idx och .swatch ar DET - kontrollprovet. Utan det skulle ett trasigt
    stackbygge ge nollor som ser ut som ett godkannande.

Och koden maste slaa upp dem dar de ligger: field.js:54-56 anvander
document.querySelector for .txt, .note och .lock, medan .idx, .swatch och dd
slas upp pa ro. Flyttas uppslagningen till ro slutar fliken fungera - men
sidan ser hel ut, och ingen grind sager ifran. Nu gor en.

DODSMATRIS. Sju mutationer, var och en kord ENSAM mot ett byteidentiskt
trad, och var och en faller pa precis ett prov - inte pa flera, vilket vore
tecken pa att proven mater samma sak tva ganger:

  .txt in i <aside class="readout">   -> de_tre_som_vaxer                 1 failed
  .note in i lasrutan                 -> de_tre_som_vaxer                 1 failed
  .lock in i lasrutan                 -> de_tre_som_vaxer                 1 failed
  .swatch UT ur lasrutan              -> kontrollprov_lasrutans_egna_delar 1 failed
  field.js: .txt  pa ro               -> faltkoden                        1 failed
  field.js: .idx  pa document         -> kontrollprov_lasrutans_egna_falt 1 failed
  en andra <p class="txt"> pa sidan   -> ett_enda_element                 1 failed
  omuterat trad                       -> 26 passed

De tva kontrollproven ar inte pynt. Utan dem kan provet inte skilja "ligger
utanfor lasrutan" fran "hittade ingenting alls": ett stackbygge som tappar en
nivaa, eller en regex som inte laser filen, ger nollor som ser ut som ett
godkannande. Mutationen .idx -> document ar bevis for att den andra
riktningen ocksa kan falla.

Skrivet av den andra parten an den som skrev layouten, enligt AGENTS.md.
"""
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
SIDOR = {
    "index.html": ROT / "site" / "index.html",
    "state-2026-315.html": ROT / "site" / "state-2026-315.html",
}
FALTKOD = ROT / "site" / "field.js"

# Tomma element far aldrig pa stacken. Utan detta blir <img> i noscript en
# oppen nivaa och allt efter den rapporteras som attling till fel element.
TOMMA = {"area", "base", "br", "col", "embed", "hr", "img", "input",
         "link", "meta", "param", "source", "track", "wbr"}

# Klasserna som ska ligga utanfor lasrutan, och de som ska ligga i den.
UTANFOR = ("txt", "note", "lock")
INUTI = ("idx", "swatch")


class Slakttrad(HTMLParser):
    """Samlar, for varje klass vi fragar om, om den har .readout over sig.

    Resultatet ar en lista per klass - inte ett ja/nej - sa att ett andra
    element med samma klass syns i stallet for att doljas av det forsta.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.traffar = {}

    def handle_starttag(self, tag, attrs):
        klasser = dict(attrs).get("class", "").split()
        if tag not in TOMMA:
            self.stack.append(klasser)
        else:
            klasser_tom = klasser
            self._registrera(klasser_tom, self.stack)
            return
        self._registrera(klasser, self.stack[:-1])

    def handle_startendtag(self, tag, attrs):
        self._registrera(dict(attrs).get("class", "").split(), self.stack)

    def _registrera(self, klasser, forfader):
        i_lasrutan = any("readout" in niva for niva in forfader)
        for k in klasser:
            self.traffar.setdefault(k, []).append(i_lasrutan)

    def handle_endtag(self, tag):
        if tag in TOMMA:
            return
        # Stang narmaste oppna nivaa. Taggnamnet behovs inte: dokumentet
        # stanger sina taggar, och kontrollprovet faller om det slutar galla.
        if self.stack:
            self.stack.pop()


def las(sida):
    p = Slakttrad()
    p.feed(SIDOR[sida].read_text(encoding="utf-8"))
    return p.traffar


TRAD = {namn: las(namn) for namn in SIDOR}


@pytest.mark.parametrize("sida", sorted(SIDOR))
@pytest.mark.parametrize("klass", UTANFOR)
def test_de_tre_som_vaxer_ligger_utanfor_lasrutan(sida, klass):
    """.txt, .note och .lock ar de enda vars hojd beror pa observationen."""
    traffar = TRAD[sida].get(klass)
    assert traffar, f".{klass} finns inte pa {sida} - provet mater ingenting"
    assert not any(traffar), (
        f".{klass} ligger i .readout pa {sida}. Da beror panelens hojd pa "
        f"observationens langd igen, och lasrutan kan bli hogre an verket.")


@pytest.mark.parametrize("sida", sorted(SIDOR))
@pytest.mark.parametrize("klass", INUTI)
def test_kontrollprov_lasrutans_egna_delar_ligger_i_den(sida, klass):
    """Utan detta kan provet ovanfor inte skilja 'utanfor' fran 'ser inget'."""
    traffar = TRAD[sida].get(klass)
    assert traffar, f".{klass} finns inte pa {sida}"
    assert all(traffar), (
        f".{klass} ligger utanfor .readout pa {sida}. Antingen har panelen "
        f"tagits isar, eller sa laser provet inte slakttradet ratt - och da "
        f"ar nollorna ovanfor inte mata nollor.")


@pytest.mark.parametrize("sida", sorted(SIDOR))
@pytest.mark.parametrize("klass", UTANFOR + INUTI + ("readout",))
def test_ett_enda_element_per_klass(sida, klass):
    """field.js tar det FORSTA traffen. Tva element gor uppslaget till en gissning."""
    traffar = TRAD[sida].get(klass, [])
    assert len(traffar) == 1, (
        f"{len(traffar)} element med .{klass} pa {sida}. querySelector tar "
        f"det forsta, och vilket det ar beror pa dokumentordningen.")


@pytest.mark.parametrize("klass", UTANFOR)
def test_faltkoden_slar_upp_dem_i_DOKUMENTET(klass):
    """Ligger de utanfor panelen maste de slas upp utanfor den ocksa."""
    kod = FALTKOD.read_text(encoding="utf-8")
    pa_dokumentet = re.search(
        r"document\s*\.\s*querySelector\s*\(\s*['\"]\." + klass + r"['\"]", kod)
    pa_lasrutan = re.search(
        r"\bro\s*\.\s*querySelector(?:All)?\s*\(\s*['\"]\." + klass + r"['\"]", kod)
    assert pa_dokumentet, (
        f"field.js slaar inte upp .{klass} pa document. Den ligger utanfor "
        f"#readout i bada sidorna, sa ett uppslag i panelen hittar den inte.")
    assert not pa_lasrutan, (
        f"field.js slaar upp .{klass} pa #readout. Elementet ligger utanfor "
        f"panelen - uppslaget ger null och faltet slutar skriva i det, utan "
        f"att sidan ser trasig ut.")


def test_kontrollprov_lasrutans_egna_falt_slas_upp_pa_panelen():
    """Samma prov at andra hallet: dd och .idx SKA slas upp pa ro."""
    kod = FALTKOD.read_text(encoding="utf-8")
    for uttryck in (r"\bro\s*\.\s*querySelector\s*\(\s*['\"]\.idx['\"]",
                    r"\bro\s*\.\s*querySelectorAll\s*\(\s*['\"]dd['\"]"):
        assert re.search(uttryck, kod), (
            "field.js slaar inte upp lasrutans egna falt pa ro. Antingen har "
            "uppslagningen byggts om, eller sa laser regexarna ovanfor inte "
            "filen - och da betyder deras nollor ingenting.")
