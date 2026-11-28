"""Revisionen svarar pa det arkiv den fick, inte pa standardarkivets fraga.

audit(day, data=DATA) tar arkivet som parameter. Varje lasning i funktionen
gar genom den parametern - utom en:

    p = DATA / "07_EVIDENCE" / "pool_titles.jsonl"

Det ar modulens globala DATA, inte funktionens data. Reviderar man ett dygn i
ett annat arkiv - ett provarkiv, en kopia, en granskares egen klon - lases
bevisposterna ur STANDARDARKIVET, och kontroll 11 ("varje url har en
bevispost") svarar pa en fraga om fel arkiv. Den kan bli gron for att en HELT
ANNAN dags bevis rakar ligga dar, och rod for att de inte gor det.

Hittat av Code 2026-11-28 under A42-matningen. Testet skrivet av den andra
parten.

VARFOR INGET VANLIGT TEST HADE FANGAT DEN: sviten kor mot standardarkivet.
Da ar DATA och data samma sokvag, och raden ar osynlig. Felet syns forst nar
de tva skiljer sig, vilket bara handen gor. Darfor provas KODEN, inte ett
utfall: inuti audit() far namnet DATA inte lasas alls.

FILEN BAR OCKSA A42 (langst ner): revisionen ska rapportera pa allt den kan
och namnge vad den inte kunde, i stallet for att do pa forsta saknade filen.

Att prova koden i stallet for utfallet ar ett undantag och ska forbli det.
Skalet star har: utfallsvagen kraver ett helt riggat dygn i ett andra arkiv -
fyra manifest, en batchkatalog och en bevispool - och ett test som bygger sa
mycket provar till slut riggningen och inte raden.
"""
import ast
import os
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))

KALLAN = ROT / "src" / "audit_state.py"


def _audit_noden():
    trad = ast.parse(KALLAN.read_text(encoding="utf-8"))
    for n in trad.body:
        if isinstance(n, ast.FunctionDef) and n.name == "audit":
            return n
    raise AssertionError("hittar ingen funktion audit() i audit_state.py")


def test_audit_tar_arkivet_som_parameter():
    """Kontroll mot ett test som provar en funktion som inte langre finns."""
    n = _audit_noden()
    namn = [a.arg for a in n.args.args]
    assert namn[:2] == ["day", "data"], namn


def test_revisionen_laser_inte_det_globala_arkivet():
    rader = sorted({x.lineno for sats in _audit_noden().body
                    for x in ast.walk(sats)
                    if isinstance(x, ast.Name) and x.id == "DATA"
                    and isinstance(x.ctx, ast.Load)})
    text = KALLAN.read_text(encoding="utf-8").splitlines()
    assert not rader, (
        "audit() laser modulens globala DATA i stallet for sin egen "
        "data-parameter:\n  "
        + "\n  ".join("rad %d: %s" % (r, text[r - 1].strip()) for r in rader))


def test_grinden_kan_falla():
    """Att matningen verkligen ser raden. Samma AST-vag, pa en egen kalla."""
    trad = ast.parse("DATA = 1\n"
                     "def audit(day, data=DATA):\n"
                     "    p = DATA / 'x'\n"
                     "    q = data / 'y'\n"
                     "    return p, q\n")
    fn = [n for n in trad.body if isinstance(n, ast.FunctionDef)][0]
    rader = [x.lineno for sats in fn.body for x in ast.walk(sats)
             if isinstance(x, ast.Name) and x.id == "DATA" and isinstance(x.ctx, ast.Load)]
    # KROPPEN, inte signaturen. data=DATA i parameterlistan ar INTE felet -
    # det ar ratt standardvarde. Felet ar en lasning inuti funktionen. Den
    # forsta versionen av det har testet gick pa hela funktionsnoden och
    # raknade default-vardet som ett brott; det hade stannat rott aven efter
    # en riktig rattelse.
    assert rader == [3], rader


# ======================================================================
# A42 - revisionen rapporterar pa allt den kan
#
# Revisionen dog forut pa forsta saknade filen, innan en enda kontroll
# skrivits ut. Uppmatt pa 2026/330: en saknad site_2026_330.json tog med sig
# de arton andra, dar ibland den enda kontroll som sager att 600 av 600
# farger reproducerar ur det frysta protokollet - och den laser bara
# fargmanifestet.
#
# DET SOM PROVAS HAR AR NAMNAREN. En revision som stallde fjorton kontroller
# och skrev ALLT STAMMER gor siffran NITTON osann, och den siffran star i
# publik text (site/labs.html). Darfor: antalet rapporterade kontroller maste
# vara nitton aven nar ingenting gar att lasa.
# ======================================================================

import io
import re
import subprocess
from contextlib import redirect_stdout

import statepaths as sp
import audit_state

DAG = "20261201"
KONTROLLER = 19


