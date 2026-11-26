"""Grind: upphovsidentiteten ar EN strang, pa tre oberoende stallen.

PARAMETER_REGISTER 1.18 faststallde 2026-11-25 att upphovet ar `600 STATES`,
en pseudonym med kontinuitet, och att signaturens UID ska vara BYTEIDENTISK
med commitidentiteten. Skalet ar inte prydlighet: da star samma strang pa tva
oberoende publika stallen - git-historiken och signaturen - och en lasare kan
matcha dem mot varandra utan att fraga oss. Tva stavningar vore tva
identiteter, och kontinuiteten ar hela pastaendet.

src/sign.py rad 86-88 sager sjalv att den grinden INTE hor hemma dar:
"en kontroll vars enda kalla ar raden ovan kontrollerar bara att raden ar lik
sig sjalv". Den star darfor har, skriven av annan part an den som byggde
signeringen, enligt AGENTS.md.

DE TRE KALLORNA, och de ar oberoende:

  1. src/sign.py UID            - repots konstant
  2. git HEAD:s forfattarfalt   - matt med git, inte last ur en fil
  3. betrodd_kommentar i dygnets signaturpost - och den kommer UR MINISIGNS
     EGEN UTSKRIFT, inte ur var variabel (sign.py rad 222-229). Det ar det
     som gor kalla 3 till ett bevis och inte ett eko.

Kalla 3 kraver att signaturtjansten har kort skarpt. Tills dess hoppas de
proven over, och DET SYNS i utskriften - ett overhoppat prov ar inte ett
godkant prov. A12 i lagesdokumentet ar den posten.

ADRESSEN VAR TVA, OCH RATTADES. 137 commits bar archive@600states.com, 48 bar
noreply@600states.com, och rattelsen skedde 2026-11-11. Namnet var detsamma i
samtliga. Provet nedan kraver darfor inte att hela historiken ar ren - det
kraver att INGEN commit efter rattelsen bar den gamla adressen. En grind som
krav de 48 vore en grind som bara gar att uppfylla genom att skriva om
historiken, och historiken skrivs inte om.

DODSMATRIS, korda mutationer:
  sign.UID far en variant ("600STATES <...>")  -> sign_ar_samma_som_git  FALLER
  sign.UID far en annan adress                 -> sign_ar_samma_som_git  FALLER
  UID-strangen skrivs en andra gang i src/     -> en_enda_stavning       FALLER

Skriven av den andra parten an den som byggde signeringen, enligt AGENTS.md.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))
import sign
import statepaths as sp

RATTELSEN = "2026-11-11"          # historikomskrivningen, se AGENTS.md
GAMMAL_ADRESS = "noreply@600states.com"


def git(*argv):
    r = subprocess.run(["git", *argv], cwd=ROT, capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(argv)}: {r.stderr.strip()}"
    return r.stdout.strip()


# ---------- kalla 1 mot kalla 2 ----------

def test_sign_UID_ar_samma_strang_som_git_HEADs_forfattare():
    """Byteidentisk. Inte "samma person" - samma strang."""
    assert sign.UID == git("log", "-1", "--format=%an <%ae>"), (
        "signaturens UID och commitidentiteten har glidit isar. Da star tva "
        "strangar pa de tva publika stallen som ska bekrafta varandra.")


def test_ingen_commit_efter_rattelsen_bar_den_gamla_adressen():
    """Historiken skrivs inte om - men den far inte glida tillbaka heller."""
    ut = git("log", f"--since={RATTELSEN}", "--format=%H %ae")
    fel = [r for r in ut.splitlines() if r.endswith(GAMMAL_ADRESS)]
    assert not fel, (
        f"{len(fel)} commit(s) efter {RATTELSEN} bar {GAMMAL_ADRESS}: "
        + ", ".join(r.split()[0][:8] for r in fel[:5]))


def test_kontrollprov_historiken_BAR_den_gamla_adressen_fore_rattelsen():
    """Utan detta kan provet ovan inte skilja "ingen glidning" fran
    "git svarar inte" eller "filtret matchar ingenting"."""
    ut = git("log", f"--until={RATTELSEN}", "--format=%ae")
    assert GAMMAL_ADRESS in ut, (
        "den gamla adressen finns inte i historiken fore rattelsen - da mater "
        "provet ovan inte det det tror sig mata.")


# ---------- en enda stavning i koden ----------

def test_en_enda_stavning_av_identiteten_i_koden():
    """FYND 004:s form. En strang som star pa tva stallen blir tva strangar."""
    traffar = []
    for p in sorted((ROT / "src").rglob("*.py")) + sorted((ROT / "tools").rglob("*.py")):
        for n, rad in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if sign.UID in rad:
                traffar.append(f"{p.relative_to(ROT)}:{n}")
    assert traffar == ["src/sign.py:88"], (
        f"identiteten star pa {len(traffar)} stallen: {traffar}. Den hor "
        f"hemma i sign.UID och lases darifran.")


# ---------- kalla 3: minisigns egen utskrift ----------

def signaturposter():
    """Alla signaturposter i arkivet. Tom lista nar arkivet saknas."""
    try:
        from config import DATA
    except Exception:
        return []
    rot = Path(DATA) / sp.GENERATION_DIR
    if not rot.exists():
        return []
    return sorted(rot.glob("STATE_*/600_STATES_*_SIGNATURE.json")) or \
        [p for p in rot.rglob("*.json") if "SIGNATURE" in p.name.upper()]


POSTER = signaturposter()
kraver_signatur = pytest.mark.skipif(
    not POSTER,
    reason="ingen signaturpost i arkivet - signatur-tjansten har aldrig kort "
           "skarpt (A12). Overhoppat ar inte godkant.")


@kraver_signatur
def test_den_betrodda_kommentaren_bar_samma_UID():
    """Kallan ar minisigns utskrift, inte var variabel - sign.py rad 222-229."""
    for p in POSTER:
        post = json.loads(p.read_text(encoding="utf-8"))
        tc = (post.get("signatur") or {}).get("betrodd_kommentar") or ""
        assert tc, f"{p.name}: tom betrodd kommentar - verifieringen gick inte igenom"
        assert tc.startswith(sign.UID), (
            f"{p.name}: den betrodda kommentaren borjar inte med sign.UID.\n"
            f"  klienten sade: {tc[:80]!r}\n  repot sager:    {sign.UID!r}")


@kraver_signatur
def test_den_betrodda_kommentarens_form_ar_UID_stateid_manifesthash():
    """Formen kommer ur sign.betrodd_kommentar(). Andras den ska provet veta."""
    for p in POSTER:
        post = json.loads(p.read_text(encoding="utf-8"))
        tc = (post.get("signatur") or {}).get("betrodd_kommentar") or ""
        vantat = sign.betrodd_kommentar(post["state_id"], post["manifest_sha256"])
        assert tc == vantat, f"{p.name}:\n  klienten: {tc!r}\n  koden:    {vantat!r}"
