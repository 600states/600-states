"""Acceptanstest for kanoniskt medlemskap: golvet, serien och kedjan bakat.

Skrivet av den andra parten an den som implementerade, enligt AGENTS.md.
Testerna provar BETEENDE i egna temporarkataloger och ror aldrig arkivet.

Tre pastaenden provas, och de ar valda for att de ar de tre som faktiskt
kan ga sonder tyst:

1. SERIEN RAKNAS PA FONSTRET, INTE PA HASHEN. Specen sa forst innehallshash,
   och da blev alla fyra retrospektiva v3-dygn CANONICAL trots noll rader i
   fonstret. En hash sager att sidan FINNS, inte att vi hade den i tid.

2. GOLVET AR EN KONSTANT, INTE ETT TAL I EN JAMFORELSE. Darfor flyttas
   konstanten i ett test och gransen ska folja med. Ett test som bara provar
   540 och 539 kan inte skilja ratt implementation fran en hardkodad siffra.

3. GOLVET AR INGEN GRIND. Ett dygn under golvet produceras anda. Det som
   DAREMOT stoppar korningen ar ett arkiv dar ordningstalet inte gar att
   rakna fram. Bada riktningarna provas.
"""
import csv, hashlib, sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
import pool_evidence as pe
import statepaths as sp
import gates

KOLUMNER = ["state_id", "tile_index", "evidence_basis", "evidence_sha256",
            "series", "canonical_index", "prev_canonical_sha256"]


# ---- byggstenar ----------------------------------------------------------
def rader(n=600, i_fonstret=600, med_hash=True):
    """n rader dar i_fonstret bar CAPTURED_IN_WINDOW och resten RETROSPECTIVE."""
    ut = []
    for i in range(n):
        ut.append({"state_id": "2026/335", "tile_index": str(i + 1),
                   "evidence_basis": "CAPTURED_IN_WINDOW" if i < i_fonstret else "RETROSPECTIVE",
                   "evidence_sha256": "a" * 64 if med_hash else ""})
    return ut


def skriv_dygn(rot, day, serie="CANONICAL", index=None, prev="", rads=None):
    """Skriver ett dygns pre-manifest i en temporarkatalog. Returnerar filen."""
    d = sp.outdir(rot, day)
    d.mkdir(parents=True, exist_ok=True)
    fil = sp.pre_manifest(rot, day)
    rads = rads if rads is not None else rader(3)
    with open(fil, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=KOLUMNER)
        w.writeheader()
        for r in rads:
            rad = dict(r)
            rad.update({"series": serie,
                        "canonical_index": f"{index:03d}" if index else "",
                        "prev_canonical_sha256": prev})
            w.writerow({k: rad.get(k, "") for k in KOLUMNER})
    return fil


def sha(p):
    """Testets egen hashning, oberoende av implementationens hjalpfunktion."""
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---- 1. serie() raknar fonstret ------------------------------------------
def test_alla_rader_i_fonstret_ar_kanoniskt():
    assert pe.serie(rader(600, 600)) == "CANONICAL"


def test_exakt_pa_golvet_ar_kanoniskt():
    """Golvet ar inklusivt. Den som star pa golvet ar uppe."""
    assert pe.serie(rader(600, 540)) == "CANONICAL"


def test_en_rad_under_golvet_ar_inte_kanoniskt():
    assert pe.serie(rader(600, 539)) == "UNQUALIFIED"


def test_hashandel_utan_fonster_kvalificerar_inte():
    """REGRESSIONEN. 600 hashade sidor, noll i fonstret - ett retrospektivt
    dygn. Pa hashandel var detta 100 procent och blev CANONICAL."""
    assert pe.serie(rader(600, 0, med_hash=True)) == "UNQUALIFIED"


def test_hashen_paverkar_inte_utfallet():
    """Samma fonsterandel med och utan hash ska ge samma svar."""
    assert (pe.serie(rader(600, 540, med_hash=True))
            == pe.serie(rader(600, 540, med_hash=False))
            == "CANONICAL")


def test_dygn_vars_form_saknar_faltet_ar_inte_kanoniskt():
    """De tre v3.2-dygnen bar inte evidence_basis alls. Det som inte sager
    nar det fangades sager inte att det fangades i tid."""
    utan = [{"state_id": "x", "tile_index": str(i)} for i in range(600)]
    assert pe.serie(utan) == "UNQUALIFIED"


def test_tomt_dygn_ar_inte_kanoniskt():
    assert pe.serie([]) == "UNQUALIFIED"


