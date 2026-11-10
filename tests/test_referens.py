"""Referensen ar en fast punkt, och vilken punkt det var ska ga att se.

Testerna provar BETEENDE, inte kallkodstext. Den forra versionen av den har
filen bestod av assert "..." in inspect.getsource(...), och sadana tester kan
bara falla pa en omdopning: byttes sys.exit mot print i grinden, eller vandes
villkoret i referensfil(), stod strangarna kvar och testerna gronade vidare.
Det ar samma form som kallregistergrinden som provade filnamnet mot sig sjalv
- ett test som inte kan falla pa det det pastar sig prova.

Varje test har lagger darfor in ett tillstand, anropar funktionen och laser
resultatet.
"""
import hashlib, json, sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src")); sys.path.insert(0, str(ROT / "tools"))
import calibrate, bygg_referens, classify

V1 = "600_STATES_KALIBRERINGSBATTERI_v1.0_REFERENS.json"
V2 = "600_STATES_KALIBRERINGSBATTERI_v1.0_REFERENS_v2.0.json"

kraver_arkiv = pytest.mark.skipif(
    not classify.PROMPT_FILE.exists(),
    reason="dataarkivet saknas - satt STATES_DATA (se README)")


def rad(oid, enighet="3/3"):
    return {"observation_id": oid, "tile_index": 1, "primary_emotion": "Joy",
            "secondary_emotion": "Hope", "intensity": "0.50", "confidence": "0.60",
            "primary_agreement": enighet}


# --- referensfil(): vilken nollpunkt som valjs -------------------------------

def test_v1_valjs_nar_ingen_v2_finns(tmp_path, monkeypatch):
    monkeypatch.setattr(calibrate, "REMEDIATION", tmp_path)
    (tmp_path / V1).write_text("{}", encoding="utf-8")
    assert calibrate.referensfil().name == V1


def test_v2_valjs_sa_fort_den_finns(tmp_path, monkeypatch):
    """Vands villkoret faller det har testet. Den forra versionen letade bara
    efter bada filnamnen i kallkoden och sag ingen skillnad."""
    monkeypatch.setattr(calibrate, "REMEDIATION", tmp_path)
    (tmp_path / V1).write_text("{}", encoding="utf-8")
    (tmp_path / V2).write_text("{}", encoding="utf-8")
    assert calibrate.referensfil().name == V2


def test_valet_gors_vid_korning_inte_vid_import(tmp_path, monkeypatch):
    """v2.0 skriven efter importen ska plockas upp anda."""
    monkeypatch.setattr(calibrate, "REMEDIATION", tmp_path)
    (tmp_path / V1).write_text("{}", encoding="utf-8")
    assert calibrate.referensfil().name == V1
    (tmp_path / V2).write_text("{}", encoding="utf-8")
    assert calibrate.referensfil().name == V2


# --- referensstampel(): harkomsten i varje resultatpost ----------------------

def test_stampeln_bar_namn_och_ratt_hash(tmp_path):
    f = tmp_path / V2
    f.write_text('{"rader": []}', encoding="utf-8")
    st = calibrate.referensstampel(f)
    assert st["referens"] == V2
    assert st["referens_sha256"] == hashlib.sha256(f.read_bytes()).hexdigest()[:16]


def test_stampeln_foljer_filens_innehall(tmp_path):
    """Byts referensen ut maste hashen folja med, annars pekar posten pa ratt
    namn och fel innehall."""
    f = tmp_path / V2
    f.write_text('{"rader": []}', encoding="utf-8")
    forst = calibrate.referensstampel(f)["referens_sha256"]
    f.write_text('{"rader": [1]}', encoding="utf-8")
    assert calibrate.referensstampel(f)["referens_sha256"] != forst


# --- enighet_ur(): rakningen far inte tappa rader ---------------------------

def test_enigheten_raknas_per_niva():
    rader = [rad("a"), rad("b"), rad("c", "2/3"), rad("d", "1/3")]
    assert bygg_referens.enighet_ur(rader) == {3: 2, 2: 1, 1: 1}


def test_varde_utanfor_skalan_stoppar_bygget():
    """En rad med 0/3 skulle forut forsvinna tyst ur rakningen, och metat hade
    pastatt en enighet som inte summerade till antalet rader."""
    with pytest.raises(SystemExit) as e:
        bygg_referens.enighet_ur([rad("a"), rad("b", "0/3")])
    assert "summerar till 1 av 2" in str(e.value)


