"""Grind: tidsstamplingen lovar inte mer an den gor, och tiger inte nar den gar fel.

Skrivet av den andra parten an den som skrev src/stamp.py, enligt AGENTS.md.

INGET PROV HAR ROR NATET ELLER KLIENTEN. Allt som nar ots gar genom stamp._kor,
och den byts ut. Det ar avsiktligt: en grind som bara gar att prova med natet
uppe gar inte att prova, och de nio stampelpaketen ska inte installeras i
projektets venv.

Talen i proven ar UPPMATTA pa NAS:en 2026-11-24 och kopierade ordagrant ur den
matningen - inte uppfunna for provet. Det galler sarskilt klientens utskrifter:
provet far inte definiera vad klienten sager.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))
import statepaths as sp
import gates
import stamp

DAG = "20261201"

# Ordagrant ur NAS:ens matning 2026-11-24, ots --no-bitcoin verify pa ett
# forankrat bevis. Fyra kalendrar, fyra block.
VERIFY_FORANKRAD = """Not checking Bitcoin attestation; Bitcoin disabled
To verify manually, check that Bitcoin block 977361 has merkleroot 8a1b66ecb7cbd07d8139a7e7d7f2c41aab1f5009b8364aaf61d03ad245e47e00
Not checking Bitcoin attestation; Bitcoin disabled
To verify manually, check that Bitcoin block 977363 has merkleroot 1f5009b8364aaf61d03ad245e47e008a1b66ecb7cbd07d8139a7e7d7f2c41aab
"""
# Ordagrant ur matningen kl. 12:22, atta minuter efter forsta blocket.
UPGRADE_VANTANDE = "Failed! Timestamp not complete"
UPGRADE_KLAR = "Got 1 attestation(s)\nSuccess! Timestamp complete"


@pytest.fixture
def arkiv(tmp_path):
    """Ett fryst emotionsmanifest och dess sidecar. Inget annat."""
    emo = sp.emotion_manifest(tmp_path, DAG)
    emo.parent.mkdir(parents=True, exist_ok=True)
    emo.write_text("tile_index,observation_id\n1,x\n", encoding="utf-8")
    sp.sha_sidecar(emo).write_text(
        hashlib.sha256(emo.read_bytes()).hexdigest() + "  " + emo.name, encoding="utf-8")
    return tmp_path


def stub(monkeypatch, svar):
    """svar: {forsta argumentet: (felkod, utskrift)} eller en funktion."""
    kallade = []

    def _k(*argv):
        kallade.append(argv)
        if callable(svar):
            return svar(*argv)
        nyckel = next((a for a in argv if not a.startswith("-")), "")
        return svar.get(nyckel, (0, ""))

    monkeypatch.setattr(stamp, "_kor", _k)
    return kallade


# ---------------------------------------------------------------- ren funktion

def test_attesteringar_laser_klientens_riktiga_utskrift():
    k = stamp.attesteringar(VERIFY_FORANKRAD)
    assert [x["block_height"] for x in k] == [977361, 977363]
    assert all(len(x["merkle_root"]) >= 32 for x in k)


def test_attesteringar_tar_bort_dubbletter():
    """Tva kalendrar kan landa i samma block. Samma attestering raknad tva
    ganger ar ett pastaende om fler vittnen an det finns."""
    assert len(stamp.attesteringar(VERIFY_FORANKRAD + VERIFY_FORANKRAD)) == 2


def test_attesteringar_ger_tom_lista_pa_text_utan_attestering():
    assert stamp.attesteringar("Failed! Timestamp not complete") == []
    assert stamp.attesteringar("") == []


# ---------------------------------------------------------------- stamplingen

def test_misslyckad_stampling_stoppar_inte_dygnet(arkiv, monkeypatch):
    """Fyra kalendrar som inte svarar 00:06 far inte kosta ett felfritt dygn."""
    stub(monkeypatch, {"stamp": (1, "connection refused"), "--version": (0, "ots v0.8.0")})
    post = stamp.step_stampla(DAG, arkiv)
    assert "stampel" not in post, "en misslyckad stampling far inte skriva en stampel"
    assert post["forsok"][-1]["felkod"] == 1
    assert post["forsok"][-1]["steg"] == "stampla"


def test_lyckad_stampling_racker_inte_for_publicering(arkiv, monkeypatch):
    """Stamplad ar inte forankrad. Grinden ska vara rod tills ett block finns."""
    emo = sp.emotion_manifest(arkiv, DAG)

    def svar(*argv):
        if "stamp" in argv:
            sp.ots_sidecar(emo).write_bytes(b"proof-pending")
            return 0, "Submitting to remote calendar"
        return 0, "ots v0.8.0"

    stub(monkeypatch, svar)
    post = stamp.step_stampla(DAG, arkiv)
    assert post["stampel"]["ots"].endswith(".ots")
    with pytest.raises(gates.GateFailure):
        gates.gate_forankrad_stampel(sp.state_id(DAG), post)


def test_stampling_gors_inte_om(arkiv, monkeypatch):
    emo = sp.emotion_manifest(arkiv, DAG)
    sp.ots_sidecar(emo).write_bytes(b"proof-pending")
    kallade = stub(monkeypatch, {})
    stamp.step_stampla(DAG, arkiv)
    assert not any("stamp" in a for a in kallade), "stampeln gjordes om"


def test_andrat_manifest_stoppar_fore_allt_annat(arkiv, monkeypatch):
    """Da ar det inte manifestet stampeln skulle intyga, och det ar inget natfel."""
    emo = sp.emotion_manifest(arkiv, DAG)
    emo.write_text("tile_index,observation_id\n1,NAGOT ANNAT\n", encoding="utf-8")
    kallade = stub(monkeypatch, {})
    with pytest.raises(gates.GateFailure):
        stamp.step_stampla(DAG, arkiv)
    assert kallade == [], "klienten anropades trots att manifestet andrats"


# ---------------------------------------------------------------- forankringen

def _stamplad(arkiv, monkeypatch):
    emo = sp.emotion_manifest(arkiv, DAG)
    sp.ots_sidecar(emo).write_bytes(b"proof-pending")
    stamp.skriv_post(DAG, {"day": DAG, "state_id": sp.state_id(DAG),
                           "manifest": emo.name,
                           "stampel": {"ots": sp.ots_sidecar(emo).name, "at": "2026-12-01T00:06:00Z"}},
                     arkiv)
    return emo


def test_forankring_utan_attestering_lamnar_otsen_orord(arkiv, monkeypatch):
    emo = _stamplad(arkiv, monkeypatch)
    fore = sp.ots_sidecar(emo).read_bytes()
    stub(monkeypatch, {"upgrade": (1, UPGRADE_VANTANDE), "verify": (1, "")})
    post = stamp.step_forankra(DAG, arkiv)
    assert "forankring" not in post
    assert sp.ots_sidecar(emo).read_bytes() == fore
    assert DAG in stamp.vantande(arkiv)


def test_lyckad_forankring_oppnar_publiceringsgrinden(arkiv, monkeypatch):
    emo = _stamplad(arkiv, monkeypatch)
    stub(monkeypatch, {"upgrade": (0, UPGRADE_KLAR), "verify": (1, VERIFY_FORANKRAD)})
    post = stamp.step_forankra(DAG, arkiv)
    assert len(post["forankring"]["kalendrar"]) == 2
    gates.gate_forankrad_stampel(sp.state_id(DAG), post)      # faller inte
    assert stamp.vantande(arkiv) == []


def test_forankring_gors_inte_om(arkiv, monkeypatch):
    emo = _stamplad(arkiv, monkeypatch)
    stub(monkeypatch, {"upgrade": (0, UPGRADE_KLAR), "verify": (1, VERIFY_FORANKRAD)})
    stamp.step_forankra(DAG, arkiv)
    kallade = stub(monkeypatch, {})
    stamp.step_forankra(DAG, arkiv)
    assert not any("upgrade" in a for a in kallade), "forankringen gjordes om"


def test_vantande_tar_aldst_forst(arkiv, monkeypatch):
    for d in ("20261203", "20261201", "20261202"):
        emo = sp.emotion_manifest(arkiv, d)
        emo.parent.mkdir(parents=True, exist_ok=True)
        stamp.skriv_post(d, {"day": d, "stampel": {"at": "x"}}, arkiv)
    assert stamp.vantande(arkiv) == ["20261201", "20261202", "20261203"]


# ------------------------------------------------- de tva jag kraver av koden

def test_oparsbar_utskrift_ar_inte_samma_sak_som_vantande(arkiv, monkeypatch):
    """Ett tyst misslyckande ar varre an ett hogljutt.

    Tva tillstand ser likadana ut for koden: "ingen attestering an" och "en
    utskrift jag inte kunde tolka". Bara det forsta ar normalt. Uppmatta
    felkoder fran klienten skiljer dem at: upgrade ger 1 med "Failed! Timestamp
    not complete" nar beviset ar ofullstandigt, och 0 med "Success! Timestamp
    complete" nar det ar helt.

    Sager klienten alltsa att beviset AR helt, och ingen blockhojd gar att lasa
    ur verifieringen, da har formatet andrats under oss. Dygnet far inte fastna
    som vantande i veckor tills nagon undrar varfor det inte publicerats.
    """
    _stamplad(arkiv, monkeypatch)
    stub(monkeypatch, {"upgrade": (0, UPGRADE_KLAR),
                       "verify": (1, "Bitcoin block height 977361, root 8a1b66ec")})
    with pytest.raises(gates.GateFailure):
        stamp.step_forankra(DAG, arkiv)


def test_otsen_gar_att_aterstalla_efter_en_skadad_upgrade(arkiv, monkeypatch):
    """ots upgrade skriver .ots PA PLATS, och den skrivningen ar klientens -
    den gar inte genom atomic. Ett avbrott mitt i skadar beviset, och beviset
    ar det enda som binder manifestet till ett block.

    Kravet: originalets bytes gar att fa tillbaka efter ett misslyckat forsok.
    Antingen ar filen orord, eller sa finns en kopia bredvid.
    """
    emo = _stamplad(arkiv, monkeypatch)
    ots = sp.ots_sidecar(emo)
    original = ots.read_bytes()

    def svar(*argv):
        if "upgrade" in argv:
            ots.write_bytes(b"\x00halvskriven")      # avbrott mitt i
            return 1, UPGRADE_VANTANDE
        return 1, ""

    stub(monkeypatch, svar)
    stamp.step_forankra(DAG, arkiv)

    kvar = [p for p in ots.parent.iterdir() if p.name.startswith(ots.name)]
    assert any(p.read_bytes() == original for p in kvar), (
        "originalets bytes gar inte att aterstalla: .ots ar skadad och ingen "
        f"kopia finns. Filer: {[p.name for p in kvar]}")


# ---------------------------------------------------------------- separationen

def test_stamplingen_nar_varken_farg_klassificering_eller_urval():
    """Stampeln intygar ett fardigt manifest; den tillverkar det inte. Samma
    princip som haller urval och farg atskilda, och provad pa samma satt:
    i en egen tolkprocess, mot vad som faktiskt hamnade i sys.modules."""
    kand = ["color_protocol", "render", "classify", "consensus", "select_day", "candidates"]
    kod = (f"import sys; sys.path.insert(0,{str(ROT/'src')!r}); sys.path.insert(0,{str(ROT)!r});"
           f"import stamp; print(','.join(m for m in {kand!r} if m in sys.modules))")
    ut = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True)
    assert ut.returncode == 0, ut.stderr
    assert ut.stdout.strip() == "", f"stamp.py drar in {ut.stdout.strip()}"


def test_den_publika_meningen_star_i_koden():
    """Claims gate i kod. Nasta lasare ska inte uppfinna en starkare
    formulering an den uppmatta: felkoden ar 1, och verifieringen ar manuell."""
    t = (ROT / "src" / "stamp.py").read_text(encoding="utf-8")
    for krav in ("--no-bitcoin verify", "FELKOD 1", "blockhojd", "merkle-rot",
                 "kraver en Bitcoin-nod"):
        assert krav in t, f"den publika meningen saknar: {krav}"
