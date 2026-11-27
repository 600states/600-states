"""Tidsstampling av det frysta emotionsmanifestet. SEPARAT PROGRAM.

    python3 src/stamp.py stampla  [dygn]
    python3 src/stamp.py forankra [dygn]

EGEN CONTAINER, EGEN LASFIL. Programmet kors i 600-states-stampel, inte i
kedjans image - se deploy/stampel.Dockerfile. Nio Bitcoin- och git-bibliotek
hor inte hemma i det instrument som laser nyheter, och en stampel intygar ett
fardigt manifest; den tillverkar det inte. Samma princip som haller urval och
farg atskilda. Darfor importerar den har filen varken klassificering,
fargprotokoll eller urval, och far aldrig gora det.

TVA STEG, OCH DE LIGGER I OLIKA KORNINGAR:

    stampla    direkt efter att emotionsmanifestets sha256-sidecar skrivits.
               Resultatet ar <manifest>.ots med fyra vantande
               kalenderattesteringar.
    forankra   i NASTA dygns korning B, pa foregaende dygns .ots.

Skalet till att forankringen ligger ett dygn senare: sex bekraftelser tar
langre tid an forsta blocket, och en korning ska aldrig vanta pa en extern
kedja. Uppmatt pa varden 2026-11-24: forsta blocket efter ca 57 minuter, alla
fyra kalendrar inom ca 5,5 timmar, och en upgrade atta minuter efter forsta
blocket lyckades inte.

Misslyckas forankringen lamnas .ots orord och forsoket skrivs i posten.
Nasta dygns korning tar om den - forsoket, aldrig stampeln.

TVA TILLSTAND SOM SER LIKADANA UT, OCH FELKODEN SKILJER DEM AT. Noll
attesteringar betyder antingen "inte an" eller "jag kan inte lasa svaret", och
bara det forsta ar normalt. Uppmatt pa varden 2026-11-24, bada riktningarna:

    ots upgrade, beviset OFULLSTANDIGT : felkod 1, "Failed! Timestamp not complete"
    ots upgrade, beviset HELT          : felkod 0, "Got 1 attestation(s)"
                                         + "Success! Timestamp complete"

Sager klienten att beviset ar helt medan verifieringens utskrift inte gar att
lasa har utskriftsformatet andrats under oss, och da STOPPAR programmet. Ett
dygn som ligger kvar som vantande i veckor tills nagon undrar varfor det inte
publicerats ar dyrare an en krasch samma natt.

STAMPLINGEN STOPPAR INGENTING. Fyra externa kalendrar som inte svarar 00:06
far inte kosta ett annars felfritt dygn; ett dygn gar inte att gora om. Ett
misslyckat stamplingsforsok ger darfor en varning och felkod 0, och utfallet
skrivs i posten. Grinden som kan falla sitter pa PUBLICERINGEN i stallet - se
gates.gate_forankrad_stampel, som kors av run_color.py:s sista steg.

Precis en sak stoppar det har programmet: ett manifest som inte ar fryst,
eller som andrats sedan frysningen. Da ar det inte manifestet stampeln skulle
intyga, och det ar inget natverksfel.

VAD SOM LAMNAR MASKINEN: filens SHA-256, inget annat. Uppmatt 2026-11-24:
felkod 0, 2 577 ms.
"""
import hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
import gates
from atomic import write_text, write_bytes
from config import DATA, require_data

# Klienten anropas som ett program, inte som ett bibliotek. Ett enda stalle, sa
# att provkorningar kan peka om det utan att kodvagen blir en annan.
OTS = "ots"

# Raden ots --no-bitcoin verify skriver ut. Talen lases UR KLIENTEN, aldrig ur
# ett eget bygge av beviset: ett bevis som verifieras av den som tillverkade
# det bevisar ingenting.
ATTESTERING = re.compile(r"Bitcoin block (\d+) has merkleroot ([0-9a-fA-F]{32,})")


def _dolj(data):
    """Sokvagar som inte hor hemma i en post som kan citeras publikt."""
    return ((str(data), "<arkivet>"),)


