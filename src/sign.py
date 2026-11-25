"""Signatur over det frysta emotionsmanifestets hash. SEPARAT PROGRAM.

    python3 src/sign.py signera [dygn]

EGEN KORNING, SAMMA CONTAINER SOM STAMPLINGEN. Programmet kors i
600-states-stampel, inte i kedjans image - se deploy/stampel.Dockerfile. Ett
signeringsverktyg hor inte hemma i det instrument som laser nyheter, av samma
skal som de nio Bitcoin-biblioteken inte gor det: den som kan rakna fram ett
manifest i samma miljo som intygar det kan inte visa att den lat bli. Darfor
importerar den har filen varken klassificering, fargprotokoll eller urval, och
far aldrig gora det. Den drar inte in ett enda nytt pip-paket: minisign ar en
binar ur Debian, inte ett bibliotek.

VERKTYGET AR MINISIGN, Ed25519. INTE GPG. Projektets eget skal: ett bevis ska
ga att kontrollera utan infrastruktur som kan forsvinna. GPG-verifiering
skickar i praktiken en granskare till en nyckelserver, med utgangsdatum och
aterkallelser pa kopet. minisign ar en binar, en publik nyckelfil, och
verifieringen ar ett kommando utan natverk.

VAD SOM SIGNERAS: MANIFESTETS SHA-256, INTE MANIFESTET. Hashen ligger redan pa
disk - frysningen skriver den som sidecar bredvid manifestet - och det ar den
filen som signeras. Signaturen laggs bredvid som egen fil och ANDRAR ALDRIG
det den bevisar; samma skal som att .ots-namnet aldrig fick ga in i manifestet.
Ett bevis som andrar det det bevisar ar inget bevis.

NYCKELN RORS INTE AV KODEN. Den privata nyckeln genereras av projektagaren och
nas bara som en sokvag i STATES_SIGN_KEY. Programmet oppnar den aldrig, skriver
aldrig ut dess innehall, och SKRUBBAR dess sokvag ur allt det loggar: minisign
skriver ut sokvagen den fick nar filen saknas, och en post som bar den vore en
sokvag i ett publikt arkiv. Den publika nyckeln ligger i repot och verifierar.

NYCKELN MASTE VARA UTAN LOSENORD (minisign -G -W). Uppmatt 2026-11-25 pa
minisign 0.12: en nyckel med losenord ber om det pa stdin, och med stdin
stangd - som i en container - avslutar klienten med felkod 2. Det ar inte en
installning som gar att kringga, det ar en egenskap hos klienten.

KLIENTENS KONTRAKT, UPPMATT 2026-11-25 pa minisign 0.12 ur Debian trixie:

    giltig signatur                     felkod 0
    signerad fil andrad                 felkod 1
    betrodd kommentar andrad            felkod 1
    fel publik nyckel                   felkod 1
    obetrodd kommentar andrad           felkod 0   (den ar inte signerad)
    nyckel-, signatur- eller filen bort felkod 2

Tre lagen, och grinden ska kunna falla i alla tre.

DEN BETRODDA KOMMENTAREN LASES UR KLIENTEN, aldrig ur var egen variabel. Samma
regel som stamplingen laser blockhojder ur ots-klienten: ett bevis som
verifieras av den som tillverkade det bevisar ingenting. Posten bar alltsa den
strang minisign sjalv skrev ut vid verifieringen.

DET HAR PROGRAMMET STOPPAR, TILL SKILLNAD FRAN STAMPLINGEN. Stamplingen far
inte stoppa pa ett fel, for den talar med fyra frammande kalendrar och ett
natavbrott 00:06 ar inte dygnets fel. Signeringen ror inget nat: misslyckas den
ar det nyckeln eller miljon som ar fel, och det blir inte battre i morgon.
Dygnet ar anda redan fryst och oskadat - det som stoppar ar den har korningen,
aldrig verket. Grinden pa publiceringen sager nej sa lange posten inte bar en
verifierad signatur.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
import gates
from atomic import write_text
from config import DATA, require_data

# Klienten anropas som ett program, inte som ett bibliotek. Ett enda stalle, sa
# att provkorningar kan peka om det utan att kodvagen blir en annan.
MINISIGN = "minisign"

# UPPHOVSIDENTITETEN. Byteidentisk med commitidentiteten och med strangen i
# PARAMETER_REGISTER 1.18 - inte en variant. Da star samma strang pa tva
# oberoende publika stallen, git-historiken och signaturen, och en lasare kan
# matcha dem mot varandra. Tva stavningar vore tva identiteter, och
# kontinuiteten ar hela pastaendet.
#
# ATT DE TRE ar samma strang provas inte har. Den grinden skrivs av annan part
# an den som byggde signeringen; en kontroll vars enda kalla ar raden ovan
# kontrollerar bara att raden ar lik sig sjalv.
UID = "600 STATES <archive@600states.com>"

# Den publika nyckeln ligger i repot och publiceras pa sajten. Sokvagen
# harleds ur modulens egen plats - ingen absolut sokvag star i koden, av samma
# skal som config.py anger for STATES_DATA.
PUBNYCKEL = HERE.parent / "600states.pub"

NYCKEL_ENV = "STATES_SIGN_KEY"


def _nyckel():
    """Sokvagen till den privata nyckeln. Las aldrig, skrivs aldrig ut."""
    v = (os.environ.get(NYCKEL_ENV) or "").strip()
    if not v:
        raise gates.GateFailure(
            f"{NYCKEL_ENV} ar inte satt - utan den finns ingen nyckel att "
            f"signera med. Den sats pa varden, aldrig i repot.")
    return v


def _kor(*argv, dolj=()):
    """(felkod, all utskrift med de givna strangarna utbytta).

    minisign skriver sina fel pa stderr, sa bada stromarna slas ihop. stdin
    stangs: en klient som fragar efter ett losenord ska falla med en felkod,
    inte hanga en korning som ingen tittar pa.

    DOLJ TAR SOKVAGAR, INTE BARA NYCKELN. Klienten skriver ut sokvagen den
    fick nar en fil saknas, och posten ar manifestets proveniensansprak - den
    kan citeras publikt. Varken nyckelns sokvag eller arkivets hor hemma dar,
    av samma skal som config.py anger for STATES_DATA.
    """
    r = subprocess.run([MINISIGN, *argv], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL)
    ut = (r.stdout or "") + (r.stderr or "")
    for hemligt, ersattning in dolj:
        if hemligt:
            ut = ut.replace(hemligt, ersattning)
    return r.returncode, ut


def klientversion():
    """Klientens egen versionsrad. Lases ur klienten, aldrig ur Dockerfilen:
    det ar den installerade klienten som signerar, inte den avsedda."""
    kod, ut = _kor("-v")
    rad = next((x.strip() for x in ut.splitlines() if x.strip()), "")
    return rad if kod == 0 and rad else f"okand (felkod {kod}: {ut.strip()[:120]})"


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _nu():
    """Nar steget kordes. Mater omvarlden och valjer ingenting - samma undantag
    som bevisens hamtningstidpunkt, se AGENTS.md."""
    return f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}"


def betrodd_kommentar(state_id, manifest_sha256):
    """Signaturens betrodda kommentar. EN rad, och den star bara har.

    Falten skiljs at av tva mellanslag, sa att strangen gar att dela pa
    blanksteg aven om nagot falt en dag innehaller ett enkelt.
    """
    return f"{UID}  {state_id}  {manifest_sha256}"


def las_post(day, data=DATA):
    p = sp.signature_record(data, day)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def skriv_post(day, post, data=DATA):
    """Posten vaxer, den skrivs inte over. Samma regel som tidsstampelposten:
    varje forsok laggs till, bade de som lyckades och de som inte gjorde det.
    En journal som tiger om sina luckor ar ett tyst osant pastaende, FYND 001.
    """
    return write_text(sp.signature_record(data, day),
                      json.dumps(post, ensure_ascii=False, indent=1))


def _verifiera(signerad, sig, dolj):
    """(felkod, utskrift, betrodd kommentar ur klienten).

    -Q skriver BARA den betrodda kommentaren och ingenting annat, sa den
    behover inte plockas ur en mening som kan formuleras om.
    """
    argv = ("-V", "-p", str(PUBNYCKEL), "-m", str(signerad), "-x", str(sig))
    kod, ut = _kor(*argv, dolj=dolj)
    kod_q, ut_q = _kor("-Q", *argv, dolj=dolj)
    tc = ut_q.strip() if kod_q == 0 else ""
    return kod, ut, tc


def step_signera(day, data=DATA):
    print(f"\n[signera] {sp.state_id(day)}")
    emo = gates.gate_frozen_emotion(day, data)
    sidecar = sp.sha_sidecar(emo)
    sig = sidecar.with_name(sidecar.name + ".minisig")
    post = las_post(day, data)
    if sig.exists():
        print(f"        {sig.name} finns redan - signaturen gors inte om")
        return post

    state_id = sp.state_id(day)
    manifest_sha = _sha(emo)
    tc = betrodd_kommentar(state_id, manifest_sha)
    version, start = klientversion(), _nu()
    nyckel = _nyckel()
    dolj = ((nyckel, "<nyckeln>"), (str(data), "<arkivet>"),
            (str(PUBNYCKEL.parent), "<repot>"))

    kod, ut = _kor("-S", "-s", nyckel, "-m", str(sidecar), "-x", str(sig),
                   "-t", tc, "-c", UID, dolj=dolj)
    post.setdefault("forsok", []).append(
        {"steg": "signera", "at": start, "felkod": kod,
         "klient": version, "utskrift": ut.strip()[:500]})
    post.update({"day": day, "state_id": state_id, "manifest": emo.name,
                 "manifest_sha256": manifest_sha, "signerar": sidecar.name})

    if kod != 0 or not sig.exists():
        skriv_post(day, post, data)
        raise gates.GateFailure(
            f"signeringen misslyckades (felkod {kod}): {ut.strip()[:200]}")

    # POSTEN BAR UTFALLET AVEN NAR DET AR DALIGT. En signatur som finns men
    # inte verifierar ar ett eget tillstand, och den som laser posten ska se
    # det i stallet for ett tomt falt - FYND 001. Det ar ocksa det enda satt
    # grindens verifieringskontroll gar att se falla: en post som bara skrivs
    # nar allt stammer gor den kontrollen omojlig att prova.
    ver_kod, ver_ut, ur_klienten = _verifiera(sidecar, sig, dolj)
    post["forsok"][-1].update({"felkod_verify": ver_kod,
                               "utskrift_verify": ver_ut.strip()[:500]})
    post["signatur"] = {
        "fil": sig.name, "sha256": _sha(sig),
        # UR KLIENTEN, inte ur var egen variabel: se modulens docstring. Tom
        # nar verifieringen inte gick igenom - da har klienten inte sagt nagot.
        "betrodd_kommentar": ur_klienten,
        "publik_nyckel": PUBNYCKEL.name,
        "publik_nyckel_sha256": _sha(PUBNYCKEL) if PUBNYCKEL.exists() else None,
        "klient": version, "at": start, "felkod_verify": ver_kod,
    }
    skriv_post(day, post, data)

    if ver_kod != 0 or not ur_klienten:
        raise gates.GateFailure(
            f"signaturen skrevs men verifierar inte mot {PUBNYCKEL.name} "
            f"(felkod {ver_kod}): {ver_ut.strip()[:200]}")

    print(f"        {sig.name}  sha256 {post['signatur']['sha256'][:16]}  ·  {version}")
    print(f"        betrodd kommentar: {ur_klienten}")
    return post


def main():
    args = sys.argv[1:]
    if (args[0] if args else "") != "signera":
        sys.exit(__doc__)
    require_data()
    day = args[1] if len(args) > 1 else sp.senast_stangda_dygnet(datetime.now(timezone.utc))
    try:
        step_signera(day)
    except gates.GateFailure as e:
        print(f"\nSIGNERINGEN STOPPAD: {e}"); sys.exit(1)
    print("\nKlart.")


if __name__ == "__main__":
    main()
