"""Fyra pastaenden om de publicerade sidorna, provade av den andra parten.

A48 OCH DESS TRE GRANNAR, alla ur en genomgang i webblasare 2026-11-28:

  1. Hjalten visade tva pilotverk utan ett ord om vad de ar. MESSAGE_BANK 0.2
     heter "The pilot / v3.0 distinction is public, not hidden", och
     upplysningen stod 300 rader ner och handlade om en annan bild.
  2. Bokavsnittet lag FORE verket pa 315-sidan. Verket ar tinget, boken ar
     dess dokument.
  3. Kapitel XVII namngav verket med enbart sitt datum. Identiteten ar
     arkivets nyckel och star i manifestet, i filnamnet och i kolofonen.
  4. Reservsiffran 26 stod kvar i hjaltens nedrakning. Samma fel som
     untilBig hade - en rattelse som raknade forekomster i EN fil, FYND 028.

REGELN AR SKRIVEN PA FORMEN, INTE PA RADEN. Testet letar inte efter den
mening Code skrev; det provar att VARJE stalle som visar ett pilotverk sager
vad verket ar. En regel som bara tacker de tva bilder nagon rakade titta pa
ar inte en regel, och det var precis sa A48 uppstod.

Pilotverken ar STATE_001-004, byggda i september, dygnen 1-4 januari 2026.
Projektet kallar dem ogiltiga och ska kora om dem. De far visas - de visar
formen - men aldrig utan att sidan sager vad de ar.
"""
import re
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
SIDOR = ROT / "site"

PILOTBILD = re.compile(r'src="img/state_00[1-4]\.png"')
DISTINKTIONEN = re.compile(r"calibration|pilot", re.I)


def _sida(namn):
    p = SIDOR / namn
    if not p.exists():
        pytest.skip("saknas: " + namn)
    return p.read_text(encoding="utf-8")


def _regioner(txt):
    """Sidan delad pa sektions- och headerstart. En bildtext hor till den
    region bilden star i - star den langre bort ar den inte en bildtext."""
    pos = [m.start() for m in re.finditer(r"<(section|header)\b", txt)] + [len(txt)]
    return [(txt[:pos[i]].count("\n") + 1, txt[pos[i]:pos[i + 1]])
            for i in range(len(pos) - 1)]


def _alla_sidor():
    return sorted(p.name for p in SIDOR.glob("*.html"))


# --- 1. pilotdistinktionen star dar verket visas -----------------------

def test_sidor_finns_att_prova():
    assert _alla_sidor(), "inga sidor i site/ - testet provar ingenting"


def test_varje_region_som_visar_ett_pilotverk_sager_vad_det_ar():
    """MESSAGE_BANK 0.2: distinktionen ar publik, inte dold. Den ska sta dar
    verket visas - inte i ett annat avsnitt pa samma sida."""
    brott = []
    for namn in _alla_sidor():
        for rad, region in _regioner(_sida(namn)):
            if PILOTBILD.search(region) and not DISTINKTIONEN.search(region):
                brott.append("%s, region fran rad %d: visar %d pilotverk utan att "
                             "namna calibration eller pilot"
                             % (namn, rad, len(PILOTBILD.findall(region))))
    assert not brott, ("pilotverk visas utan distinktion:\n  " + "\n  ".join(brott))


def test_ingen_pilotbilds_alt_text_pastar_att_den_ar_ett_State():
    """TVA REGLER, OCH DE AR INTE SAMMA.

    Regionen bar DISTINKTIONEN - provet ovan. Alt-texten bar ett strangare
    och snavare krav: den far inte PASTA nagot osant. Den behover inte
    upprepa distinktionen, for en lasare som hor alt-texten hor ocksa
    regionens text.

    Skillnaden ar matt. Fyra alt-texter i showcase lyder "Rendered field of
    600 colours, 1 January 2026" - de pastar ingenting falskt och far sta.
    En lyder "A rendered 600 STATES field" om ett pilotverk, och den ar
    osann: bilden ar inget State och blir aldrig ett.

    Ett pastaende om medlemskap i alt-text kraver darfor distinktionen i
    samma strang."""
    img = re.compile(r"<img[^>]*>")
    pastar = re.compile(r"600 STATES|\ba State\b|\bStates\b", re.I)
    brott = []
    for namn in _alla_sidor():
        for tagg in img.findall(_sida(namn)):
            if not PILOTBILD.search(tagg):
                continue
            alt = re.search(r'alt="([^"]*)"', tagg)
            assert alt, "%s: pilotbild utan alt-text" % namn
            t = alt.group(1)
            if pastar.search(t) and not DISTINKTIONEN.search(t):
                brott.append("%s: %s" % (namn, t[:90]))
    assert not brott, ("pilotbild vars alt-text pastar att den ar ett State:\n  "
                       + "\n  ".join(brott))