# ---- 2. golvet ar en konstant --------------------------------------------
def test_golvet_ar_nittio_procent():
    assert pe.GOLV_KANONISK == 0.90


def test_gransen_foljer_konstanten_och_inte_en_hardkodad_siffra(monkeypatch):
    """Flyttas konstanten ska gransen flytta med. Annars kan testet ovan inte
    skilja en riktig implementation fran talet 540 skrivet i koden."""
    monkeypatch.setattr(pe, "GOLV_KANONISK", 0.50)
    assert pe.serie(rader(600, 300)) == "CANONICAL"
    assert pe.serie(rader(600, 299)) == "UNQUALIFIED"


# ---- 3. kedjan bakat -----------------------------------------------------
def test_tomt_arkiv_ger_forsta_platsen(tmp_path):
    fore, prev, brott = pe.kedja(tmp_path, "20261201")
    assert (fore, prev, brott) == (0, "", [])


def test_ett_kanoniskt_dygn_fore_raknas_och_lankas(tmp_path):
    f = skriv_dygn(tmp_path, "20261201", serie="CANONICAL", index=1)
    fore, prev, brott = pe.kedja(tmp_path, "20261202")
    assert fore == 1
    assert prev == sha(f)
    assert brott == []


def test_ett_dygn_under_golvet_raknas_inte(tmp_path):
    skriv_dygn(tmp_path, "20261201", serie="UNQUALIFIED")
    fore, prev, brott = pe.kedja(tmp_path, "20261202")
    assert (fore, prev, brott) == (0, "", [])


def test_dygnet_sjalvt_och_senare_dygn_raknas_inte(tmp_path):
    skriv_dygn(tmp_path, "20261202", serie="CANONICAL", index=1)
    skriv_dygn(tmp_path, "20261203", serie="CANONICAL", index=2)
    fore, _, brott = pe.kedja(tmp_path, "20261202")
    assert fore == 0
    assert brott == []


def test_saknat_manifest_ar_ett_brott(tmp_path):
    sp.outdir(tmp_path, "20261201").mkdir(parents=True, exist_ok=True)
    _, _, brott = pe.kedja(tmp_path, "20261202")
    assert len(brott) == 1
    assert "20261201" in brott[0].replace("_", "") or "STATE" in brott[0]


def test_lank_bakat_som_inte_stammer_ar_ett_brott(tmp_path):
    skriv_dygn(tmp_path, "20261201", serie="CANONICAL", index=1)
    skriv_dygn(tmp_path, "20261202", serie="CANONICAL", index=2, prev="0" * 64)
    _, _, brott = pe.kedja(tmp_path, "20261203")
    assert any("lanken bakat" in b for b in brott)


def test_ordningstal_som_inte_ar_sin_plats_ar_ett_brott(tmp_path):
    skriv_dygn(tmp_path, "20261201", serie="CANONICAL", index=17)
    _, _, brott = pe.kedja(tmp_path, "20261202")
    assert any("ordningstal" in b for b in brott)


def test_ratt_kedja_over_tva_dygn_ger_inga_brott(tmp_path):
    f1 = skriv_dygn(tmp_path, "20261201", serie="CANONICAL", index=1)
    skriv_dygn(tmp_path, "20261202", serie="CANONICAL", index=2, prev=sha(f1))
    fore, prev, brott = pe.kedja(tmp_path, "20261203")
    assert fore == 2
    assert brott == []
    assert prev == sha(sp.pre_manifest(tmp_path, "20261202"))


# ---- 4. vad som stoppar korningen, och vad som inte gor det --------------
def test_brott_i_kedjan_stoppar_korningen():
    with pytest.raises(gates.GateFailure):
        gates.gate_kanonisk_kedja("CANONICAL", 1, ["STATE_2026_302: inget pre-manifest"])


def test_ordningstal_over_taket_stoppar_korningen():
    with pytest.raises(gates.GateFailure):
        gates.gate_kanonisk_kedja("CANONICAL", 601, [])


def test_sista_numret_i_serien_slapps_igenom():
    gates.gate_kanonisk_kedja("CANONICAL", 600, [])


def test_dygn_under_golvet_stoppar_inte_korningen():
    """GOLVET AR INGEN GRIND. Dygnet produceras anda, det far bara inget
    nummer. Att hoppa over det bryter en dag, en korning, ett utfall."""
    gates.gate_kanonisk_kedja("UNQUALIFIED", None, [])
