"""Claims gate i kod: den tillbakadragna formuleringen far inte sta kvar pa sajten.

MESSAGE_BANK avsnitt 0.1 ar listan over formuleringar som aldrig far anvandas.
Listan har hittills bott i ett dokument, och ETT DOKUMENT KAN INTE FALLA EN
KORNING. Den 2026-11-28 drogs "the series opens on 1 December 2026" tillbaka,
rattelsen gjordes i site/index.html - och samma pastaende stod kvar pa tre
stallen till. Ingenting markte det. Darfor detta test.

SKALET TILL ATT PASTAENDET AR TILLBAKADRAGET: sidan kan inte visa dag ettens
verk den 1 december. step_site grindar pa gate_forankrad_stampel, som kraver
minst en Bitcoin-attestering, och forankringen tog ett dygn i provet. Verket
OBSERVERAS den 1:a och PUBLICERAS den 2:a. "Opens" ar det enda ordet pa sajten
som kan lasas som ett lofte om nagot synligt den dagen.

TVA SATT ATT GOMMA SIG, och bada star i den har filen:

  1. mailto-kroppen ar procentkodad. "series%20opens%20on%201%20December" ar
     osynlig for ett vanligt grep efter "series opens". Den forsta matningen
     den 2026-11-28 missade just den raden.
  2. HTML-entiteter och radbrytningar bryter en mening mitt itu.

Texten normaliseras darfor fore provningen: procentavkodning, entiteter,
gemener, blanksteg hopdragna. Att normaliseringen verkligen behovs provas av
ett eget test langst ner - utan det vore det har ett grep som pastar sig vara
en grind.

VAD TESTET INTE AR: det ar inte hela claims gate. Det provar EN rad ur 0.1,
den som ar en ordagrann formulering och darfor maskinprovbar. Rader som
"sag inte att urvalet sanker bevisgraden" ar pastaenden om varlden och kan
inte provas har. MONSTER nedan vaxer med en rad per tillbakadragen
formulering som ar ett ord, inte ett resonemang.

VARFOR OCKSA site/dist: dist ar det som laddas upp. Kallan kan vara rattad och
dist bara gammalt bygge - da star pastaendet kvar for lasaren. dist ligger
utanfor git och saknas i en farsk klon; da hoppas den delen over.
"""
import html as htmllib
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))

KALLAN = ROT / "site"
DIST = KALLAN / "dist"

# En rad per tillbakadragen formulering ur MESSAGE_BANK 0.1. Skalet star i
# docstringen ovan och i 0.1; har star bara det som kan falla.
MONSTER = (
    ("series opens",
     'MESSAGE_BANK 0.1, 2026-11-28: "the canonical series opens on ..." - '
     'serien BORJAR den 1 december, men ingenting blir synligt da. '
     'Skriv "begins", eller sag "observed".'),
    (r"opens on 1 december",
     'MESSAGE_BANK 0.1, 2026-11-28: samma pastaende, aven i mailto-kroppen. '
     'Skriv "before the first State is observed on 1 December 2026".'),
    (r"\bopens 1 december",
     'MESSAGE_BANK 0.1, 2026-11-28: "Opens 1 December 2026" - skriv "Begins".'),
)


def normalisera(text: str) -> str:
    """Samma mening, oavsett hur den ar kodad i filen.

    Procentkodningen forst: mailto-kroppen ar hela pastaendet, skrivet med
    %20 mellan orden. Sedan entiteterna, sedan gemener och ett blanksteg
    mellan ord. Utan det forsta steget provar det har testet ingenting alls
    for den rad som faktiskt gommde sig.
    """
    return re.sub(r"\s+", " ", htmllib.unescape(unquote(text))).lower()


def brott_i(text: str):
    """Vilka monster som traffar, med sitt skal. Tom lista = ren text."""
    t = normalisera(text)
    return [(m, skal) for m, skal in MONSTER if re.search(m, t)]


def sidor(katalog: Path):
    if not katalog.exists():
        return []
    return sorted(p for p in katalog.glob("*.html"))


