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
