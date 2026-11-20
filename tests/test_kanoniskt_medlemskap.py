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


# =========================================================================
# 5. SERIESTARTEN  (tillagt for 4ed215c)
#
# Golvet sager hur bra ett dygn blev. Seriestarten sager om dygnet alls kan
# vara ett av de 600. Tva villkor for samma medlemskap, och det andra skyddar
# mot det som inte gar att ta tillbaka: inkorningsdygnen kors mot det riktiga
# arkivet, och ett av dem som klarar golvet skulle bli verk nummer ett och
# frysas in som det.
#
# Fore 4ed215c fanns talet pa tva stallen: konstanten, och _luckor som borjade
# vid den aldsta katalogen pa disk. Det ar FYND 004:s form, och testerna nedan
# provar bade beteendet och att talet star en gang.
# =========================================================================
import ast
import inspect

import run_state


def skriv_dygn_utan_seriekolumner(rot, day, rads):
    """Ett dygn vars form inte bar series alls - da raknar kedjan om ur raderna."""
    d = sp.outdir(rot, day)
    d.mkdir(parents=True, exist_ok=True)
    fil = sp.pre_manifest(rot, day)
    falt = ["state_id", "tile_index", "evidence_basis", "evidence_sha256"]
    with open(fil, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=falt)
        w.writeheader()
        for r in rads:
            w.writerow({k: r.get(k, "") for k in falt})
    return fil


def test_gransen_for_seriens_start():
    assert pe.i_serien("20261201")
    assert pe.i_serien("20261202")
    assert not pe.i_serien("20261130")
    assert not pe.i_serien("20261129")


def test_i_serien_tar_bade_strang_och_tal():
    """Dygnet reser som strang genom kedjan men kan komma som tal fran ett
    testverktyg eller ett skript. Gransen ska vara densamma."""
    assert pe.i_serien(20261201)
    assert not pe.i_serien(20261130)


def test_golvet_vet_inte_vilket_dygn_raderna_kommer_fran():
    """serie() ska forbli ren i raderna. Blandas seriestarten in dar far vi
    ett matt som svarar pa tva fragor, och da gar det inte att saga vilken av
    dem som fallde ett dygn."""
    assert list(inspect.signature(pe.serie).parameters) == ["rader"]
    assert pe.serie(rader(600, 600)) == "CANONICAL"


def test_forserie_dygn_som_sager_canonical_i_sin_fil_raknas_inte(tmp_path):
    """Filen kan ha skrivits innan parametern fanns. Kedjan far inte tro den."""
    skriv_dygn(tmp_path, "20261130", serie="CANONICAL", index=1)
    assert _serie_i_fil_sager_canonical(tmp_path, "20261130")
    assert pe.kedja(tmp_path, "20261201") == (0, "", [])


def _serie_i_fil_sager_canonical(rot, day):
    rader_ = list(csv.DictReader(open(sp.pre_manifest(rot, day), encoding="utf-8")))
    return pe._serie_i_fil(rader_) == "CANONICAL"


def test_forserie_dygn_som_raknas_om_ur_radata_raknas_inte(tmp_path):
    """Utan series-kolumn raknar kedjan om, och 600/600 i fonstret ger CANONICAL
    pa raderna. Den far anda inte bli ett av de 600."""
    rads = rader(600, 600)
    skriv_dygn_utan_seriekolumner(tmp_path, "20261129", rads)
    assert pe.serie(rads) == "CANONICAL"
    assert pe.kedja(tmp_path, "20261201") == (0, "", [])


def test_halvfardigt_forserie_dygn_ar_inget_brott(tmp_path):
    """Inkorningen ar just de dygn som kan vara avbrutna. En katalog utan
    pre-manifest fore seriestarten far inte stoppa seriens forsta dygn."""
    sp.outdir(tmp_path, "20261130").mkdir(parents=True, exist_ok=True)
    assert pe.kedja(tmp_path, "20261201") == (0, "", [])


def test_seriens_forsta_dygn_blir_ett_trots_forserie_dygn(tmp_path):
    """Hela poangen. Tva inkorningsdygn, ett av dem kanoniskt i sin egen fil,
    och 1 december ska anda bli nummer 001."""
    skriv_dygn(tmp_path, "20261129", serie="CANONICAL", index=1)
    skriv_dygn(tmp_path, "20261130", serie="CANONICAL", index=2)
    skriv_dygn(tmp_path, "20261201", serie="CANONICAL", index=1)
    fore, _, brott = pe.kedja(tmp_path, "20261202")
    assert fore == 1, "seriens forsta dygn ska vara det enda kanoniska"
    assert brott == []


def test_luckor_listar_inte_forserie_dygn(tmp_path, monkeypatch):
    monkeypatch.setattr(run_state, "DATA", tmp_path)
    skriv_dygn(tmp_path, "20261201", serie="CANONICAL", index=1)
    assert run_state._luckor("20261205") == ["20261202", "20261203", "20261204"]


# ---- mutationen: talet star pa ett stalle --------------------------------
def test_gransen_foljer_konstanten_i_i_serien(monkeypatch):
    monkeypatch.setattr(pe, "SERIESTART", "20270115")
    assert not pe.i_serien("20270114")
    assert pe.i_serien("20270115")


def test_kedjans_filter_foljer_konstanten(monkeypatch, tmp_path):
    """Flyttas seriestarten ska kedjan sluta rakna ett dygn den nyss raknade."""
    skriv_dygn(tmp_path, "20261201", serie="CANONICAL", index=1)
    assert pe.kedja(tmp_path, "20261210")[0] == 1
    monkeypatch.setattr(pe, "SERIESTART", "20261205")
    assert pe.kedja(tmp_path, "20261210")[0] == 0


def test_luckornas_start_foljer_konstanten(tmp_path, monkeypatch):
    """_luckor borjade forut vid den aldsta katalogen pa disk - samma tal,
    uttryckt en andra gang. Flyttas konstanten ska listan folja med."""
    monkeypatch.setattr(run_state, "DATA", tmp_path)
    monkeypatch.setattr(pe, "SERIESTART", "20261203")
    assert run_state._luckor("20261205") == ["20261203", "20261204"]


def test_datumet_star_pa_ett_stalle_i_koden():
    """EN DEFINITION, ETT STALLE. Doktranger och anvandningsexempel raknas inte
    - de kan inte driva isar fran konstanten, for de styr ingenting."""
    src = ROT / "src"
    traffar = []
    for fil in sorted(src.glob("*.py")):
        trad = ast.parse(fil.read_text(encoding="utf-8"))
        doktexter = set()
        for nod in ast.walk(trad):
            if isinstance(nod, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                d = ast.get_docstring(nod, clean=False)
                if d is not None:
                    doktexter.add(id(nod.body[0].value))
        for nod in ast.walk(trad):
            if (isinstance(nod, ast.Constant) and isinstance(nod.value, str)
                    and id(nod) not in doktexter and pe.SERIESTART in nod.value):
                traffar.append(f"{fil.name}:{nod.lineno}")
    assert len(traffar) == 1 and traffar[0].startswith("pool_evidence.py:"), (
        "seriestarten ska finnas som literal pa exakt ett stalle i src/, "
        f"men star pa: {traffar}")
