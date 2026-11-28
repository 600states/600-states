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

Att prova koden i stallet for utfallet ar ett undantag och ska forbli det.
Skalet star har: utfallsvagen kraver ett helt riggat dygn i ett andra arkiv -
fyra manifest, en batchkatalog och en bevispool - och ett test som bygger sa
mycket provar till slut riggningen och inte raden.
"""
import ast
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
