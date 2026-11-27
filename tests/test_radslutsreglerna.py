"""Acceptanstest for radslutsreglerna i .gitattributes.

Skrivet av den andra parten an den som andrade filen, enligt AGENTS.md.

BAKGRUND, 2026-11-27. Instruktionen till den som andrade filen sa att
skyddsraderna for de frysta filerna skulle sta FORST. Det var fel: i
.gitattributes vinner den SISTA traffande raden. Hade skyddet stat forst hade
den generella regeln "* text=auto eol=lf" skrivit over det och normaliserat
exekveringsprompten, specen, fargprotokollet och kallregistret - alltsa flyttat
de hashar hela provenienskedjan vilar pa. Den som andrade vagrade, matte med
git check-attr och visade text: unset.

Regeln bor darfor inte i nagons minnesbild. Den provas har, och proven stalls
mot GITS EGET SVAR - inte mot filens text. En rad i .gitattributes sager vad
nagon avsett; check-attr sager vad git faktiskt gor.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import statepaths as sp


def git(*args):
    """Kor git i repots rot och returnerar stdout. Faller med besked om git
    inte gar att kora - ett overhoppat prov ar inte ett godkant prov, och den
    har filen provar en egenskap hos repot som bara git kan svara pa."""
    r = subprocess.run(("git",) + args, cwd=ROT, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.fail(f"git {' '.join(args)} gav {r.returncode}: {r.stderr.strip()}")
    return r.stdout


def attribut(sokvagar, *attr):
    """{sokvag: {attribut: varde}} ur git check-attr."""
    ut = {}
    rad_ut = git("check-attr", *attr, "--", *sokvagar)
    for rad in rad_ut.splitlines():
        if not rad.strip():
            continue
        vag, namn, varde = rad.rsplit(": ", 2)
        ut.setdefault(vag, {})[namn] = varde
    return ut


def skyddade():
    """De filer .gitattributes haller utanfor normaliseringen, lasta ur
    repot och inte uppraknade har. En lista i provet vore ett varde pa tva
    stallen - FYND 004:s form."""
    vagar = [v for v in git("ls-files", "protocols/").splitlines() if v.strip()]
    vagar += [v for v in git("ls-files", "600states.pub").splitlines() if v.strip()]
    return vagar


# ---- 1. skyddet haller ---------------------------------------------------
def test_de_frysta_filerna_normaliseras_inte():
    """Varje fil under protocols/ och den publika nyckeln ska bara -text.
    text: unset ar gits svar pa att filen lamnas i fred."""
    vagar = skyddade()
    assert vagar, "inga skyddade filer hittades - provet skulle da inte prova nagot"
    svar = attribut(vagar, "text")
    fel = [v for v in vagar if svar.get(v, {}).get("text") != "unset"]
    assert not fel, ("dessa frysta filer ar inte skyddade mot normalisering: "
                     + ", ".join(fel))


def test_kontrollprov_en_vanlig_kallfil_normaliseras():
    """Positivt kontrollprov. Provet ovan ar vardelost om check-attr svarar
    unset for allt - da vore skyddet omojligt att skilja fran ingen regel."""
    svar = attribut(["src/pool_evidence.py"], "text", "eol")
    assert svar["src/pool_evidence.py"]["text"] == "auto"
    assert svar["src/pool_evidence.py"]["eol"] == "lf"


def test_ordningen_i_filen_satter_skyddet_sist():
    """Den regel som nastan forstordes. Den generella raden maste komma FORE
    skyddsraderna, eftersom sista traffen vinner. Provet laser filens text -
    till skillnad fran de ovriga - just for att fanga en omflyttning som annu
    inte hunnit andra nagot utfall."""
    rader = (ROT / ".gitattributes").read_text(encoding="utf-8").splitlines()
    generell = [i for i, r in enumerate(rader) if r.strip().startswith("* text=")]
    skydd = [i for i, r in enumerate(rader)
             if "-text" in r and not r.strip().startswith("#")]
    assert generell, ".gitattributes saknar den generella regeln * text=..."
    assert skydd, ".gitattributes saknar varje -text-rad"
    assert max(generell) < min(skydd), (
        "skyddsraderna star FORE den generella regeln. Sista traffen vinner i "
        ".gitattributes, sa de frysta filerna skulle da normaliseras.")


# ---- 2. indexet bar LF ---------------------------------------------------
def test_ingen_sparad_kallfil_bar_crlf_i_indexet():
    """eol=lf styr utcheckningen; det har provar vad som faktiskt ligger
    LAGRAT. En commit med CRLF i indexet gor repot plattformsberoende igen."""
    fel = []
    for rad in git("ls-files", "--eol", "--", "src", "site", "tests").splitlines():
        if not rad.strip():
            continue
        delar = rad.split(None, 3)
        if len(delar) == 4 and delar[0] == "i/crlf":
            fel.append(delar[3])
    assert not fel, "dessa filer bar CRLF i indexet: " + ", ".join(fel)


def test_kontrollprov_matningen_hittar_crlf_nar_det_finns():
    """Provet ovan pastar en nolla. En nolla ur en matning som inte kan se
    det den letar efter ar ingen matning. Kallregistret ar fryst i CRLF och
    ska synas - samma kommando, samma tolkning."""
    traffar = []
    for rad in git("ls-files", "--eol", "--", "protocols").splitlines():
        delar = rad.split(None, 3)
        if len(delar) == 4 and delar[0] == "i/crlf":
            traffar.append(delar[3])
    assert traffar, ("matningen hittade ingen CRLF nagonstans - da kan den "
                     "inte heller sta for nollan i provet ovan")
