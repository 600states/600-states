"""Acceptanstest for tools/fore_push.py — grinden fore push.

Den finns for ett verkligt fel: agarens fornamn lag i nio commitmeddelanden i
ett publikt repo i tva manader. Genomsokningen som godkande pushen las bara
blobbar, alltsa filinnehall, och rapporterade noll traffar. Commitmeddelanden
ar egna objekt och hoppades over helt.

Skrivet av den andra parten an den som byggde grinden, enligt AGENTS.md.
Testerna provar BETEENDE i engangsrepon under tmp_path. De ror aldrig
projektets repo och aldrig arkivets riktiga ordlista.

Det fem pastaendena som baro:

  1. ett namn i ett COMMITMEDDELANDE faller - filen kan vara ren
  2. ett ONABART objekt faller - det en gren pekar pa ar inte allt som pushas
  3. attributionen provas pa RADEN, sa regelboken faller inte pa sig sjalv
  4. tillatlistan star pa INNEHALL - samma monster, annan strang, faller anda
  5. utan ordlista sager grinden "provades inte", ALDRIG "rent"
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "tools"))
sys.path.insert(0, str(ROT))
import fore_push


# EXEMPLEN BYGGS IHOP, DE STAR ALDRIG HELA I FILEN.
# Ett test for grinden maste innehalla exempel pa det forbjudna, och grinden
# laser den har filen som vilken annan. Star strangarna hela faller den pa sitt
# eget test - regelbok-problemet en niva till. chr(92) ar omvant snedstreck.
NAMN = "QXTESTNAMN"                          # bara i testets egen ordlista
EPOST = "nagon" + "@" + "annanfirma.se"
EGEN = "archive" + "@" + "600states.com"
SOKVAG = "C:" + chr(92) + "Users" + chr(92) + "nagon" + chr(92) + "Dokument"
TILLATEN_SOKVAG = "C:" + chr(92) + "dev" + chr(92) + "600-states"


def git(repo, *a, indata=None):
    return subprocess.run(["git", "-C", str(repo), *a], check=True,
                          input=indata, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Ett tomt repo och en tom ordlista. Varken projektets repo eller arkivets
    riktiga lista far roras av ett test."""
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.name", "600 STATES")
    git(r, "config", "user.email", "archive@600states.com")
    (r / "a.txt").write_text("ingenting kansligt\n", encoding="utf-8")
    git(r, "add", "-A")
    git(r, "commit", "-qm", "forsta")
    data = tmp_path / "arkiv"
    data.mkdir()
    (data / fore_push.ORDLISTA).write_text(
        "# testordlista\n[privat namn]\n" + NAMN + "\n"
        "[kommersiell strategi]\nreservpris\nutropspris\n", encoding="utf-8")
    monkeypatch.setattr(fore_push.config, "data_root", lambda: data)
    return r


def kor(repo, capfd):
    kod = fore_push.main(repo)
    return kod, capfd.readouterr().out


# ---- 0. ett rent repo slapps igenom ------------------------------------
def test_rent_repo_ger_felkod_noll(repo, capfd):
    kod, ut = kor(repo, capfd)
    assert kod == 0
    assert "Rent" in ut