def _kor(*argv, dolj=()):
    """(felkod, all utskrift med de givna strangarna utbytta).

    Klienten loggar pa stderr, sa bada stromarna slas ihop.

    DOLJ TAR SOKVAGAR. Klienten skriver ut sokvagen den fick - "Assuming
    target filename is '/srv/...'" - och den raden hamnade ordagrant i
    tidsstampelpostens falt utskrift. Posten ar manifestets
    proveniensansprak och kan citeras publikt; vardens sokvagar hor inte
    hemma dar, av samma skal som config.py anger for STATES_DATA.

    Regeln fanns redan, men bara i ett av de tva bevisprogrammen: sign._kor
    bar den sedan tidigare och den har gjorde det inte. En regel med tva
    svar ar FYND 004:s form. Programmen delar med avsikt ingen kod - de ar
    tva korningar med olika behorighet - sa raden star pa bada stallena och
    ar avsiktligt likalydande. A26.
    """
    r = subprocess.run([OTS, *argv], capture_output=True, text=True)
    ut = (r.stdout or "") + (r.stderr or "")
    for hemligt, ersattning in dolj:
        if hemligt:
            ut = ut.replace(hemligt, ersattning)
    return r.returncode, ut


def klientversion():
    """Klientens egen versionsrad. Lases ur klienten, aldrig ur lasfilen: det
    ar den installerade klienten som stamplar, inte den avsedda."""
    kod, ut = _kor("--version")
    rad = next((x.strip() for x in ut.splitlines() if x.strip()), "")
    return rad if kod == 0 and rad else f"okand (felkod {kod}: {ut.strip()[:120]})"


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _nu():
    """Nar steget kordes. Mater omvarlden och valjer ingenting - samma undantag
    som bevisens hamtningstidpunkt, se AGENTS.md."""
    return f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}"


def kopia_fore_upgrade(ots):
    """Originalets bytes bredvid .ots, skrivna av oss och genom atomic.

    ots upgrade skriver .ots PA PLATS, och den skrivningen ar klientens - den
    gar inte genom atomic och ett avbrott mitt i den kan skada filen. Beviset
    ar det enda som binder manifestet till ett block och gar inte att
    aterskapa: en ny stampel skulle binda manifestet till ett SENARE block och
    gora det aldsta beviset varre. Efter ett forsok som inte lyckades ska
    originalets bytes darfor alltid ga att fa tillbaka.
    """
    k = ots.with_name(ots.name + ".fore-upgrade")
    # EN BEFINTLIG KOPIA SKRIVS INTE OVER. Ligger den kvar har ett forsok
    # gjorts utan att lyckas, och da ar dess bytes originalet - inte det
    # klienten kan ha hunnit skriva i .ots sedan dess.
    return k if k.exists() else write_bytes(k, ots.read_bytes())


def attesteringar(text):
    """Blockhojd och merkle-rot per kalender, ur verifieringens utskrift.

    TXID SKRIVS INTE UT FOR MER AN EN AV FYRA KALENDRAR av klienten, sa den
    publiceras inte. Blockhojd och merkle-rot skrivs for alla fyra, och det ar
    anda de som gar att sla upp.

    Dubbletter tas bort: tva kalendrar kan landa i samma block, och samma
    attestering raknad tva ganger ar ett pastaende om fler vittnen an det finns.
    """
    ut = []
    for hojd, rot in ATTESTERING.findall(text):
        post = {"block_height": int(hojd), "merkle_root": rot.lower()}
        if post not in ut:
            ut.append(post)
    return ut


def las_post(day, data=DATA):
    p = sp.timestamp_record(data, day)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def skriv_post(day, post, data=DATA):
    """Posten vaxer, den skrivs inte over.

    Den ar stamplingens korjournal och manifestets proveniensansprak, och den
    far inte beskriva det sista forsoket utan alla. Varje forsok laggs till i
    "forsok", bade de som lyckades och de som inte gjorde det. En journal som
    tiger om sina luckor ar ett tyst osant pastaende - regeln star sedan
    FYND 001. Ett dygn som behovde fyra natter pa sig ska synas som det.
    """
    return write_text(sp.timestamp_record(data, day),
                      json.dumps(post, ensure_ascii=False, indent=1))


def _matpost(day, post, data):
    """Matpunkt 9, PARAMETER_REGISTER 1.17. Lases ur posten stamplingen redan
    skrivit; inget tal raknas om har.

    TXID SKRIVS ALDRIG. Klienten skriver ut txid for hogst en av fyra
    kalendrar, sa ett falt med den vore ett pastaende om fler vittnen an som
    gar att visa - samma beslut som i attesteringar(). Nyckeln star kvar med
    None sa att det syns att 1.17 bad om den och att den inte gar att fylla,
    i stallet for att se ut som en glomska.
    """
    import measurements
    st = post.get("stampel") or {}
    fo = post.get("forankring") or {}
    kal = fo.get("kalendrar") or []
    measurements.notera(day, "stampel", data, **{measurements.STAMPEL: {
        "stamplad_at": st.get("at"), "ots": st.get("ots"),
        "forankrad_at": fo.get("at"),
        "blockhojder": [k["block_height"] for k in kal],
        "merkle_rotter": [k["merkle_root"] for k in kal],
        "txid": None}})


