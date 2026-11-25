"""Boken: prov mot den BYGGDA PDF:en, aldrig mot konstanter i generatorn.

VARFOR DET AR HELA POANGEN MED DEN HAR FILEN
Generatorns koordinater ar avlasta ur en PDF av den andra parten. Ett test som
laser samma konstanter ur kallkoden provar da ingenting - det upprepar bara
avlasningen. Code skrev det sjalv i sin egen riskrad:

    "registrets layout vilar nu helt pa min avlasning av fyra sidor i en PDF -
     gar den avlasningen fel gar registret fel, och ingen grind sager ifran."

Darfor bygger den har filen boken och mater den fardiga sidan, och jamfor mot
det frysta manifestet i arkivet - inte mot generatorn.

KOSTNAD, SAGD RAKT UT
Tva bygganden a ~28 s. Sviten gar fran ~10 s till ~70 s med arkiv. Utan arkiv
eller utan typsnitt hoppas allt harunder over. Det ar dyrt och det ar vart det:
boken ar det tredje beviset i kedjan, och dess enda anspraak ar att samma
manifest alltid ger samma bok.
"""
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))

import config
import statepaths as sp

GENERATOR = ROT / "tools" / "bygg_bok.py"
NYCKEL = "2026_315"
DYGN = "20261111"

# Specens matt, BOKEN_SPEC 3 och 3.1. Talen star har for att kunna JAMFORAS mot
# sidan - de ar inte en kopia av generatorns varden utan specens egna.
MM = 72 / 25.4
SIDBREDD = round(210 * MM, 4)
SIDHOJD = round(150 * MM, 4)
INRE = round(23 * MM, 3)        # 65.197
YTTRE = round(14 * MM, 3)       # 39.685
SATSYTA = round(173 * MM, 3)    # 490.394
SIDOR = 611
FORSTA_RUTSIDAN = 6
RUTOR = 600


def _har_typsnitt():
    try:
        sys.path.insert(0, str(ROT / "tools"))
        import bygg_bok
        bygg_bok.typsnittskatalog()
        return True
    except BaseException:
        return False


def _har_biblioteken():
    """pdfplumber for matningen, reportlab och qrcode for bygget.

    DEN HAR GRINDEN SAKNADE reportlab OCH qrcode I FORSTA VERSIONEN och nio
    prov foll pa ett ModuleNotFoundError i en underprocess i stallet for att
    hoppas over. Ett prov som inte kan kora ska saga det, inte krascha.
    """
    for namn in ("pdfplumber", "reportlab", "qrcode"):
        try:
            __import__(namn)
        except ImportError:
            return False
    return True


kraver_bok = pytest.mark.skipif(
    not (config.SPEC_FILE.exists() and _har_typsnitt() and _har_biblioteken()),
    reason="kraver dataarkivet, DejaVu via STATES_FONTS, pdfplumber, reportlab, qrcode")


