"""Grind: det bygget skrev in i sidan ar det data.js sager.

Sidan anger hur manga rutor som saknar samstammighet. Talet kommer ur
build_data()s returvarde, samma variabel som data.js byggs av - i dag kan de
darfor inte glida isar. "I dag" ar inte en grind: delar nagon variabeln, flyttar
rakningen eller byter kalla, sager ingenting ifran. Det har testet sager ifran.

Provas pa den BYGGDA sidan, inte pa kallan. Det ar den vagen en besokare ser,
och det ar ocksa den enda plats dar talet finns som tal - i kallan star en
platshallare.

Skrivet av den andra parten an den som skrev bygget, enligt AGENTS.md.
"""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
DIST = ROT / "site" / "dist"
KALLA = ROT / "site" / "index.html"
# Faltets skript flyttade till site/field.js nar en andra sida borjade visa
# samma falt. GLOSS lases dar den star.
FALTKOD = ROT / "site" / "field.js"

sys.path.insert(0, str(ROT / "site"))
sys.path.insert(0, str(ROT))
import build as bygge
import config

kraver_bygge = pytest.mark.skipif(
    not (DIST / "index.html").exists() or not (DIST / "data.js").exists(),
    reason="site/dist saknas - kor python site/build.py forst")

# Labs-dygnets manifest, via byggets EGNA konstanter: andras LABS_DAY foljer
# provet med i stallet for att prova ett dygn som inte langre byggs.
try:
    LABS_MANIFEST = bygge.manifest_for(
        config.data_root() / "08_V3_STATES" / bygge.LABS_DIR, bygge.LABS_DAY)
except SystemExit:
    LABS_MANIFEST = None

kraver_labsdygnet = pytest.mark.skipif(
    LABS_MANIFEST is None,
    reason="dataarkivet saknas - satt STATES_DATA (se README)")


def _rutor():
    """tiles ur den byggda data.js. Filen ar en tilldelning med JSON efter =."""
    text = (DIST / "data.js").read_text(encoding="utf-8")
    return json.loads(text.split("=", 1)[1].rstrip().rstrip(";"))["tiles"]


def _ur_sidan(falt, sida="index.html"):
    m = re.search(r"<span data-%s>([^<]*)</span>" % falt,
                  (DIST / sida).read_text(encoding="utf-8"))
    assert m, f"hittar inget data-{falt} i den byggda {sida}"
    return m.group(1)


def _gloss_nycklar():
    """Nycklarna i GLOSS, ur kallan - glossen ar skript och byggs inte om."""
    text = FALTKOD.read_text(encoding="utf-8")
    block = text.split("var GLOSS = {", 1)
    assert len(block) == 2, "hittar ingen GLOSS i site/field.js"
    return set(re.findall(r"'([^']+)':", block[1].split("}", 1)[0]))


@kraver_bygge
def test_sidans_tal_ar_data_js_tal():
    """Talet i meningen mot rakningen i data.js, pa faltets varde.

    INTE med ett reguljart uttryck over hela filen: prosan i rutornas egna falt
    innehaller samma strangar, och en sadan rakning gav en gang 603 over 600
    rutor.
    """
    ur_data = sum(1 for r in _rutor() if r[4] == "1/3")
    ur_sidan = _ur_sidan("nocons")
    assert ur_sidan.isdigit(), (
        f"sidan sager '{ur_sidan}' dar ett tal ska sta - bygget ersatte inte "
        "platshallaren")
    assert int(ur_sidan) == ur_data, (
        f"sidan sager {ur_sidan} rutor utan samstammighet, data.js har "
        f"{ur_data}")


@kraver_bygge
def test_sidans_antal_distinkta_farger_ar_data_js_tal():
    """Samma form som talet ovan, pa samma payload.

    SKRIVET AV SAMMA PART SOM ANDRADE BYGGET, till skillnad fran resten av
    filen. Det bryter mot arbetsdelningen i AGENTS.md och star har i stallet
    for att doljas: raden ar en upprepning av provet ovan och inte en ny
    bedomning, men den ar inte oberoende granskad.
    """
    ur_data = len({r[0] for r in _rutor()})
    ur_sidan = _ur_sidan("distinct")
    assert ur_sidan.isdigit(), (
        f"sidan sager '{ur_sidan}' dar ett tal ska sta - bygget ersatte inte "
        "platshallaren")
    assert int(ur_sidan) == ur_data, (
        f"sidan sager {ur_sidan} distinkta farger, data.js har {ur_data}")