def step_stampla(day, data=DATA):
    print(f"\n[stampla] {sp.state_id(day)}")
    emo = gates.gate_frozen_emotion(day, data)
    ots = sp.ots_sidecar(emo)
    post = las_post(day, data)
    if ots.exists():
        print(f"        {ots.name} finns redan - stampeln gors inte om")
        return post

    # DEN PUBLIKA MENINGEN. Star har, ordagrant, dar stampeln skrivs, sa att
    # nasta lasare inte uppfinner en starkare formulering:
    #
    #   Beviset binder manifestets hash till ett Bitcoin-block. En utomstaende
    #   kontrollerar det utan egen nod: ots --no-bitcoin verify skriver ut
    #   blockhojd och merkle-rot, och bada gar att sla upp i vilken
    #   blockutforskare som helst. Kommandot avslutar med FELKOD 1 - det
    #   verifierar inte automatiskt, det talar om vad som ska kontrolleras for
    #   hand. Automatisk verifiering kraver en Bitcoin-nod.
    #
    # Alltsa inte: att verifieringen lyckas, att den returnerar noll, eller att
    # vem som helst verifierar med ett kommando. Felkoden ar 1.
    version, start = klientversion(), _nu()
    kod, ut = _kor("stamp", str(emo), dolj=_dolj(data))
    forsok = {"steg": "stampla", "at": start, "felkod": kod,
              "klient": version, "utskrift": ut.strip()[:500]}
    post.setdefault("forsok", []).append(forsok)
    post.update({"day": day, "state_id": sp.state_id(day),
                 "manifest": emo.name, "manifest_sha256": _sha(emo)})

    if kod != 0 or not ots.exists():
        # VARNING, INTE STOPP. Stampeln ska ske nara frysningen, sa att den
        # uteblir ar vart att se direkt - men korningen gar vidare och utfallet
        # skrivs. Publiceringsgrinden ar den som sager nej.
        print(f"  VARNING stamplingen misslyckades (felkod {kod}) - dygnet ar "
              f"fryst och oskadat, stampeln kan tas om")
        print("        " + (ut.strip().splitlines() or ["ingen utskrift"])[-1][:200])
        skriv_post(day, post, data)
        return post

    post["stampel"] = {"ots": ots.name, "ots_sha256": _sha(ots),
                       "klient": version, "at": start}
    skriv_post(day, post, data)
    _matpost(day, post, data)
    print(f"        {ots.name}  sha256 {post['stampel']['ots_sha256'][:16]}  ·  {version}")
    print("        vantande kalenderattesteringar - forankras i nasta dygns korning B")
    return post