def _bygg(ut):
    r = subprocess.run([sys.executable, str(GENERATOR), str(ut), NYCKEL],
                       cwd=str(ROT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return ut


@pytest.fixture(scope="module")
def boken(tmp_path_factory):
    """Tva bygganden av SAMMA dygn, plus vaggklockan runt det forsta."""
    d = tmp_path_factory.mktemp("bok")
    fore = time.time()
    a = _bygg(d / "a.pdf")
    efter = time.time()
    b = _bygg(d / "b.pdf")
    return {"a": a, "b": b, "byggd_mellan": (fore, efter)}


@pytest.fixture(scope="module")
def manifest():
    """Det frysta manifestet, {tile_index: hex}."""
    import csv
    kat = sp.outdir(config.DATA, DYGN)
    traff = sorted(kat.glob("*EMOTION_COLOR_MANIFEST*CONSENSUS.csv"))
    assert traff, f"inget fargmanifest i {kat}"
    with open(traff[0], encoding="utf-8") as fh:
        rader = list(csv.DictReader(fh))
    return {int(r["tile_index"]): r["hex"].lower() for r in rader}


def _rutor(sida, bredd, tol=0.05):
    """Rektanglar med en given bredd, vansterkanterna sorterade."""
    return sorted({round(r["x0"], 3) for r in sida.rects
                   if abs(r["x1"] - r["x0"] - bredd) < tol})


# ---------------------------------------------------------------- formen

@kraver_bok
def test_sidantal_och_sidyta(boken):
    import pdfplumber
    with pdfplumber.open(boken["a"]) as pdf:
        assert len(pdf.pages) == SIDOR
        assert round(pdf.pages[0].width, 4) == SIDBREDD
        assert round(pdf.pages[0].height, 4) == SIDHOJD


@kraver_bok
def test_forsta_rutsidan_ar_sex(boken):
    """Fortexten ar fem sidor. Flyttar den flyttar hela boken."""
    import pdfplumber
    with pdfplumber.open(boken["a"]) as pdf:
        # rutsidan kanns igen pa fargrutan, 42 mm bred
        for i in range(SIDOR):
            if _rutor(pdf.pages[i], 42 * MM):
                assert i + 1 == FORSTA_RUTSIDAN
                return
    pytest.fail("ingen sida bar en 42 mm fargruta")


# ------------------------------------------------- raderna ur manifestet

@kraver_bok
def test_varje_rutsida_bar_sin_rad_ur_manifestet(boken, manifest):
    """600 sidor, 600 ordningstal, 600 hexvarden - lasta ur den byggda boken."""
    import pdfplumber, re
    sedda = {}
    with pdfplumber.open(boken["a"]) as pdf:
        for n in range(FORSTA_RUTSIDAN, FORSTA_RUTSIDAN + RUTOR):
            text = pdf.pages[n - 1].extract_text() or ""
            tal = re.search(r"\b(\d{3})\b", text)
            hexv = re.search(r"#([0-9A-Fa-f]{6})", text)
            assert tal and hexv, f"sida {n} saknar ordningstal eller hex"
            sedda[int(tal.group(1))] = "#" + hexv.group(1).lower()
    assert len(sedda) == RUTOR, "ordningstal upprepas mellan rutsidor"
    assert sorted(sedda) == list(range(1, RUTOR + 1)), "lucka i ordningstalen"
    fel = {i: (v, manifest[i]) for i, v in sedda.items() if v != manifest[i]}
    assert not fel, f"hexvarden som inte ar manifestets: {list(fel)[:5]}"


@kraver_bok
def test_registret_bar_manifestets_600_varden(boken, manifest):
    """Fargregistret, sidorna 606-609. Ingen lucka, ingen dubblett.

    ORDNINGEN LASES UR LAGET, INTE UR TEXTEN. Registret ar satt i kolumner och
    lases nedfor dem; extract_text() lamnar raderna tvars over sidan och ger
    1, 29, 57, 85... Forsta versionen av provet jamforde den ordningen mot
    1..600 och foll. Sorteringen pa (x, y) ar den ritordning Code matte.
    """
    import pdfplumber, re
    MON = re.compile(r"^(\d{3})#([0-9A-Fa-f]{6})$")
    poster, per_sida = [], {}
    with pdfplumber.open(boken["a"]) as pdf:
        for n in range(606, 610):
            funna = [(round(w["x0"], 1), round(w["top"], 1), w["text"])
                     for w in pdf.pages[n - 1].extract_words()
                     if MON.match(w["text"])]
            per_sida[n] = funna
            poster += sorted(funna, key=lambda q: (q[0], q[1]))

    assert [len(per_sida[n]) for n in (606, 607, 608, 609)] == [168, 168, 168, 96], \
        {n: len(v) for n, v in per_sida.items()}
    assert len(poster) == RUTOR

    index = [int(MON.match(t).group(1)) for _, _, t in poster]
    assert index == list(range(1, RUTOR + 1)), \
        f"registret ar inte i obruten kolumnordning: {index[:8]}"

    fel = [i for i, (_, _, t) in zip(index, poster)
           if "#" + MON.match(t).group(2).lower() != manifest[i]]
    assert not fel, f"registret avviker fran manifestet i {fel[:5]}"


# ------------------------------------------------------------- speglingen

@kraver_bok
def test_satsytan_speglar_pa_rutsidorna(boken):
    """Udda sida har ryggen till vanster: satsytan borjar pa inre marginalen."""
    import pdfplumber
    with pdfplumber.open(boken["a"]) as pdf:
        for n in (6, 7, 310, 311, 604, 605):
            kant = _rutor(pdf.pages[n - 1], 42 * MM)
            assert len(kant) == 1, f"sida {n}: {len(kant)} fargrutor"
            vantat = INRE if n % 2 else YTTRE
            assert kant[0] == pytest.approx(vantat, abs=0.01), \
                f"sida {n} borjar pa {kant[0]}, vantat {vantat}"


@kraver_bok
def test_satsytan_speglar_i_registret(boken):
    """Fyra registersidor i ett tradbundet block maste spegla som alla andra."""
    import pdfplumber
    steg = round(SATSYTA / 6, 3)
    with pdfplumber.open(boken["a"]) as pdf:
        for n in (606, 607, 608, 609):
            kol = _rutor(pdf.pages[n - 1], 5.2)
            assert kol, f"sida {n} bar inga fargrutor"
            vantat = INRE if n % 2 else YTTRE
            assert kol[0] == pytest.approx(vantat, abs=0.01), \
                f"sida {n} borjar pa {kol[0]}, vantat {vantat}"
            if len(kol) > 1:
                assert kol[1] - kol[0] == pytest.approx(steg, abs=0.01), \
                    f"sida {n}: kolumnsteg {kol[1] - kol[0]}, vantat {steg}"


# ------------------------------------------------------ oaterkalleligheten

@kraver_bok
def test_samma_manifest_ger_byteidentisk_pdf(boken):
    """Bokens enda anspraak. Faller den faller skalet att den genereras av kod."""
    h = [hashlib.sha256(boken[k].read_bytes()).hexdigest() for k in ("a", "b")]
    assert h[0] == h[1], f"tva bygganden gav olika filer: {h[0][:12]} / {h[1][:12]}"


@kraver_bok
def test_datumet_ar_dygnets_midnatt_och_inte_byggtiden(boken):
    """POSITIVT KONTROLLPROV till testet ovan.

    Tva lika hashar bevisar inte frysning - de kan betyda att ingenting i
    bygget ar tidsberoende. Det har provet visar att datumfaltet BAR dygnet
    och inte klockan, vilket ar mekanismen. Lamnas det at reportlab skriver
    den byggtiden, och da ar talet inom fonstret harunder.
    """
    import pdfplumber
    fore, efter = boken["byggd_mellan"]
    with pdfplumber.open(boken["a"]) as pdf:
        skapad = str(pdf.metadata.get("CreationDate", ""))
        andrad = str(pdf.metadata.get("ModDate", ""))
    assert DYGN in skapad, f"CreationDate bar inte {DYGN}: {skapad!r}"
    assert skapad == andrad, "CreationDate och ModDate sager olika saker"
    for t in (fore, efter):
        stampel = time.strftime("D:%Y%m%d", time.gmtime(t))
        assert stampel not in skapad, \
            f"datumet ar byggtiden, inte dygnet: {skapad!r}"


# ------------------------------------------------------------ separationen

def test_instrumentet_kan_inte_importera_boken():
    """Egen tolk: en import i den har processen sager inget om instrumentets."""
    kod = ("import sys; sys.path.insert(0, 'src');"
           "import run_state, pool_evidence, classify, run_color;"
           "assert 'reportlab' not in sys.modules, 'instrumentet drog in reportlab';"
           "assert 'bygg_bok' not in sys.modules, 'instrumentet drog in boken';"
           "print('ok')")
    r = subprocess.run([sys.executable, "-c", kod], cwd=str(ROT),
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok" in r.stdout


def test_bokens_lasfil_pinnar_exakta_versioner():
    """Den publicerade sha256:n ar bara reproducerbar ur den LASTA miljon.

    UPPMATT 2026-11-25, och det ar skalet att provet finns: samma manifest och
    samma generator gav

        c184ee15...  reportlab 5.0.1, Windows   (andra parten)
        23be3b8f...  reportlab 5.1.0, Linux     (detta prov)

    Samma antal byte, 10 742 069, olika innehall. Byteidentitet galler INOM en
    miljo, aldrig mellan tva reportlab-versioner. Darfor maste lasfilen pinna
    exakt - ett >= gor den publicerade hashen till ett pastaende ingen kan
    kontrollera, och BOKEN_SPEC 2 publicerar den hashen bredvid bildens.
    """
    rader = [r.strip() for r in
             (ROT / "deploy" / "requirements-bok.txt").read_text(encoding="utf-8").splitlines()
             if r.strip() and not r.strip().startswith("#")]
    assert rader, "lasfilen ar tom - provet sager inget"
    for r in rader:
        assert "==" in r, f"lasfilen pinnar inte exakt: {r!r}"
        assert not any(t in r for t in (">=", "<=", "~=", ">", "<")), \
            f"lasfilen bar ett intervall: {r!r}"


def test_kedjans_requirements_bar_inte_pdf_biblioteken():
    """reportlab och qrcode hor hemma i deploy/requirements-bok.txt."""
    kedjan = (ROT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert kedjan.strip(), "requirements.txt ar tom - provet sager inget"
    for namn in ("reportlab", "qrcode"):
        assert namn not in kedjan, f"{namn} star i kedjans requirements.txt"
    boken = (ROT / "deploy" / "requirements-bok.txt").read_text(encoding="utf-8").lower()
    for namn in ("reportlab", "qrcode"):
        assert namn in boken, f"{namn} saknas i bokens lasfil"


def test_generatorn_bar_ingen_lokal_sokvag_och_inget_namn():
    """Samma regel som fore_push, provad dar den kan falla ett test."""
    import re
    kod = GENERATOR.read_text(encoding="utf-8")
    # HEMKATALOGERNA STAVAS SOM I fore_push.py, med en alternation och inte med
    # de tva sokvagarna utskrivna var for sig. Skalet star i den filens egen
    # docstring: grinden laser HELA objektdatabasen, den har filen inrakad, och
    # en regex som stavar ut det forbjudna faller pa sig sjalv vid nasta
    # korning. Skriv inte om den till literaler "for tydlighetens skull" - da
    # blir grinden rod, och bloben gar inte att ta bort utan att skriva om
    # historiken. Formen ar bredare an den var, inte smalare: den tar aven
    # omvand snedstreck.
    for monster in (r"[A-Za-z]:\\\\", r"[\\/](?:Users|home)[\\/]", r"/volume\d"):
        assert not re.search(monster, kod), f"lokal sokvag i generatorn: {monster}"
    assert "STATES_FONTS" in kod, "typsnittskatalogen ska komma ur miljon"


@kraver_bok
def test_omslaget_ar_regular_inte_extralight(boken):
    """A2 fastslogs 2026-11-14. Den bargade PDF:en bar A1 - kopiera inte den."""
    import pdfplumber
    with pdfplumber.open(boken["a"]) as pdf:
        titel = [ch for ch in pdf.pages[0].chars if round(ch["size"], 1) == 40.0]
    assert titel, "ingen 40-punktstext pa titelsidan"
    namn = {ch["fontname"].split("+")[-1] for ch in titel}
    assert namn == {"DejaVuSans"}, f"titeln ar satt i {namn}, ska vara regular"