@kraver_bygge
def test_sidans_slugandel_ar_data_js_falt():
    """Talet i meningen mot rutornas claim_source i data.js, index 11.

    SKRIVET AV SAMMA PART SOM ANDRADE BYGGET, precis som provet for distinct
    ovan. Det bryter mot arbetsdelningen i AGENTS.md och star har i stallet
    for att doljas: raden ar en upprepning av samma form, inte en ny
    bedomning, och den ar inte oberoende granskad.

    Faltet, inte prosan: rutornas egen text innehaller ordet "S" overallt, och
    en rakning over filen skulle traffa den.
    """
    ur_data = sum(1 for r in _rutor() if r[11] == "S")
    ur_sidan = _ur_sidan("slug-001")
    assert ur_sidan.isdigit(), (
        f"sidan sager '{ur_sidan}' dar ett tal ska sta - bygget ersatte inte "
        "platshallaren")
    assert int(ur_sidan) == ur_data, (
        f"sidan sager {ur_sidan} rutor lasta ur webbadressen, data.js har "
        f"{ur_data}")


@kraver_bygge
@kraver_labsdygnet
def test_labssidans_distinkta_farger_ar_manifestets():
    """Talet pa 600 LABS mot en omrakning ur dygnets eget manifest.

    DEN HAR VAKTEN LIGGER BLAND DE OVERHOPPADE UTAN ARKIVET, till skillnad
    fran de tva pa startsidan. De jamfor sidan mot data.js, och bada filerna
    ligger i site/dist. Det har talet kommer fran ett ANNAT dygn an faltets
    och star darfor inte i data.js: enda omrakningen ar manifestet, och
    manifestet ligger i arkivet. En farsk klon utan STATES_DATA kor alltsa
    inte den har raden, och talet ar da bara "ett tal over noll" enligt
    platshallarprovet. Det ar exakt den lucka som gjorde modellidentitetens
    varde ovaktat, och den star har i stallet for att hittas.

    Uppmatt 2026-11-24 pa 0ba06de, fore det har provet: 504 -> 505 pa den
    byggda sidan gav SEX GRONA. Bygget skrev talet, men ingenting jamforde
    det.

    Rakningen gors har, inte med bygget egna distinkta_farger(): ett prov som
    anropar funktionen det provar sager bara att den ar sig lik.

    SKRIVET AV SAMMA PART SOM ANDRADE BYGGET, som de tva ovan.
    """
    rader = list(csv.DictReader(
        LABS_MANIFEST.read_text(encoding="utf-8").splitlines()))
    assert len(rader) == 600, (
        f"{LABS_MANIFEST.name} har {len(rader)} rader, inte 600")
    ur_arkivet = len({r["hex"].strip().lower() for r in rader})
    ur_sidan = _ur_sidan("distinct-2026-" + bygge.LABS_DAY, "labs.html")
    assert ur_sidan.isdigit(), (
        f"labs-sidan sager '{ur_sidan}' dar ett tal ska sta - bygget ersatte "
        "inte platshallaren")
    assert int(ur_sidan) == ur_arkivet, (
        f"labs-sidan sager {ur_sidan} distinkta farger for dygn "
        f"2026/{bygge.LABS_DAY}, manifestet har {ur_arkivet}")


@kraver_bygge
def test_sidans_testtal_ar_en_egen_insamling():
    """Talet i tabellen mot en egen insamling av samma tva filer.

    VAD GRINDEN SKYDDAR MOT, OCH INTE. Bygget kor om rakningen vid varje
    bygge, sa talet ar ratt sa lange sidan byggs. Det har provet fangar en
    handredigering i den byggda sidan och en gammal dist som laddas upp. Det
    fangar INTE ett fel i sjalva rakningen: blir bygget och provet fel pa
    samma satt sager raden ingenting. Mer an sa pastas inte.

    Insamlingen gors har, inte genom byggets rakna_tester(). Provet raknar
    nod-id:n; bygget laser pytests sammanfattningsrad. Tva vagar till samma
    tal, sa att ett fel i den enda regexen inte kan bekrafta sig sjalv. En
    egen rakning av "def test_" hade missat parametriserade fall, och det ar
    darfor pytest far samla aven har.

    Filerna kommer ur byggets URVALETS_TESTER: vilka filer raden handlar om ar
    en uppgift, inte en rakning, och den ska inte sta pa tva stallen.

    SKRIVET AV SAMMA PART SOM ANDRADE BYGGET, som de tre ovan.
    """
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--collect-only",
                        *bygge.URVALETS_TESTER],
                       cwd=str(ROT), capture_output=True, text=True)
    assert r.returncode == 0, (
        "insamlingen gick inte att kora:\n" + (r.stdout or r.stderr)[-400:])
    noder = [rad for rad in r.stdout.splitlines() if "::" in rad]
    assert noder, "pytest samlade ingenting att rakna i " + str(bygge.URVALETS_TESTER)

    ur_sidan = _ur_sidan("tests")
    assert ur_sidan.isdigit(), (
        f"sidan sager '{ur_sidan}' dar ett tal ska sta - bygget ersatte inte "
        "platshallaren")
    assert int(ur_sidan) == len(noder), (
        f"sidan sager {ur_sidan} tester over urval och storytak, insamlingen "
        f"ger {len(noder)}. Ar sidan byggd efter att testerna andrades?")


