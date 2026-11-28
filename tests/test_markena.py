"""Markena: vilken fil en lasare faktiskt far, och om den har horn.

A52, 2026-11-28. Agaren sag sajtens ikon i Firefox startsida som en
grusboll med SVARTA HORN. Market var ratt - cirkeln ar gjord ur verket och
ska vara grus - men fel fil visades.

Uppmatt:

    favicon.ico           48x48    RGBA   alfa 0-255, cirkeln genomskinlig
    apple-touch-icon.png  180x180  RGB    hornen malade (10,10,11)

Ingen webmanifest, och bara tva ikondeklarationer. Firefox valjer den
STORSTA ikonen for sin ruta, alltsa apple-ikonen - den enda som avsiktligt
har opaka horn. Botemedlet ar inte att andra apple-ikonen, for iOS maskar
alltid mot en ogenomskinlig platta och en genomskinlig apple-ikon ger
svarta horn DAR i stallet. Botemedlet ar att ge webblasarna en stor
genomskinlig PNG att valja i stallet.

TVA PASTAENDEN, OCH DET ANDRA ar lika viktigt som det forsta:

  1. Det finns en stor genomskinlig ikon, och sidorna deklarerar den.
  2. apple-touch-icon.png ar och forblir OPAK. Den ser ut som ett fel och
     ar det inte. Utan det har provet "rattar" nagon den nasta gang
     hornen kommer pa tal, och da ar felet tillbaka pa iOS i stallet.

Proven som laser byggda filer hoppas over utan ett bygge. De som laser
sidornas head gor det aldrig - deklarationen star i kallan.
"""
import re
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
SIDOR = ROT / "site"
DIST = SIDOR / "dist"

STORA = ("icon-192.png", "icon-512.png")
APPLE = "apple-touch-icon.png"


def _sidor():
    return sorted(p for p in SIDOR.glob("*.html"))


def _bild(namn):
    Image = pytest.importorskip("PIL.Image", reason="PIL saknas")
    f = DIST / namn
    if not f.exists():
        pytest.skip("site/dist saknas eller ar inte ombyggt - %s finns inte" % namn)
    return Image.open(f)


# --- 1. sidorna deklarerar en stor genomskinlig ikon -------------------

def test_sidor_finns():
    assert _sidor(), "inga sidor i site/"


def test_varje_sida_deklarerar_de_stora_ikonerna():
    """En deklaration som saknas pa EN sida racker: Firefox valjer per sida,
    och den sidan far apple-ikonen igen. FYND 028:s form."""
    brott = []
    for p in _sidor():
        txt = p.read_text(encoding="utf-8")
        for namn in STORA:
            if namn not in txt:
                brott.append("%s saknar %s" % (p.name, namn))
    assert not brott, ("sidor utan stor genomskinlig ikon - de far "
                       "apple-ikonen med malade horn:\n  " + "\n  ".join(brott))


def test_deklarationerna_namner_sin_storlek_och_sin_typ():
    """Utan sizes och type maste webblasaren hamta filen for att veta vad
    den ar. Da kan den lika garna valja apple-ikonen, som sager bada."""
    for p in _sidor():
        txt = p.read_text(encoding="utf-8")
        for namn, storlek in zip(STORA, ("192x192", "512x512")):
            rad = re.search(r'<link[^>]*href="/%s"[^>]*>' % re.escape(namn), txt)
            assert rad, "%s: ingen link-rad for %s" % (p.name, namn)
            r = rad.group(0)
            assert 'rel="icon"' in r, "%s: %s ar inte rel=icon: %s" % (p.name, namn, r)
            assert storlek in r, "%s: %s saknar sizes=%s" % (p.name, namn, storlek)
            assert "image/png" in r, "%s: %s saknar type=image/png" % (p.name, namn)


# --- 2. de stora ikonerna ar genomskinliga -----------------------------

@pytest.mark.parametrize("namn,sida", [("icon-192.png", 192), ("icon-512.png", 512)])
def test_de_stora_ikonerna_ar_genomskinliga(namn, sida):
    im = _bild(namn)
    assert im.size == (sida, sida), "%s ar %s" % (namn, im.size)
    assert im.mode == "RGBA", "%s ar %s - utan alfakanal blir hornen malade" % (namn, im.mode)
    a = im.getchannel("A")
    assert a.getextrema() == (0, 255), (
        "%s har alfa %s - en helt opak eller helt genomskinlig ikon ar inte "
        "en cirkel" % (namn, a.getextrema()))
    assert a.getpixel((2, 2)) == 0, "%s: hornet ar inte genomskinligt" % namn
    assert a.getpixel((sida // 2, sida // 2)) == 255, "%s: mitten ar genomskinlig" % namn


def test_den_lilla_ikonen_ar_ororad():
    """favicon.ico var ratt hela tiden. Den provas sa att en rattelse av de
    stora inte raker med den."""
    im = _bild("favicon.ico")
    assert im.convert("RGBA").getchannel("A").getextrema() == (0, 255)


# --- 3. apple-ikonen SKA vara opak -------------------------------------

def test_apple_ikonen_ar_och_forblir_opak():
    """DET HAR AR INGET FEL. iOS lagger alltid ikonen mot en ogenomskinlig
    platta och maskar till en rundad kvadrat; en genomskinlig apple-ikon
    ger svarta horn DAR i stallet. Provet star emot nasta person som ser
    (10,10,11) i ett horn och tror sig hitta buggen igen."""
    im = _bild(APPLE)
    assert im.mode == "RGB", (
        "%s har alfakanal. Den ska vara opak - skalet star i build_favicon "
        "och i det har provets docstring" % APPLE)
    assert im.getpixel((2, 2)) == (10, 10, 11), (
        "%s: hornet ar %s. Det ska vara sidans egen bakgrund, inte systemets "
        "val" % (APPLE, im.getpixel((2, 2))))


# --- att matningarna kan falla -----------------------------------------

def test_matningen_kan_falla():
    Image = pytest.importorskip("PIL.Image", reason="PIL saknas")
    opak = Image.new("RGB", (8, 8), (10, 10, 11))
    assert opak.mode == "RGB"
    med_alfa = Image.new("RGBA", (8, 8), (1, 2, 3, 0))
    assert med_alfa.getchannel("A").getextrema() == (0, 0)   # inte (0,255)
    med_alfa.putpixel((4, 4), (1, 2, 3, 255))
    assert med_alfa.getchannel("A").getextrema() == (0, 255)