# --- 2. verket fore boken ---------------------------------------------

def test_verket_star_fore_boken_pa_315_sidan():
    txt = _sida("state-2026-315.html")
    rubriker = re.findall(r"<h2[^>]*>(.*?)</h2>", txt, re.S)
    assert "The work" in rubriker and "The book" in rubriker, rubriker
    assert rubriker.index("The work") < rubriker.index("The book"), (
        "boken star fore verket. Verket ar tinget, boken ar dess dokument: %s"
        % rubriker)


# --- 3. identiteten, inte bara datumet ---------------------------------

def test_lanken_till_verket_bar_dess_identitet():
    """Datumet ensamt ar inte fel, det ar ofullstandigt. Identiteten ar
    arkivets nyckel och star i manifestet, filnamnet och kolofonen."""
    brott = []
    for namn in _alla_sidor():
        txt = _sida(namn)
        for m in re.finditer(r'href="/state-2026-315\.html"', txt):
            omkring = txt[max(0, m.start() - 400):m.end() + 400]
            if "2026/315" not in omkring:
                brott.append("%s rad %d: lanken till verket namner bara datumet"
                             % (namn, txt[:m.start()].count("\n") + 1))
    assert not brott, "\n  ".join(brott)


# --- 4. inga gamla reservsiffror ---------------------------------------

def test_ingen_reservsiffra_i_nedrakningarna():
    """Talet satts av JS. Star en siffra kvar i kallan ser en lasare utan JS
    ett tal som var sant nagon annan dag. untilBig rattades 2026-11-28 och
    countdown missades - samma fil, samma fel, FYND 028."""
    txt = _sida("index.html")
    brott = []
    for id_ in ("countdown", "untilBig"):
        m = re.search(r'id="%s"[^>]*>(.*?)<' % id_, txt, re.S)
        assert m, "hittar inte " + id_
        if re.search(r"\d", m.group(1)):
            brott.append("%s bar %r" % (id_, m.group(1).strip()))
    assert not brott, ("reservsiffra kvar i kallan: " + ", ".join(brott)
                       + " - en lasare utan JS far ett tal fran en annan dag")


def test_det_fardiga_talet_star_kvar_och_sager_samma_sak_pa_bada_stallen():
    """334 ar INGEN reserv - det ar fardigt och far inte strykas med de andra.
    Attributet och texten maste dock saga samma sak."""
    m = re.search(r'data-to="(\d+)"[^>]*>(\d+)<', _sida("index.html"))
    assert m, "talet med data-to hittas inte"
    assert m.group(1) == m.group(2), (
        "data-to=%s men texten sager %s - tva varden for samma tal"
        % (m.group(1), m.group(2)))


# --- att matningarna kan falla -----------------------------------------

def test_matningarna_kan_falla():
    assert PILOTBILD.search('<img src="img/state_003.png" alt="x">')
    assert not PILOTBILD.search('<img src="img/state_2026_315.png" alt="x">')
    assert DISTINKTIONEN.search("A calibration work from the pilot series")
    assert not DISTINKTIONEN.search("A rendered 600 STATES field")
    pastar = re.compile(r"600 STATES|\ba State\b|\bStates\b", re.I)
    assert pastar.search("A rendered 600 STATES field")
    assert not pastar.search("Rendered field of 600 colours, 1 January 2026.")
    assert pastar.search("A calibration work from the pilot series, not a State: x")
    assert len(_regioner("<header>a</header><section>b</section>")) == 2