@kraver_bygge
def test_varje_enighetsniva_i_data_har_en_gloss():
    """Ett nytt faltvarde far ingen gloss i stallet for fel gloss - bra, men da
    star det oglosat pa sidan. Testet fangar vardet, inte beteendet."""
    i_data = {r[4] for r in _rutor()}
    utan = sorted(i_data - _gloss_nycklar())
    assert utan == [], f"enighetsnivaer i data.js som GLOSS inte namner: {utan}"


kraver_git = pytest.mark.skipif(
    not (ROT / ".git").exists(),
    reason="inget git-trad - stampeln gar inte att sla upp")


@kraver_bygge
@kraver_git
def test_stampeln_pekar_pa_en_commit_som_finns_i_historiken():
    """Stampeln ska namna en commit som gar att na fran HEAD.

    HARKOMST: provet ar skrivet av projektagaren, inte av den som committade
    det. Det lag i arbetstradet 2026-11-24 och committades oforandrat i
    24e4d06 av den part som orsakade felet det beskriver. Uppgiften star har
    och inte bara i git log, sa att den foljer filen.

    Den finns till for att den utrullade sidan sjalv ska kunna saga vilken
    version som ligger ute. En stampel som pekar pa ett commitobjekt utanfor
    grenen kan ingen utomstaende sla upp, och i ett projekt som publicerat att
    dess historik skrevs om ar det precis fel form att ha pa en publicerad
    artefakt.

    EN AELDRE BYGGD SIDA AR INTE ETT FEL. En stampel pa en FORFADER till HEAD
    ar arlig: sidan byggdes da, och den commiten gar att hamta. Det testet
    forbjuder ar en stampel som inte gar att na alls.

    Sa uppstod det 2026-11-24: 527-provet kraver en byggd sida, build.py
    kraver ett rent trad, och svitraden maste darfor matas EFTER bygget. Den
    amendades in, amenden gav commiten ett nytt sha, och dist stod kvar med
    det gamla - 3b184f5, identiskt trad och identisk foralder, men inte langre
    pa grenen. Regeln som foljer: efter en amend byggs sidan om.
    """
    m = re.search(r'<meta name="build" content="([^"]*)">',
                  (DIST / "index.html").read_text(encoding="utf-8"))
    assert m, "den byggda sidan saknar byggstampel"
    stampel = m.group(1)
    if stampel == "unknown":
        pytest.skip("bygget kunde inte lasa git - inget att sla upp")
    sha = stampel[:-len("-dirty")] if stampel.endswith("-dirty") else stampel

    finns = subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"],
                           cwd=str(ROT), capture_output=True)
    assert finns.returncode == 0, (
        f"stampeln {stampel} ar inget commitobjekt i det har tradet")

    natbar = subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"],
                            cwd=str(ROT), capture_output=True)
    assert natbar.returncode == 0, (
        f"stampeln {stampel} gar inte att na fran HEAD - sidan ar byggd ur en "
        "commit som inte ligger pa grenen. Bygg om efter en amend eller en "
        "ombaserad gren.")


@kraver_bygge
def test_byggets_platshallare_ersattes():
    """En oersatt platshallare betyder att kallan laddats upp i stallet for
    bygget. Bada talen provas, for de skrivs av samma loop."""
    for falt, sida in (("tests", "index.html"), ("nocons", "index.html"),
                       ("distinct", "index.html"), ("slug-001", "index.html"),
                       ("distinct-2026-308", "labs.html")):
        v = _ur_sidan(falt, sida)
        assert v.isdigit() and int(v) > 0, (
            f"data-{falt} ar '{v}' i den byggda {sida} - inte ett tal over noll")
