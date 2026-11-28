"""A43: verket far en publicerad hash, och den har EN form.

Manifestet ar hashat, stamplat och signerat. Bilden - som ar Proof of State -
hade ingen publicerad hash alls fore 78fbb62: renderingssteget raknade ut
PNG:ens sha256 och skrev den i loggen, dar ingen kan prova den.

Skrivet av den andra parten an den som skrev step_render, enligt AGENTS.md.

FYRA PASTAENDEN:

  1. Sidecaren ligger bredvid PNG:en och heter filens namn plus .sha256.
  2. Raden ar PNG:ens FAKTISKA hash - inte en strang som rakar se ut som en
     hash. Testet raknar om den ur filens byte och jamfor.
  3. Formen ar EN form. Digest, tva blanksteg, filnamn, radslut, ingenting
     annat. Den star i dag pa flera stallen i src/ och maste vara ordagrant
     samma strang pa alla - annars far granskaren lara sig ett andra format
     for det andra beviset. FYND 004:s form, mellan tva skrivningar.
  4. Sidecaren ar inte en andra version av verket. frozen() ser en fil, inte
     tva, och publiceringens glob hittar PNG:en och inte sidecaren.

VAD TESTET INTE PASTAR: ingenting om signaturens omfang. Signaturen tacker
manifestet; bilden ar harledbar ur det. Sidecaren gor bilden kontrollerbar
utan att harleda om, och vidgar ingenting.

render_state ersatts av en egen funktion. Det som provas ar sidecaren, inte
renderaren - en riktig rendering skulle prova fargprotokollet igen och dolja
vad det ar som fallit nar testet blir rott.
"""
import hashlib
import re
import sys
import types
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))
import statepaths as sp
import run_color

# Digest, TVA blanksteg, filnamn, radslut. Inget mer i filen.
FORMEN = re.compile(r"\A([0-9a-f]{64})  (\S.*)\n\Z")

PNG_NAMN = "600_STATES_2026_315_%s_CONSENSUS.png" % sp.V
BYTE = b"\x89PNG\r\n\x1a\n" + b"rutor" * 40


def _rigga(tmp_path, namn=PNG_NAMN, byte=BYTE):
    """En renderare som skriver en kand fil, och inget annat."""
    png = tmp_path / namn
    modul = types.ModuleType("render")
    modul.render_state = lambda day, data: (png.write_bytes(byte), png)[1]
    return png, modul


def _kor(monkeypatch, tmp_path, **kw):
    png, modul = _rigga(tmp_path, **kw)
    monkeypatch.setitem(sys.modules, "render", modul)
    ut = run_color.step_render("20261201", data=tmp_path)
    return png, ut


# --- 1 och 2: sidecaren finns, och bar filens egen hash ----------------

def test_sidecaren_skrivs_bredvid_verket(monkeypatch, tmp_path):
    png, ut = _kor(monkeypatch, tmp_path)
    assert ut == png
    side = sp.sha_sidecar(png)
    assert side.exists(), "verket fick ingen publicerad hash"
    assert side.name == png.name + ".sha256"
    assert side.parent == png.parent


def test_raden_ar_verkets_faktiska_hash(monkeypatch, tmp_path):
    png, _ = _kor(monkeypatch, tmp_path)
    m = FORMEN.match(sp.sha_sidecar(png).read_text(encoding="utf-8"))
    assert m, "sidecaren har inte formen digest + tva blanksteg + namn + radslut"
    assert m.group(1) == hashlib.sha256(png.read_bytes()).hexdigest()
    assert m.group(2) == png.name, "raden namnger inte filen den galler"


def test_en_annan_bild_ger_en_annan_rad(monkeypatch, tmp_path):
    """Kontroll mot ett test som skulle gilla en pinnad strang: byt byte,
    och bade digesten och likheten med filen maste folja med."""
    a, _ = _kor(monkeypatch, tmp_path)
    rad_a = sp.sha_sidecar(a).read_text(encoding="utf-8")
    b, _ = _kor(monkeypatch, tmp_path, byte=BYTE + b"en ruta till")
    rad_b = sp.sha_sidecar(b).read_text(encoding="utf-8")
    assert rad_a != rad_b
    assert FORMEN.match(rad_b).group(1) == hashlib.sha256(b.read_bytes()).hexdigest()


def test_inget_temporart_ligger_kvar(monkeypatch, tmp_path):
    """atomic_write som allt annat. Ett halvskrivet bevis ar inget bevis."""
    png, _ = _kor(monkeypatch, tmp_path)
    kvar = sorted(p.name for p in tmp_path.iterdir())
    assert kvar == sorted([png.name, png.name + ".sha256"]), kvar


# --- 3: en form, inte tva ----------------------------------------------

def test_sidecaren_skrivs_i_en_enda_form():
    """Formen star i dag pa flera stallen i src/. VARIABELNAMNET far skilja -
    det ar inte formen - men ingenting annat far gora det. En granskare som
    kan prova fargmanifestets sidecar ska kunna prova verkets utan att lara
    sig ett andra format.

    Samlas skrivningarna till en funktion blir det en traff, och testet haller
    utan andring. Att det ar FLERA traffar i dag ar A45, inte ett fel har.
    """
    monster = re.compile(
        r"atomic_write\(\s*sp\.sha_sidecar\([^\n]*\)\s*\)\s*as\s+fh\s*:\s*\n"
        r"\s*fh\.write\((f\"[^\"]*\")\)")
    normal = lambda s: re.sub(r"\{\w+(\.name)?\}", lambda m: "{%s}" % (m.group(1) or ""), s)
    funna = {}
    for fil in sorted((ROT / "src").glob("*.py")):
        for m in monster.finditer(fil.read_text(encoding="utf-8")):
            funna.setdefault(normal(m.group(1)), []).append(fil.name)
    assert funna, "hittar ingen sidecarskrivning alls - monstret har glidit"
    assert len(funna) == 1, (
        "sidecaren skrivs i mer an en form:\n  "
        + "\n  ".join("%s  <- %s" % (s, ", ".join(f)) for s, f in funna.items()))
    (form,) = funna
    assert form == 'f"{}  {.name}\\n"', form


# --- 4: sidecaren ar inte en andra version av verket --------------------

def test_frozen_ser_en_fil_inte_tva(monkeypatch, tmp_path):
    """frozen() hojer ValueError nar en katalog bar tva versioner av samma
    fil. Sidecaren far inte raknas som den andra."""
    png, _ = _kor(monkeypatch, tmp_path)
    assert sp.frozen(png) == png


def test_publiceringens_glob_hittar_verket_och_inte_sidecaren(monkeypatch, tmp_path):
    """site/build.py letar PNG:en med samma monster. Ett hit, inte tva."""
    png, _ = _kor(monkeypatch, tmp_path)
    traff = sorted(tmp_path.glob("600_STATES_2026_315_v*_CONSENSUS.png"))
    assert traff == [png], [p.name for p in traff]


def test_grinden_kan_falla(monkeypatch, tmp_path):
    """Kontroll: utan skrivningen ska testerna ovan bli roda. Visas genom att
    formen provas mot en sidecar som saknar radslut och mot en med tre
    blanksteg - bada ar saker en slarvig rattelse kan producera."""
    assert not FORMEN.match("%s  %s" % ("a" * 64, PNG_NAMN))
    assert not FORMEN.match("%s   %s\n" % ("a" * 64, PNG_NAMN))
    assert not FORMEN.match("%s  %s\n" % ("A" * 64, PNG_NAMN))
    assert FORMEN.match("%s  %s\n" % ("a" * 64, PNG_NAMN))
