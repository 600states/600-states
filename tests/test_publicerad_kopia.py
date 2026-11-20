"""Grind: protocols/ far inte glida fran arkivet.

Skrivet av den andra parten an den som byggde publiceringen i ddaade1, enligt
AGENTS.md.

config.FROZEN ar kallan. protocols/ ar en kopia, och en kopia ar ett andra
exemplar av samma sanning - FYND 004:s form, den har gangen mellan arkivet och
allmanheten. Glider de isar granskar varlden ett dokument som instrumentet inte
kor, och ingenting i en korning marker det: koden laser arkivet och bryr sig
inte om vad som ligger i repot.

Darfor maste kontrollen vara ett test. Den kan inte vara en rutin, for det finns
ingen korning den sitter i.

Fyra pastaenden:

  1. Varje publicerat dokument ar byte for byte arkivets.
  2. Inget dokument har tillkommit i kopian som inte finns i kallan.
  3. Den publicerade hashen ar dokumentets hash - manifestet far inte heller
     glida.
  4. Manifestet tacker varje dokument i katalogen. Ett dokument utan rad i
     manifestet ar opublicerat i praktiken: ingen kan kontrollera det.

Testerna hoppas over utan arkivet. Da finns ingen kalla att jamfora mot, och ett
test som da provar kopian mot sig sjalv vore varre an inget test.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))
import config

KOPIAN = ROT / "protocols"
MANIFEST = "MANIFEST_SHA256__600_STATES_PROTOCOLS_v1.0"
EJ_DOKUMENT = {"LICENSE", MANIFEST + ".txt", MANIFEST + ".json"}

kraver_arkiv = pytest.mark.skipif(
    not config.FROZEN.exists(),
    reason="dataarkivet saknas - satt STATES_DATA (se README)")


def dokument():
    """De publicerade protokollen: allt i protocols/ som inte ar riggning."""
    return sorted(p for p in KOPIAN.iterdir()
                  if p.is_file() and p.name not in EJ_DOKUMENT)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_katalogen_finns_och_ar_inte_tom():
    assert KOPIAN.is_dir(), "protocols/ saknas"
    assert len(dokument()) >= 12, f"forvantade minst 12 dokument, fick {len(dokument())}"


@kraver_arkiv
def test_varje_publicerat_dokument_ar_arkivets_byte_for_byte():
    """Bytes, inte rader. Kallregistret ar CRLF och de ovriga LF, sa en
    jamforelse som normaliserar radslut hade sluppit igenom precis den fil som
    .gitattributes finns till for att skydda."""
    avvikelser = []
    for p in dokument():
        kalla = config.FROZEN / p.name
        if not kalla.exists():
            avvikelser.append(f"{p.name}: finns i protocols/ men inte i arkivet")
        elif kalla.read_bytes() != p.read_bytes():
            avvikelser.append(
                f"{p.name}: kopian {sha(p)[:16]}, arkivet {sha(kalla)[:16]}")
    assert avvikelser == [], (
        "protocols/ har glidit fran config.FROZEN - varlden laser nagot annat "
        f"an instrumentet kor: {avvikelser}")


@kraver_arkiv
def test_radslut_bevarades_i_arbetstradet():
    """.gitattributes bar protocols/** -text. Hade den raden saknats skulle en
    Windows-klon och en Linux-klon fa olika bytes for kallregistret, och den
    publicerade hashen hade stamt pa hogst en av dem."""
    reg = KOPIAN / "600_STATES_Source_Registry_v2.0_FROZEN.csv"
    if not reg.exists():
        pytest.skip("kallregistret ar inte publicerat")
    kalla = config.FROZEN / reg.name
    assert reg.read_bytes() == kalla.read_bytes()
    assert b"\r\n" in kalla.read_bytes(), (
        "kallregistret var CRLF i arkivet nar grinden skrevs; ar det inte det "
        "langre ar antagandet bakom .gitattributes-raden borta")


def test_den_publicerade_hashen_ar_dokumentets():
    """Provas UTAN arkivet ocksa: manifestet och dokumenten ligger bada i
    repot, sa den som klonar ska kunna kontrollera dem mot varandra."""
    rader = _manifestrader()
    assert rader, "manifestets .txt ar tom eller gar inte att lasa"
    fel = [f"{namn}: manifestet sager {h[:16]}, filen ar {sha(KOPIAN / namn)[:16]}"
           for namn, h in rader.items()
           if (KOPIAN / namn).exists() and sha(KOPIAN / namn) != h]
    saknade = [namn for namn in rader if not (KOPIAN / namn).exists()]
    assert fel == [], f"publicerad hash stammer inte med filen: {fel}"
    assert saknade == [], f"manifestet namner filer som inte finns: {saknade}"


def test_de_tva_manifestformaten_sager_samma_sak():
    """.txt och .json skrivs i samma anrop och ska darfor inte kunna glida.
    "Darfor" ar ett resonemang om koden; det har ar kontrollen av det."""
    data = json.loads((KOPIAN / (MANIFEST + ".json")).read_text(encoding="utf-8"))
    ur_json = {e["path"]: e["sha256_file_bytes"].lower() for e in data["entries"]}
    assert ur_json == _manifestrader(), (
        "manifestets tva format sager olika saker om samma filer")
    assert data["file_count"] == len(ur_json), (
        f"file_count sager {data['file_count']}, posterna ar {len(ur_json)}")
    for e in data["entries"]:
        fil = KOPIAN / e["path"]
        if fil.exists():
            assert fil.stat().st_size == e["size_bytes"], f"{e['path']}: fel storlek"


def test_manifestet_tacker_varje_publicerat_dokument():
    """Ett dokument utan rad i manifestet gar inte att kontrollera. Da ar det
    publicerat men inte bevisbart, vilket ar samma sak som opublicerat for den
    som granskar."""
    rader = _manifestrader()
    utan = [p.name for p in dokument() if p.name not in rader]
    assert utan == [], f"publicerade dokument utan rad i manifestet: {utan}"


def _manifestrader():
    """{filnamn: sha256} ur manifestets .txt, i sha256sum-format."""
    txt = (KOPIAN / (MANIFEST + ".txt")).read_text(encoding="utf-8")
    ut = {}
    for rad in txt.splitlines():
        rad = rad.strip()
        if not rad or rad.startswith("#"):
            continue
        delar = rad.split(None, 1)
        if len(delar) == 2 and len(delar[0]) == 64:
            ut[delar[1].lstrip("*").strip()] = delar[0].lower()
    return ut