def _kor(data):
    """audit() med sin utskrift fangad. Returnerar (tal, utskrift)."""
    bok = io.StringIO()
    with redirect_stdout(bok):
        tal = audit_state.audit(DAG, data=data)
    return tal, bok.getvalue()


def _bara_fargmanifest(tmp_path):
    """Ett arkiv dar EN kalla gar att lasa. Raderna ar avsiktligt trasiga -
    posten handlar om att kontrollen STALLS, inte om att den godkanns."""
    ut = sp.outdir(tmp_path, DAG)
    ut.mkdir(parents=True)
    sp.color_manifest(tmp_path, DAG).write_text(
        "tile_index,hex\n1,#000000\n", encoding="utf-8")
    return tmp_path


def test_tomt_arkiv_ger_nitton_ej_provade(tmp_path):
    """Ingenting gar att lasa - och alla nitton rapporteras anda."""
    (godkanda, fallna, ej_provade), _ = _kor(tmp_path)
    assert (godkanda, fallna, ej_provade) == (0, 0, KONTROLLER)


def test_namnaren_krymper_aldrig(tmp_path):
    """DET HAR AR POSTENS SKAL. 'stallda 0 av 19', aldrig 'stallda 0 av 0'."""
    _, utskrift = _kor(tmp_path)
    m = re.search(r"stallda (\d+) av (\d+), godkanda (\d+), fallna (\d+), "
                  r"ej provade (\d+)", utskrift)
    assert m, "sammanfattningsraden saknas:\n" + utskrift
    stallda, av, godkanda, fallna, ej = (int(x) for x in m.groups())
    assert av == KONTROLLER
    assert stallda == godkanda + fallna
    assert stallda + ej == KONTROLLER


def test_varje_kontroll_namnges_aven_nar_den_inte_kunde_stallas(tmp_path):
    """En utelamnad rad later en revision som provade fjorton se ut som en
    som provade nitton."""
    _, utskrift = _kor(tmp_path)
    assert utskrift.count("EJ PROVAD") == KONTROLLER, utskrift
    for namn in ("hex reproduceras av protokollet", "publisher cap",
                 "sajtens preHash = filen", "varje url har en bevispost"):
        assert namn in utskrift, namn


def test_kontroll_8_stalls_aven_nar_allt_annat_saknas(tmp_path):
    """Posten finns for den har kontrollen. Den laser BARA fargmanifestet och
    ska stallas aven utan sajtfil, pre-manifest, bevispool och PNG."""
    (_, fallna, _), utskrift = _kor(_bara_fargmanifest(tmp_path))
    rad = [r for r in utskrift.splitlines()
           if "hex reproduceras av protokollet" in r]
    assert len(rad) == 1, utskrift
    assert "EJ PROVAD" not in rad[0], rad[0]
    assert fallna >= 1, "kontrollen stalldes men bokfordes inte som fallen"


def test_en_kontroll_som_kastar_faller_i_stallet_for_att_doda_revisionen(tmp_path):
    """Samma fel ett steg senare ar samma fel. Raderna i provarkivet saknar
    de falt kontrollen laser, sa funk() kastar - och det ska bli FEL med
    besked, inte ett stacktrace."""
    (godkanda, fallna, ej_provade), _ = _kor(_bara_fargmanifest(tmp_path))
    assert godkanda + fallna + ej_provade == KONTROLLER


def test_sokvagen_skrivs_aldrig_ut(tmp_path):
    """Rapporten kan citeras. Arkivets sokvag hor inte hemma dar - filnamnet
    sager vilken fil som saknas."""
    _, utskrift = _kor(tmp_path)
    assert str(tmp_path) not in utskrift
    assert sp.GENERATION_DIR not in utskrift
    assert "PRE_EMOTION_MANIFEST" in utskrift, "filnamnet ska namnas"


# --- felkoderna, kord som program ---------------------------------------

def _rc(arkiv):
    r = subprocess.run([sys.executable, str(ROT / "src" / "audit_state.py"), DAG],
                       env={**os.environ, "STATES_DATA": str(arkiv)},
                       capture_output=True, text=True)
    return r.returncode, r.stdout


def test_ej_provad_ger_felkod_2(tmp_path):
    """Noll fallna ar inte samma sak som godkant. Ett dygn dar fjorton
    kontroller stalldes far inte sluta med samma kod som ett dar nitton
    gjorde det."""
    rc, ut = _rc(tmp_path)
    assert rc == 2, ut
    assert "INTE ALLT GICK ATT PROVA" in ut
    assert "ALLT STAMMER" not in ut


def test_fallen_slar_ej_provad(tmp_path):
    """Bada finns: ett kant fel rapporteras fore ett okant."""
    rc, ut = _rc(_bara_fargmanifest(tmp_path))
    assert rc == 1, ut
    assert "AVVIKELSER HITTADE" in ut
