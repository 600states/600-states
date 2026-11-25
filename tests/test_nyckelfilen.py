"""Den publika signeringsnyckelns BYTES, inte dess innehall.

VARFOR
Nyckelns sha256 ar publicerad i PARAMETER_REGISTER 1.18. En fil vars hash ar
publicerad far inte radslutsnormaliseras: `text=auto` hade gjort en klon pa
Windows till 115 byte och en pa Linux till 113, och den publicerade hashen hade
stammat pa hogst en av dem. `.gitattributes` bar redan den regeln for
`protocols/**` sedan 2026-11-20 — den var bara inte tillampad pa nyckeln, och
git sade ifran vid incheckningen: "LF will be replaced by CRLF".

EN REGEL I .gitattributes AR ETT ONSKEMAL TILLS NAGOT LASER BYTEN.
Proven harunder laser det INCHECKADE objektet, inte arbetskopian: det ar
objektet som klonas, och arbetskopian ar redan platsspecifik.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent

NYCKEL = "600states.pub"
# UR NAS:ENS RAPPORT 2026-11-25 och oberoende harledd ur nyckeltexten.
PUBLICERAD_SHA = "0e759259d7a2a25f20595d8534d88e3066e6581717d5d8495472dbb84f252b58"
PUBLICERAD_LANGD = 113
NYCKEL_ID = "B081656E9A8D302C"


def _git(*argv, text=True):
    return subprocess.run(["git", *argv], cwd=str(ROT),
                          capture_output=True, text=text)


kraver_git = pytest.mark.skipif(
    _git("rev-parse", "--git-dir").returncode != 0,
    reason="ingen git-katalog")


@kraver_git
def test_det_incheckade_objektet_ar_de_publicerade_byten():
    """Objektet som klonas MASTE vara de 113 byte vars hash star i 1.18."""
    r = _git("cat-file", "-p", f"HEAD:{NYCKEL}", text=False)
    assert r.returncode == 0, "nyckeln finns inte i HEAD"
    raw = r.stdout
    assert len(raw) == PUBLICERAD_LANGD, \
        f"{len(raw)} byte, publicerat {PUBLICERAD_LANGD}"
    assert hashlib.sha256(raw).hexdigest() == PUBLICERAD_SHA, \
        "objektets hash ar inte den publicerade"
    assert b"\r" not in raw, "objektet bar CR - radsluten har normaliserats"


@kraver_git
def test_nyckeln_ar_undantagen_fran_radslutsnormalisering():
    """`-text` i .gitattributes. Utan den konverterar en Windows-utcheckning."""
    r = _git("check-attr", "text", "--", NYCKEL)
    assert r.returncode == 0
    assert "text: unset" in r.stdout, \
        f"nyckeln ar inte markerad -text: {r.stdout.strip()!r}"


@kraver_git
def test_de_frysta_protokollen_ar_fortfarande_undantagna():
    """Regeln fanns for protocols/** fore nyckeln. Tas den bort gar tolv
    publicerade hashar sonder tyst."""
    r = _git("check-attr", "text", "--", "protocols/LICENSE")
    assert "text: unset" in r.stdout, \
        f"protocols/** har tappat sitt -text: {r.stdout.strip()!r}"


@kraver_git
def test_nyckel_id_i_kommentaren_ar_nyckelns_eget():
    """Kommentarsraden heter *untrusted* med avsikt och kan saga vad som helst.
    Id:t i base64-nyttolasten ar sanningen; de tva ska stamma.

    Mutationsprov inbakat: ett andrat tecken tidigt i base64 ger ett annat id,
    sa overensstammelsen ar en kontroll och inte en tautologi.
    """
    import base64
    r = _git("cat-file", "-p", f"HEAD:{NYCKEL}")
    rader = r.stdout.splitlines()
    assert len(rader) == 2, f"{len(rader)} rader i nyckelfilen"
    assert NYCKEL_ID in rader[0], "kommentarsraden namner inte nyckel-id:t"

    raw = base64.b64decode(rader[1])
    assert len(raw) == 42, f"{len(raw)} byte avkodat, Ed25519 vantar 42"
    assert raw[:2] == b"Ed", f"algoritm {raw[:2]!r}, inte Ed25519"
    assert raw[2:10][::-1].hex().upper() == NYCKEL_ID, \
        "id:t i nyttolasten ar inte det kommentaren pastar"

    muterad = rader[1][:3] + ("A" if rader[1][3] != "A" else "B") + rader[1][4:]
    assert base64.b64decode(muterad)[2:10][::-1].hex().upper() != NYCKEL_ID, \
        "provet duger inte: ett muterat tecken gav samma id"