def step_forankra(day, data=DATA):
    print(f"\n[forankra] {sp.state_id(day)}")
    post = las_post(day, data)
    if not (post.get("stampel") or {}).get("at"):
        print("        dygnet har ingen stampel att forankra"); return post
    if post.get("forankring"):
        print(f"        redan forankrad {post['forankring']['at']} - gors inte om"); return post

    emo = sp.emotion_manifest(data, day)
    ots = sp.ots_sidecar(emo)
    if not ots.exists():
        print(f"  VARNING {ots.name} saknas - stampeln maste tas om"); return post

    start = _nu()
    kopia = kopia_fore_upgrade(ots)
    upp_kod, upp_ut = _kor("upgrade", str(ots), dolj=_dolj(data))
    # FELKODEN AVGOR INTE. ots --no-bitcoin verify avslutar med felkod 1 aven
    # nar beviset ar helt - den verifierar inte automatiskt, den talar om vad
    # som ska kontrolleras for hand. Det som avgor ar om klienten kan skriva ut
    # en blockhojd och en merkle-rot: finns de ar hashen bunden till ett block.
    ver_kod, ver_ut = _kor("--no-bitcoin", "verify", str(ots), dolj=_dolj(data))
    kal = attesteringar(ver_ut)
    post.setdefault("forsok", []).append(
        {"steg": "forankra", "at": start, "felkod_upgrade": upp_kod,
         "felkod_verify": ver_kod, "attesteringar": len(kal),
         "utskrift": (upp_ut + ver_ut).strip()[:500]})

    if not kal:
        skriv_post(day, post, data)
        if upp_kod == 0:
            # FELKODEN AVGOR HAR, OCH BARA HAR. upgrade felkod 0 betyder att
            # klienten anser beviset helt ("Success! Timestamp complete",
            # uppmatt pa varden 2026-11-24) - och da ska verifieringen kunna
            # skriva ut en blockhojd. Kan den inte det ar det inte dygnet som
            # vantar, det ar utskriftsformatet som andrats under oss. Ett
            # tyst misslyckande skulle ligga kvar som vantande i veckor.
            gates._say("upgrade och verifiering sager samma sak", False,
                       f"upgrade felkod 0 (beviset helt) men verifieringen gav "
                       f"noll attesteringar - formatet har andrats, "
                       f"{kopia.name} har originalets bytes")
        # Sex bekraftelser kravs, och de tar langre tid an forsta blocket.
        # .ots lamnas ORORD och forsoket tas om nasta dygn. Rapportera, gor
        # inte om: en ny stampel skulle binda manifestet till ett senare block
        # och gora det aldsta beviset varre.
        print(f"  VARNING ingen Bitcoin-attestering an (upgrade felkod "
              f"{upp_kod}) - .ots lamnas orord, forsoket tas om nasta dygn")
        return post

    post["forankring"] = {"at": start, "ots_sha256": _sha(ots), "kalendrar": kal}
    skriv_post(day, post, data)
    _matpost(day, post, data)
    # Forankringen lyckades: .ots ar andrad med avsikt och nya ots_sha256 star
    # i posten. Kopian tas bort. Den ar en ofullstandig version av samma bevis,
    # och en fil som ser ut som bevis men binder mindre an originalet ar nagot
    # nagon forr eller senare verifierar i stallet for det riktiga.
    kopia.unlink(missing_ok=True)
    # KLIENTENS EGEN KOPIA LYDER SAMMA REGEL. ots upgrade skriver
    # <manifest>.csv.ots.bak med originalets ofullstandiga bevis, och den
    # hamnar i arkivet bredvid manifestet. Meningen ovan galler ordagrant
    # aven den filen: vems hand som skrev den andrar inte vad den ar. Den
    # tas bort har och inte tidigare, av samma skal som var egen - fram till
    # forankringen ar den aterstallningsvagen. A25.
    ots.with_name(ots.name + ".bak").unlink(missing_ok=True)
    for k in kal:
        print(f"        block {k['block_height']}  merkleroot {k['merkle_root']}")
    print(f"        {len(kal)} attestering(ar) - dygnet far publiceras")
    return post


def vantande(data=DATA):
    """Dygn med en stampel men utan forankring, aldst forst.

    DYGNET TAS UR POSTEN, aldrig raknat ur katalognamnet: harledningen mellan
    dygn och katalog bor i statepaths, och en andra harledning har vore samma
    fel som gjorde state_id till tva format. Posten bar sitt eget dygn.
    """
    rot = data / sp.GENERATION_DIR
    ut = []
    for p in sorted(rot.glob("STATE_*/600_STATES_*_TIMESTAMP.json")):
        post = json.loads(p.read_text(encoding="utf-8"))
        if post.get("day") and (post.get("stampel") or {}).get("at") and not post.get("forankring"):
            ut.append(post["day"])
    return sorted(ut)


def main():
    args = sys.argv[1:]
    steg = args[0] if args else ""
    if steg not in ("stampla", "forankra"):
        sys.exit(__doc__)
    require_data()
    day = args[1] if len(args) > 1 else None
    try:
        if steg == "stampla":
            step_stampla(day or sp.senast_stangda_dygnet(datetime.now(timezone.utc)))
        elif day:
            step_forankra(day)
        else:
            # UTAN DYGN TAS ALLA SOM VANTAR, aldst forst. Ett forsok som inte
            # lyckades ska tas om, och ett dygn som missades helt ska inte
            # ligga ostamplat i arkivet for att ingen rakade kora ratt datum.
            dygn = vantande()
            print(f"{len(dygn)} dygn vantar pa forankring"
                  + (": " + ", ".join(dygn) if dygn else ""))
            for d in dygn:
                step_forankra(d)
    except gates.GateFailure as e:
        print(f"\nSTAMPLINGEN STOPPAD: {e}"); sys.exit(1)
    print("\nKlart.")


if __name__ == "__main__":
    main()