def _rapport(sida: Path, trafflista):
    """Vilken rad det star pa - annars far lasaren leta i 800 rader."""
    rader = []
    for nr, rad in enumerate(sida.read_text(encoding="utf-8").splitlines(), 1):
        if brott_i(rad):
            rader.append(nr)
    namn = ", ".join(m for m, _ in trafflista)
    skal = "\n  ".join(skal for _, skal in trafflista)
    return ("%s rad %s: %s\n  %s"
            % (sida.name, rader or "okand", namn, skal))


def test_kallans_sidor_finns():
    """Kontroll mot ett test som provar noll filer och sager gront."""
    assert sidor(KALLAN), "inga html-sidor i site/ - testet provar ingenting"


def test_ingen_tillbakadragen_formulering_i_kallan():
    brott = [_rapport(s, t) for s in sidor(KALLAN) if (t := brott_i(s.read_text(encoding="utf-8")))]
    assert not brott, "tillbakadragen formulering i publik text:\n" + "\n".join(brott)


def test_ingen_tillbakadragen_formulering_i_bygget():
    """dist ar det som laddas upp. Ratt kalla och gammalt bygge ar inte ratt."""
    byggda = sidor(DIST) + sorted(DIST.glob("*/*.html"))
    if not byggda:
        pytest.skip("site/dist saknas - inget bygge att prova")
    brott = [_rapport(s, t) for s in byggda if (t := brott_i(s.read_text(encoding="utf-8")))]
    assert not brott, ("tillbakadragen formulering i BYGGET - kallan kan vara "
                       "rattad utan att bygget ar det. Bygg om: "
                       "python site/build.py\n" + "\n".join(brott))


# --- att grinden kan falla, och inte faller pa fel sak ------------------

def test_procentkodningen_gommer_ingenting():
    """DETTA AR SKALET TILL NORMALISERINGEN. Den forsta matningen 2026-11-28
    missade mailto-raden for att den sag ut sa har."""
    kodad = ("body=Please%20tell%20me%20before%20the%20series%20opens%20"
             "on%201%20December%202026.")
    assert "series opens" not in kodad          # osynlig for ett vanligt grep
    assert brott_i(kodad), "procentkodad text slipper forbi grinden"


def test_entitet_och_radbrytning_gommer_ingenting():
    assert brott_i("the canonical series\n    opens on 1 December 2026")
    assert brott_i("the canonical series&nbsp;opens on 1 December 2026")


def test_grinden_traffar_den_ratta_meningen():
    assert brott_i("It is not a canonical State, and the canonical series "
                   "opens on 1 December 2026.")
    assert brott_i("Opens 1 December 2026")


def test_grinden_faller_inte_pa_nagot_annat():
    """Ordet ar inte forbjudet - pastaendet ar. Alla fyra star pa sajten."""
    for ren in ("Get the opening notice",
                "<b>No flag opens it.</b> Redoing a day requires deleting the "
                "lock file by hand",
                "// already near the opening: stagger these at load",
                "A settled question is not reopened by asking",
                "the first State, 2026/335, is observed on 1 December 2026",
                "Begins 1 December 2026"):
        assert not brott_i(ren), "falskt positiv: " + ren


def test_varje_monster_kan_falla():
    """Ett monster som ingenting kan traffa ar ett onskemal. Att det finns
    EN strang som faller for varje rad i MONSTER provas har, sa att en
    framtida rad inte kan laggas till som ren dekoration."""
    exempel = {"series opens": "the canonical series opens on 1 December",
               r"opens on 1 december": "it opens on 1 December 2026",
               r"\bopens 1 december": "Opens 1 December 2026"}
    assert set(exempel) == {m for m, _ in MONSTER}, (
        "MONSTER och exempellistan har glidit isar - varje monster ska ha "
        "en strang som visar att det kan falla")
    for m, strang in exempel.items():
        assert re.search(m, normalisera(strang)), "monstret traffar inget: " + m
