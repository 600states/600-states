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
    """Att ordet och antalet stammer - INTE vilket tal det rakar vara.

    Testet lag tidigare pa == 10 och foll sa fort ett elfte kapitel skrevs.
    Det var en observation av dagslaget upphojd till regel, samma form som
    bandet 13-15 i kapitel VII pa sidan sjalv. Grinden provar en relation;
    testet ska prova samma relation."""
    import re
    html = io.open(SIDA, encoding="utf-8").read()
    kapitel_pa_sidan = len(re.findall(r'<p class="ch-num">[IVXLC]+</p>', html))
    assert kapitel_pa_sidan >= 1
    assert build.gate_hjaltens_rakning(html) == kapitel_pa_sidan

def test_fel_siffra_stoppar_bygget():
    with pytest.raises(SystemExit) as e:
        build.gate_hjaltens_rakning(sida("eleven", 10))
    assert "10 kapitel" in str(e.value)

def test_ratt_siffra_slapper_igenom():
    assert build.gate_hjaltens_rakning(sida("twelve", 12)) == 12

def test_talord_utanfor_ordboken_stoppar():
    with pytest.raises(SystemExit):
        build.gate_hjaltens_rakning(sida("nine", 9))


# =========================================================================
# EN RAKNING, ETT STALLE  (tillagt for 068829b)
#
# Talordet stod i hjalten OCH i underrubriken, och grinden sag bara hjalten.
# Vid sjutton kapitel hade den ena rattats och den andra blivit kvar: ett
# varde pa tva stallen, FYND 004:s form, den har gangen i grindens egen text.
#
# Grinden ar skriven av den ena parten, testet av den andra.
# =========================================================================

def sida_med(ord_, n, sub=None, meta=None):
    """Sidan plus de tva ovriga stallen dar den beskriver sig sjalv."""
    delar = ['<p class="lead">The instrument has been wrong %s times.</p>' % ord_]
    if sub is not None:
        delar.append('<p class="sub">%s</p>' % sub)
    if meta is not None:
        delar.append('<meta name="description" content="%s">' % meta)
    return "".join(delar) + kapitel(n)


def test_talordet_i_underrubriken_ocksa_stoppar_bygget():
    """DET HAR AR GRINDENS SKAL. Bada meningarna ar sanna, sa claims gate
    slapper igenom dem - det ar rakningens antal stallen som ar felet."""
    with pytest.raises(SystemExit) as e:
        build.gate_hjaltens_rakning(
            sida_med("twelve", 12, sub="There are twelve write-ups here."))
    assert "ETT stalle" in str(e.value)


def test_talordet_i_meta_beskrivningen_ocksa_stoppar_bygget():
    """Det tredje stallet. Det hittades forst nar grinden byggdes - alltsa
    efter att tva stallen rattats for hand, vilket ar hela argumentet."""
    with pytest.raises(SystemExit) as e:
        build.gate_hjaltens_rakning(
            sida_med("twelve", 12, meta="Twelve method errors found."))
    assert "ETT stalle" in str(e.value)


def test_grinden_bryr_sig_inte_om_versaler():
    """"Twelve" i en meta-beskrivning ar samma pastaende som "twelve"."""
    with pytest.raises(SystemExit):
        build.gate_hjaltens_rakning(
            sida_med("twelve", 12, sub="TWELVE write-ups."))


def test_ordet_i_kapiteltexten_raknas_inte():
    """INTE LATHET, UTAN AVSIKT. Sidan namner sexton kanslor och sexton
    hextecken, och innehallsforteckningen bar en kapitelrubrik med samma ord.
    En rakning over hela filen hade fallit pa sitt eget innehall - och da hade
    grinden varit omojlig att uppfylla i stallet for att skydda nagot."""
    html = sida_med("twelve", 12) + (
        "<p>Twelve emotional states. Twelve hex characters. "
        "Twelve values out of a hundred and one.</p>")
    assert build.gate_hjaltens_rakning(html) == 12


def test_ett_langre_ord_som_innehaller_talordet_raknas_inte():
    """Gransen gar vid hela ord. "Twelvefold" ar inte en andra rakning."""
    html = sida_med("twelve", 12, sub="A twelvefold increase in nothing.")
    assert build.gate_hjaltens_rakning(html) == 12


def test_sidan_utan_underrubrik_och_meta_passerar():
    """Bada ar valfria. Saknas de ska grinden rakna hjalten ensam, inte falla
    pa att den inte hittade dem."""
    assert build.gate_hjaltens_rakning(sida_med("twelve", 12)) == 12


def test_den_riktiga_sidan_har_talordet_pa_exakt_ett_stalle():
    """Mot den levererade filen, inte mot en attrapp."""
    import re
    html = io.open(SIDA, encoding="utf-8").read()
    n = build.gate_hjaltens_rakning(html)
    assert n >= 1
    ordbok = {v: k for k, v in build.TALORD.items()}
    ordet = ordbok[n]
    omsig = []
    for m in (re.search(r'<p class="lead">(.*?)</p>', html, re.S),
              re.search(r'<p class="sub">(.*?)</p>', html, re.S),
              re.search(r'<meta name="description" content="(.*?)">', html, re.S)):
        if m:
            omsig.append(m.group(1))
    helt = r"(?<![A-Za-z])%s(?![A-Za-z])" % ordet
    assert sum(len(re.findall(helt, t, re.I)) for t in omsig) == 1