# ---- 1. commitmeddelandet, som var hela missen -------------------------
def test_namn_i_commitmeddelande_faller_aven_nar_filen_ar_ren(repo, capfd):
    """Karnan i FYND:et. Filen ar ren; namnet star bara i meddelandet."""
    (repo / "b.txt").write_text("helt ofarligt\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "andra: " + NAMN + " bad om detta")
    kod, ut = kor(repo, capfd)
    assert kod == 1
    assert "privat namn" in ut
    assert "commit" in ut


def test_namn_i_fil_faller(repo, capfd):
    (repo / "b.txt").write_text("Kontakt: " + NAMN + "\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "andra")
    assert kor(repo, capfd)[0] == 1


def test_filNAMNET_provas_ocksa(repo, capfd):
    """Ett tradobjekt bar filnamnen, och de ar lika publika som innehallet."""
    (repo / (NAMN + ".txt")).write_text("tomt\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "andra")
    assert kor(repo, capfd)[0] == 1


# ---- 2. onabara objekt --------------------------------------------------
def test_onabart_objekt_faller(repo, capfd):
    """git rev-list ser bara det en gren pekar pa. Tre attributionsrader lag i
    overgivna objekt fran amends och syntes aldrig. Grinden laser databasen."""
    (repo / "b.txt").write_text("x\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "andra: " + NAMN)
    git(repo, "reset", "-q", "--hard", "HEAD~1")        # objektet finns kvar
    assert git(repo, "log", "--oneline").count("\n") == 1
    kod, ut = kor(repo, capfd)
    assert kod == 1, "ett objekt som ingen gren pekar pa ar anda i databasen"
    assert "privat namn" in ut


# ---- 3. raden, inte ordet ----------------------------------------------
def test_attributionsrad_i_commitmeddelande_faller(repo, capfd):
    (repo / "b.txt").write_text("x\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qF", "-",
        indata="andra\n\nCo-Authored-By: Nagon <" + EPOST + ">\n")
    kod, ut = kor(repo, capfd)
    assert kod == 1
    assert "attribution" in ut


def test_regelboken_faller_inte_pa_sig_sjalv(repo, capfd):
    """Orden maste kunna sta som loptext i AGENTS.md, COPYRIGHT.md och kartan -
    de tre texter som beskriver forbudet. Faller grinden pa ordet faller den pa
    sin egen regelbok."""
    (repo / "AGENTS.md").write_text(
        "Ingen rad som borjar med Co-Authored-By eller Claude-Session far in i\n"
        "ett commitmeddelande. Lanken till claude.ai/code hor inte heller dit.\n",
        encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "regeln skrivs ned")
    kod, ut = kor(repo, capfd)
    assert kod == 0, f"grinden foll pa sin egen regelbok:\n{ut}"


# ---- 4. tillatlistan star pa innehall ----------------------------------
def test_tillaten_strang_slapps_igenom(repo, capfd):
    (repo / "b.txt").write_text("koden ligger i " + TILLATEN_SOKVAG + "\n",
                                encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "andra")
    kod, ut = kor(repo, capfd)
    assert kod == 0
    assert "tillatna" in ut


def test_annan_strang_under_samma_monster_faller(repo, capfd):
    """En tillatlista pa filnamn hade vitlistat filen for all framtid."""
    (repo / "b.txt").write_text("sokvag " + SOKVAG + "\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "andra")
    kod, ut = kor(repo, capfd)
    assert kod == 1
    assert "lokal sokvag" in ut


def test_tillatlistan_redovisar_hur_ofta_varje_post_anvands(repo, capfd):
    """En post pa 0 x ar en post vars skal inte langre galler."""
    assert "0 x" in kor(repo, capfd)[1]


# ---- 5. tystnad ar det farligaste --------------------------------------
def test_utan_ordlista_sager_grinden_provades_inte(repo, capfd, monkeypatch, tmp_path):
    tom = tmp_path / "ingen_ordlista"
    tom.mkdir()
    monkeypatch.setattr(fore_push.config, "data_root", lambda: tom)
    kod, ut = kor(repo, capfd)
    assert kod == 2, "ett rent utfall utan ordlista ar det farligaste som finns"
    assert "PROVADES INTE" in ut
    assert "Rent" not in ut


def test_en_traff_vager_tyngre_an_saknad_ordlista(repo, capfd, monkeypatch, tmp_path):
    """Faller den pa nagot ska felkoden sage FALLER, inte provades-inte."""
    tom = tmp_path / "ingen2"
    tom.mkdir()
    monkeypatch.setattr(fore_push.config, "data_root", lambda: tom)
    (repo / "b.txt").write_text(EPOST + "\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "andra")
    assert kor(repo, capfd)[0] == 1


# ---- e-post --------------------------------------------------------------
def test_egen_doman_slapps_men_inte_andra(repo, capfd):
    (repo / "b.txt").write_text(EGEN + "\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "egen doman")
    assert kor(repo, capfd)[0] == 0
    (repo / "c.txt").write_text(EPOST + "\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "frammande doman")
    kod, ut = kor(repo, capfd)
    assert kod == 1
    assert "e-post" in ut


# ---- binart innehall far inte falla grinden pa ett undantag -------------
def test_binar_blob_kraschar_inte(repo, capfd):
    (repo / "bild.bin").write_bytes(bytes(range(256)) * 8)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "binart")
    kod, ut = kor(repo, capfd)
    assert kod == 0
    assert "binara blobbar" in ut


# ======================================================================
# TILLATLISTANS ATTA STALLEN FOR DejaVus LICENSTEXT
#
# Typsnitten lades i repot 2026-11-28. Licensen maste folja med och maste sta
# ordagrant - en redigerad licenstext ar ingen licens - och atta av dess rader
# faller under ordlistan: fem upphovspersoners adresser och tre meningar om vad
# som far och inte far goras kommersiellt. Ingen av dem ar projektets.
#
# Posterna ar STALLEN, (blob, radnr), och det ar TVINGANDE. En textpost hade
# skrivit ut adresserna i fore_push.py, och da bar grinden dem sjalv och faller
# pa sin egen tillatlista - docstringens punkt 3, en niva till.
#
# DET FELET INTRAFFADE ANDA, i skalstexten: den forsta lydelsen stavade ut
# licensens villkor med ett ord ur ordlistan, och grinden foll pa sin egen
# motivering. Testet nedan - att HELA tillatlistan passerar grinden den vaktar -
# ar skrivet for just det.
#
# Proven ror aldrig projektets repo. De laser TILLATET och licensfilens blob.
# ======================================================================

LICENSFILEN = "tools/fonts/LICENSE-DejaVu.txt"


def _arkivets_ordlista():
    """Arkivets riktiga ordlista. INGEN try/except: ett prov som hoppar over
    sig sjalvt for att ett funktionsnamn glidit ar ett prov som sager gront
    utan att ha provat nagot. Saknas filen hoppas provet over, och DET sags."""
    fil = fore_push.config.data_root() / fore_push.ORDLISTA
    if not fil.exists():
        pytest.skip("arkivets ordlista saknas - satt STATES_DATA")
    return [r.strip() for r in fil.read_text(encoding="utf-8").splitlines()
            if r.strip() and not r.startswith("#")]


def _git_rot(*a):
    return subprocess.run(["git", "-C", str(ROT), *a],
                          capture_output=True, text=True).stdout.strip()


def _dejavuposter():
    """Posterna som ar stallen. En post ar ett stalle nar vad:et inte ar text."""
    return [(m, v, skal) for m, v, skal in fore_push.TILLATET
            if not isinstance(v, str)]


kraver_licensfilen = pytest.mark.skipif(
    not (ROT / LICENSFILEN).exists(),
    reason="licensfilen saknas - typsnitten ar inte i det har tradet")


@kraver_licensfilen
def test_posterna_pekar_pa_licensfilens_egen_blob():
    """Blobben mats, den tas inte ur posten. En post som pinnar fel objekt
    slapper igenom ingenting och syns aldrig - den bara ligger dar."""
    blob = _git_rot("rev-parse", "HEAD:" + LICENSFILEN)
    assert len(blob) == 40, "hittar ingen blob for " + LICENSFILEN
    rader = sorted(v[1] for _, v, _ in _dejavuposter() if v[0] == blob)
    assert len(rader) == 8, (
        "forvantade atta poster pinnade till licensfilens blob, fick %d" % len(rader))
    assert len(set(rader)) == 8, "tva poster pekar pa samma rad: %s" % rader


@kraver_licensfilen
def test_varje_post_pekar_pa_en_rad_som_verkligen_faller():
    """En post vars rad inte traffar ar dekoration. Ordlistan ar arkivets, sa
    provet hoppas over utan den."""
    mon = fore_push.monster(_arkivets_ordlista())
    blob = _git_rot("rev-parse", "HEAD:" + LICENSFILEN)
    text = (ROT / LICENSFILEN).read_text(encoding="utf-8", errors="replace")
    traffar = {radnr: namn for namn, _, radnr, _ in fore_push.prova(text, mon)}
    for namn, (sha, radnr), _ in _dejavuposter():
        if sha != blob:
            continue
        assert radnr in traffar, (
            "post pa rad %d traffar ingenting - posten ar dekoration" % radnr)
        assert traffar[radnr] == namn, (
            "rad %d faller under %r, posten star under %r"
            % (radnr, traffar[radnr], namn))


def test_tillatlistan_passerar_sjalv_den_grind_den_vaktar():
    """DET HAR AR SKALET TILL ATT POSTERNA AR STALLEN.

    Varje skalstext i TILLATET lases av grinden som vilken annan rad som helst.
    Stavar en motivering ut det den motiverar faller grinden pa sin egen
    tillatlista - och den enda vagen ut ar att vitlista vitlistan, vilket ar
    samma sak som att ta bort grinden.

    Det intraffade 2026-11-28: skalstexten till DejaVus villkorsposter bar ett
    ord ur ordlistan, och grinden foll pa sin egen motivering."""
    mon = fore_push.monster(_arkivets_ordlista())
    brott = []
    for m, v, skal in fore_push.TILLATET:
        vad = v if isinstance(v, str) else "stalle"
        for namn, traffad, _, rad in fore_push.prova(skal, mon):
            # GRINDENS EGEN NYCKELSLAGNING, inte en strangare. En post som star
            # pa ORDET slapper igenom sitt eget skal, och det ar meningen -
            # posten for royalty forklarar varfor i sin egen text. Det provet
            # ska fanga ar ett skal som INGEN post tacker.
            if any(n in fore_push.TILLATNA
                   for n in ((namn, traffad), (namn, rad.strip()))):
                continue
            brott.append("%s | %s: skalet traffar %r och ingen post tacker det"
                         % (m, vad, namn))
    assert not brott, (
        "tillatlistans egna motiveringar faller under grinden:\n  "
        + "\n  ".join(brott))


@kraver_licensfilen
def test_en_andrad_licensfil_slutar_matcha():
    """Posten ar pinnad till innehallet, inte till filnamnet. Andras filen
    byter den blob och posterna slutar galla - grinden faller igen, och nagon
    far titta. Det ar ratt beteende for en licens."""
    import hashlib
    byte = (ROT / LICENSFILEN).read_bytes()
    def blobsha(b):
        h = hashlib.sha1()
        h.update(b"blob %d\0" % len(b)); h.update(b)
        return h.hexdigest()
    nu = blobsha(byte)
    assert nu == _git_rot("rev-parse", "HEAD:" + LICENSFILEN), (
        "testets egen blobrakning stammer inte - da provar resten ingenting")
    efter = blobsha(byte + b"\n")
    assert efter != nu
    pinnade = {v[0] for _, v, _ in _dejavuposter()}
    assert nu in pinnade
    assert efter not in pinnade, "en andrad fil skulle fortfarande vara vitlistad"


@kraver_licensfilen
def test_ingen_adress_och_ingen_licensmening_star_utskriven():
    """Kontroll mot att nagon senare gor om posterna till texter."""
    kallan = (ROT / "tools" / "fore_push.py").read_text(encoding="utf-8")
    licensen = (ROT / LICENSFILEN).read_text(encoding="utf-8", errors="replace")
    for radnr in (3, 33, 34, 48, 54, 55, 56, 57):
        rad = licensen.splitlines()[radnr - 1].strip()
        assert rad, "rad %d ar tom - radnumren har glidit" % radnr
        assert rad not in kallan, (
            "licensens rad %d star utskriven i fore_push.py" % radnr)