# --- bygg_meta(): star det nagot som korningen inte gjorde? -----------------

@kraver_arkiv
def test_metat_beskriver_den_korning_som_faktiskt_gjordes():
    bat = {"meta": {"kalla_dygn": "2026/308", "referensmodell": bygg_referens.MODELL,
                    "not": "ursprunglig not."}}
    m = bygg_referens.bygg_meta(bat, "20260101T000000Z", {3: 1, 2: 0, 1: 0})
    assert m["pass"] == bygg_referens.PASS
    assert m["modell"] == bygg_referens.MODELL
    assert m["form"] == "en observation per begaran, Batch API"
    assert m["byggd"] == "20260101T000000Z"
    # sokvagen till rasvaren ska peka dit korningen faktiskt skrev dem
    vantad = "kalibrering_rasvar/%s_en_i_taget_20260101T000000Z/" % bygg_referens.MODELL
    assert m["rasvar"] == vantad
    assert m["prompt_sha256"] == classify.sha(classify.PROMPT_FILE)
    assert m["spec_sha256"] == classify.sha(classify.SPEC_FILE)
    assert m["kalla_dygn"] == "2026/308"            # batteriets falt foljer med
    assert m["not"].startswith("ursprunglig not.")  # och skrivs inte over


@kraver_arkiv
def test_metat_sager_vad_den_ersatter():
    bat = {"meta": {"referensmodell": bygg_referens.MODELL}}
    m = bygg_referens.bygg_meta(bat, "20260101T000000Z", {3: 0, 2: 0, 1: 0})
    assert m["referens_version"] == "2.0"
    assert m["ersatter"] == V1


# --- grindarna i main(): provade, inte lasta ---------------------------------

def _batteri(tmp_path, modell):
    f = tmp_path / "batteri.json"
    f.write_text(json.dumps({"meta": {"referensmodell": modell, "kalla_dygn": "2026/308"},
                             "observationer": [{"observation_id": "OBS-A", "tile_index": 1}]}),
                 encoding="utf-8")
    return f


@kraver_arkiv
def test_en_befintlig_referens_skrivs_aldrig_over(tmp_path, monkeypatch):
    """Grinden anropas pa riktigt. Byts sys.exit mot print faller testet - det
    gjorde det inte nar testet bara letade efter if NY.exists() i kallan."""
    monkeypatch.setattr(bygg_referens, "BATTERI", _batteri(tmp_path, bygg_referens.MODELL))
    monkeypatch.setattr(bygg_referens, "NY", tmp_path / V2)
    (tmp_path / V2).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["bygg_referens.py", "--dry-run"])
    with pytest.raises(SystemExit) as e:
        bygg_referens.main()
    assert "finns redan" in str(e.value)


@kraver_arkiv
def test_torrkorning_gar_igenom_nar_ingen_referens_finns(tmp_path, monkeypatch):
    """Motprovet: utan befintlig fil ska samma vag ge torrkorning och ingen fil."""
    monkeypatch.setattr(bygg_referens, "BATTERI", _batteri(tmp_path, bygg_referens.MODELL))
    monkeypatch.setattr(bygg_referens, "NY", tmp_path / V2)
    monkeypatch.setattr(sys, "argv", ["bygg_referens.py", "--dry-run"])
    assert bygg_referens.main() == 0
    assert not (tmp_path / V2).exists()


@kraver_arkiv
def test_annan_modell_an_batteriets_stoppar_bygget(tmp_path, monkeypatch):
    """Modellen stod bara arvd ur batteriets meta: bytte nagon MODELL skrev
    referensen anda batteriets modellnamn, och metat hade ljugit."""
    monkeypatch.setattr(bygg_referens, "BATTERI", _batteri(tmp_path, "claude-haiku-5-5"))
    monkeypatch.setattr(bygg_referens, "NY", tmp_path / V2)
    monkeypatch.setattr(sys, "argv", ["bygg_referens.py", "--dry-run"])
    with pytest.raises(SystemExit) as e:
        bygg_referens.main()
    assert "referensmodell" in str(e.value)
