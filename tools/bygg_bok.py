"""Boken till ett verk: en sida per ruta, genererad ur det frysta manifestet.

    python tools/bygg_bok.py <ut.pdf> [state_id]

VARFOR DEN HAR FILEN LIGGER I tools/ OCH INTE I src/
Boken ligger NEDSTROMS det frysta manifestet. Den laser ett fardigt verk och
tillverkar det inte. Lag den i src/ kunde instrumentet importera den, och ett
PDF-bibliotek vore da en del av det som laser nyheter. Samma skal som gav
stamplingen en egen container: reportlab och qrcode star i
deploy/requirements-bok.txt, aldrig i kedjans requirements.txt.

VARIFRAN SIFFRORNA I DEN HAR FILEN KOMMER
Den forsta generatorn skrevs 2026-11-13 i en sessionscontainer som ar riven.
Kallkoden finns inte kvar nagonstans. Det som finns ar dess UTSKRIFT:
600_STATES_2026_315_BOOK.pdf, 611 sidor.

Darfor ar nastan varje koordinat harunder UPPMATT ur den PDF:en 2026-11-25,
med pdfplumber, ur textmatrisen (matrix[4], matrix[5]) som ar reportlabs egen
ritkoordinat - inte ur teckenrutans ovankant, som ligger en versalhojd fel.
Matningen ar inte en gissning om hur sidan sag ut: den AR sidan.

Tre sidor matta i sin helhet - 6, 310 och 605 - gav samma koordinatskelett.
De tva skillnader som finns ar innehallets, inte kodens: URL:en bryts till en
eller tva rader med 6,6 punkters steg (det ar hacka() harunder, ett av de
tva fragment som gar in ordagrant), och sidnumret ar hogerstallt sa dess vansterkant flyttar med
antalet siffror. En skanning av 88 rutsidor visade dessutom att hogerspalten
FLYTER: pastaendet borjar alltid pa samma rad, allt under det foljer efter.
Fem olika kombinationer av radantal reproducerades exakt av modellen harunder.

BARGNINGEN AR ETT UNDERLAG, INTE EN KALLA
Transkriptet bar TVA generatorer. Den forsta satte 481.89 x 680.315 pt =
170 x 240 mm staende och kastades nar formatet byttes till 21 x 15 cm; den
andra skrevs fran noll och ar den PDF:en pa disk kommer ur. Bargningens
avsnitt 5.1:s anropsrad, 5.4, 5.5 och 5.6 hor till den KASTADE generatorn -
46 x 4 kolumner var en layout for en staende sida. Bara 5.2 och 5.3 gar in
ordagrant. Allt annat ar uppmatt. Nar dokumentet och byten sager olika vinner
byten.

TRE STALLEN DAR DEN HAR FILEN MED AVSIKT INTE AR PDF:EN PA DISK
1. OMSLAGET. PDF:en bar A1 - titeln i DejaVuSans-ExtraLight 40. BOKEN_SPEC
   avvisade A1 2026-11-14 till forman for A2: samma komposition, REGULAR 40.
   "Extra light ar inte tystnad, det ar en vald tunnhet."
2. MARGINALERNA. PDF:en har 14 mm runtom och en satsyta pa 182 mm. Specen 3.1
   kraver SPEGLADE marginaler - inre 23 mm, yttre 14 mm, satsyta 173 mm -
   darfor att ett tradbundet block pa 611 sidor slukar bredd vid ryggen.
   Rutsidans komposition andras inte, bara papperets sida vander.
3. DATUMET. Se FRYST DATUM harunder.

FRYST DATUM
ReportLab skriver CreationDate och ModDate i filen. Lamnas de at klockan kan
samma manifest aldrig ge samma PDF tva ganger, och da faller hela skalet att
boken genereras av kod i stallet for att sattas for hand. Bada satts darfor
ur dygnet sjalvt: observationsdygnets midnatt i UTC, harlett ur state_id.
"""
import csv
import json
import os
import sys
from collections import OrderedDict
from datetime import date, timedelta
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

import config  # noqa: E402

from reportlab import rl_config  # noqa: E402
from reportlab.lib.colors import Color, HexColor, white  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.pdfgen import canvas as rl_canvas  # noqa: E402

# ---------------------------------------------------------------- typsnitt --
# TYPSNITTEN LIGGER I REPOT, i tools/fonts/. Bokens PDF publiceras som en
# hash (BOKEN_SPEC 2), och vi vet redan att den inte ar byteidentisk mellan
# tva reportlab-versioner. Att den DESSUTOM skulle bero pa vilka filer som
# rakar ligga i /usr/share/fonts pa den maskin som kor ar en andra osynlig
# axel i samma pastaende. Licensen tillater buntning - Bitstream Vera plus
# publika andringar, samma sak Debian och Chromium gor - och licensfilen
# ligger bredvid dem.
#
# Ordningen: STATES_FONTS ar kvar som en override for den som vill prova en
# annan skarning, repots egen katalog ar det NORMALA, och systemets star
# sist sa att en container utan repokopian anda hittar dem.
TYPSNITT = OrderedDict([
    ("S", "DejaVuSans.ttf"),
    ("SB", "DejaVuSans-Bold.ttf"),
    ("L", "DejaVuSans-ExtraLight.ttf"),
    ("M", "DejaVuSansMono.ttf"),
])


REPOTS_TYPSNITT = Path(__file__).resolve().parent / "fonts"


def typsnittskatalog():
    env = os.environ.get("STATES_FONTS")
    kandidater = [Path(env)] if env else []
    kandidater.append(REPOTS_TYPSNITT)
    kandidater.append(Path("/usr/share/fonts/truetype/dejavu"))
    for k in kandidater:
        if all((k / f).exists() for f in TYPSNITT.values()):
            return k
    # SVARET AR INTE LANGRE EN MILJOVARIABEL. Saknas filerna ar det repots
    # kopia som ar borta, och det ar den raden som ska sta har.
    raise SystemExit(
        "Hittar inte DejaVu-typsnitten: " + ", ".join(TYPSNITT.values()) + "\n"
        f"De hor hemma i {REPOTS_TYPSNITT} och foljer med repot.\n"
        "Sok dar forst; STATES_FONTS ar en override for en annan skarning.")


def las_typsnitt():
    kat = typsnittskatalog()
    for namn, fil in TYPSNITT.items():
        pdfmetrics.registerFont(TTFont(namn, str(kat / fil)))


# --------------------------------------------------------------- geometrin --
# 210 x 150 mm liggande. Uppmatt: 595.2756 x 425.1969 pt.
SIDA = (210 * mm, 150 * mm)

# Speglade marginaler, BOKEN_SPEC 3.1. Satsytan ar lika bred pa varje sida -
# bara dess plats pa arket speglas.
MARG_INRE = 23 * mm
MARG_YTTRE = 14 * mm
SATSYTA = 173 * mm

RUTOR_X = 30
RUTOR_Y = 20

SVART = Color(0.07, 0.07, 0.07)
GRA = Color(0.45, 0.45, 0.45)
GRA_LJUS = Color(0.6, 0.6, 0.6)
GRA_LINJE = Color(0.8, 0.8, 0.8)


def satsyta(sidnr):
    """Vansterkanten pa sidans satsyta. Udda sidnummer ar hogersida."""
    return MARG_INRE if sidnr % 2 else MARG_YTTRE


# ---------------------------------- bargat ordagrant: enbart 5.2 och 5.3 --
def klocka(fm):
    """20261111000000 -> 11 Nov 2026 00:00 UTC"""
    if not fm or len(fm) < 12:
        return fm or ""
    man = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return (f"{int(fm[6:8])} {man[int(fm[4:6]) - 1]} {fm[0:4]} "
            f"{fm[8:10]}:{fm[10:12]} UTC")


def hacka(text, font, storlek, bredd):
    """Bryter en lang obruten strang (en URL) pa tecken sa att den far plats."""
    rader, nu = [], ""
    for ch in text:
        if pdfmetrics.stringWidth(nu + ch, font, storlek) <= bredd:
            nu += ch
        else:
            rader.append(nu)
            nu = ch
    if nu:
        rader.append(nu)
    return rader


def skriv(c, x, y, text, font, storlek, farg, bredd=SATSYTA, radavstand=None):
    """Bryter text pa ordgrans, ritar den, och returnerar NY y.

    Anvands som y = skriv(...). Varje anropare anger sitt radavstand; det
    har standardvardet styr ingen sida i boken och ar inte uppmatt.
    """
    if radavstand is None:
        radavstand = storlek * 1.45
    c.setFont(font, storlek)
    c.setFillColor(farg)
    rader, nu = [], ""
    for ord_ in text.split():
        prov = (nu + " " + ord_).strip()
        if pdfmetrics.stringWidth(prov, font, storlek) <= bredd or not nu:
            nu = prov
        else:
            rader.append(nu)
            nu = ord_
    if nu:
        rader.append(nu)
    for rad in rader:
        c.drawString(x, y, rad)
        y -= radavstand
    return y


def radantal(text, font, storlek, bredd):
    """Hur manga rader skriv() skulle ge. Behovs for spaltbrytningen."""
    n, nu = 0, ""
    for ord_ in text.split():
        prov = (nu + " " + ord_).strip()
        if pdfmetrics.stringWidth(prov, font, storlek) <= bredd or not nu:
            nu = prov
        else:
            n += 1
            nu = ord_
    return n + (1 if nu else 0)


# --------------------------------------------------------- fargregistret --
# UPPMATT, inte bargat. Bargningens avsnitt 5.6 har PER_KOL, KOL = 46, 4 och
# rubrik 13 pt, och den layouten har aldrig funnits pa en liggande sida: den
# hor till den FORSTA generatorn, som satte 170 x 240 mm staende och kastades
# nar formatet byttes. PDF:en pa disk ar den andra generatorn. Nar dokumentet
# och byten sager olika vinner byten.
REG_KOL = 6
REG_PER_KOL = 28
REG_EFTER_RUBRIK = 23.29      # rubrikens rad till underradens
REG_EFTER_SUB = 17.95         # underradens till forsta registerraden
REG_RAD = 9.2


def hexindex(c, rader, state_id, sidnr):
    """Alla 600 hexvarden som text, fyra sidor. Registret, inte bilden.

    Sex kolumner a 28 rader ar uppmatt pa sidorna 606-609: 168 + 168 + 168 + 96
    = 600, och den sista sidan fyller tre kolumner plus tolv rader. Kolumnerna
    raknas ur den SPEGLADE satsytan och inte ur den symmetriska som utskriften
    har: fyra sidor som inte speglar i ett tradbundet block pa 611 sidor tappar
    sin inre kolumn ner i ryggen, och BOKEN_SPEC 3.1 gor inget undantag for
    registret.
    """
    per_sida = REG_PER_KOL * REG_KOL
    kb = SATSYTA / REG_KOL
    sidor = 0
    for start in range(0, len(rader), per_sida):
        bit = rader[start:start + per_sida]
        x0 = satsyta(sidnr + sidor)
        y = SIDA[1] - 26 * mm
        if start == 0:
            c.setFont("SB", 12)
            c.setFillColor(SVART)
            c.drawString(x0, y, "Colour index")
            # Underraden ar EN rad i satsytan - 330 pt av 490 - och bryts
            # aldrig. Radavstandet for en andra rad gar darfor inte att mata
            # ur utskriften, sa avstandet till registret star som ett matt.
            skriv(c, x0, y - REG_EFTER_RUBRIK,
                  "Every tile and the colour its reading became. The image is "
                  "these 600 values and nothing else.", "S", 7.0, GRA, SATSYTA,
                  REG_EFTER_SUB)
            y = y - REG_EFTER_RUBRIK - REG_EFTER_SUB
        top = y
        for i, r in enumerate(bit):
            kx = x0 + (i // REG_PER_KOL) * kb
            ky = top - (i % REG_PER_KOL) * REG_RAD
            c.setFillColor(HexColor(r["hex"]))
            c.rect(kx, ky - 1, 5.2, 5.2, stroke=0, fill=1)
            c.setFont("M", 5.6)
            c.setFillColor(GRA)
            c.drawString(kx + 7.4, ky, f"{int(r['tile_index']):03d}")
            c.setFillColor(SVART)
            c.drawString(kx + 19.0, ky, r["hex"].upper())
        sidfot(c, state_id, str(sidnr + sidor))
        c.showPage()
        sidor += 1
    return sidor


# --------------------------------------------------------- gemensamma delar --
def sidfot(c, vanster, sidnummer):
    """Uppmatt: y = 8 mm, mono 5,6 i gratt, sidnumret hogerstallt."""
    x0 = satsyta(int(sidnummer))
    c.setFont("M", 5.6)
    c.setFillColor(GRA)
    c.drawString(x0, 8 * mm, vanster)
    c.drawRightString(x0 + SATSYTA, 8 * mm, sidnummer)


def qr_bild(url):
    """QR-koden pekar pa kallan som den publicerades.

    BOKEN_SPEC 5: en kod per sida, inte tva. Destinationen byts till
    /t/<state_id>/<ruta> nar rutsidorna pa sajten finns - fore forsta tryckta
    boken, inte efter.
    """
    import qrcode
    return qrcode.make(url).get_image()


# ------------------------------------------------------------- rutsidan ----
def rutsida(c, pre, farg, state_id, datum, sidnr):
    """En ruta, en sida. 600 av bokens 611 sidor.

    HELA DEN HAR FUNKTIONEN AR UPPMATT. Dess kropp fanns inte kvar att barga -
    bara dess utskrift, sida 6 till 605. Varje tal harunder star som det matts,
    och de som gick att lasa som jamna millimetermatt skrivs som millimeter.
    """
    from reportlab.lib.utils import ImageReader

    x0 = satsyta(sidnr)
    hoger = x0 + SATSYTA
    hx = x0 + 69 * mm                       # hogerspaltens x, uppmatt
    rb = hoger - hx                         # hogerspaltens bredd

    # --- huvudet, hogerstallt -------------------------------------------
    c.setFont("M", 6.2)
    c.setFillColor(GRA)
    c.drawRightString(hoger, SIDA[1] - 22 * mm,
                      f"{state_id}    {klocka(pre['first_mention_utc'])}")

    # --- vanster spalt: talet, fargrutan, hexvardet, minigriden ---------
    c.setFont("L", 30)
    c.setFillColor(SVART)
    c.drawString(x0, SIDA[1] - 26 * mm, f"{int(pre['tile_index']):03d}")

    ry = SIDA[1] - 39 * mm - 42 * mm
    c.setFillColor(HexColor(farg["hex"]))
    c.rect(x0, ry, 42 * mm, 42 * mm, stroke=0, fill=1)

    hy = ry - 5 * mm
    c.setFont("M", 7)
    c.setFillColor(SVART)
    c.drawString(x0, hy, farg["hex"].upper())

    gb = 44 * mm
    cw = ch = gb / RUTOR_X
    gh = ch * RUTOR_Y
    gy = hy - 6 * mm - gh                   # griden raknas fran sin OVERKANT
    rad, kol = int(pre["grid_row"]), int(pre["grid_column"])

    c.setStrokeColor(GRA_LINJE)
    c.setLineWidth(0.12)
    for i in range(RUTOR_X + 1):
        c.line(x0 + i * cw, gy, x0 + i * cw, gy + gh)
    for j in range(RUTOR_Y + 1):
        c.line(x0, gy + j * ch, x0 + gb, gy + j * ch)

    # Harkorset genom rutans mitt, och rutan sjalv 0,5 pt storre at varje hall.
    # (Bargningens avsnitt 5.4 sager 0,4 och 0,8; PDF:en pa disk sager 0,5 och
    # 1,0, och det ar PDF:en som ar utskriften. Se rapporten.)
    cx, cy = x0 + (kol - 1) * cw, gy + gh - rad * ch
    c.setStrokeColor(GRA)
    c.setLineWidth(0.25)
    c.line(x0, cy + ch / 2, x0 + gb, cy + ch / 2)
    c.line(cx + cw / 2, gy, cx + cw / 2, gy + gh)
    c.setFillColor(SVART)
    c.rect(cx - 0.5, cy - 0.5, cw + 1.0, ch + 1.0, stroke=0, fill=1)

    c.setFont("M", 5.6)
    c.setFillColor(GRA)
    c.drawString(x0, gy - 4.5 * mm, f"row {rad}   col {kol}")

    # --- hoger spalt: pastaendet, anteckningen, linjen, falten -----------
    y = skriv(c, hx, SIDA[1] - 30 * mm,
              farg["neutral_event_representation"], "S", 8.6, SVART, rb, 12)
    y = skriv(c, hx, y - 3 * mm,
              farg["classification_note"], "S", 6.6, GRA, rb, 9.2)

    ly = y - 3 * mm
    c.setStrokeColor(GRA_LINJE)
    c.setLineWidth(0.4)
    c.line(hx, ly, hoger, ly)

    falt = [
        ("primary", farg["primary_emotion"]),
        ("secondary", farg["secondary_emotion"]),
        ("intensity", farg["intensity"]),
        ("confidence", farg["confidence"]),
        ("agreement", farg["primary_agreement"]),
        ("claim source", farg["claim_source"]),
        ("publisher", pre["representative_domain"]),
        ("source tier", pre["source_tier"]),
        ("layer", pre["selection_layer"]),
        ("review region", pre["review_region"]),
        ("mention rows", pre["mention_rows"]),
        ("http status", pre["evidence_http_status"]),
        ("evidence basis", pre["evidence_basis"]),
        ("retrieved", pre["evidence_retrieved_at"][:19]),
        ("observation id", pre["observation_id"]),
    ]
    fy = ly - 5.5 * mm
    for i, (etikett, varde) in enumerate(falt):
        kx = hx + (i % 2) * (rb / 2)
        ky = fy - (i // 2) * 8.6
        c.setFont("M", 5.6)
        c.setFillColor(GRA)
        c.drawString(kx, ky, etikett)
        c.setFont("M", 6.2)
        c.setFillColor(SVART)
        c.drawString(kx + 21 * mm, ky, str(varde))

    hashy = fy - ((len(falt) + 1) // 2 - 1) * 8.6 - 7 * mm
    c.setFont("M", 5.6)
    c.setFillColor(GRA)
    c.drawString(hx, hashy, "evidence sha256")
    c.setFont("M", 6.2)
    c.setFillColor(SVART)
    sha = pre["evidence_sha256"] or ""
    for i in range(0, max(len(sha), 1), 32):
        c.drawString(hx + 21 * mm, hashy - (i // 32) * 7.4, sha[i:i + 32])

    # --- nere till hoger: QR-koden, och URL:en till vanster om den -------
    qs = 20 * mm
    qx, qy = hoger - qs, 14 * mm
    c.drawImage(ImageReader(qr_bild(pre["representative_url"])),
                qx, qy, qs, qs)
    c.setFont("M", 5.0)
    c.setFillColor(GRA)
    c.drawRightString(hoger, qy - 3.5 * mm, "source as published")

    ub = qx - hx - 5 * mm
    uy = qy + qs - 5
    c.setFont("M", 5)
    c.setFillColor(GRA)
    for rad_ in hacka(pre["representative_url"], "M", 5, ub)[:4]:
        c.drawString(hx, uy, rad_)
        uy -= 6.6

    sidfot(c, datum, str(sidnr))
    c.showPage()


# ------------------------------------------------------------ fortexten ----
def titelsida(c, state_id, datum):
    """Omslag A2: titeln i REGULAR 40, vansterstalld. Inte ExtraLight.

    PDF:en pa disk bar A1 - samma komposition i extra light. BOKEN_SPEC 6
    avvisade den 2026-11-14: "Extra light ar inte tystnad, det ar en vald
    tunnhet, och en vald tunnhet ar ett pastaende."
    """
    x0 = satsyta(1)
    c.setFillColor(SVART)
    c.rect(0, 0, SIDA[0], SIDA[1], stroke=0, fill=1)
    c.setFont("S", 40)
    c.setFillColor(white)
    c.drawString(x0, SIDA[1] - 52 * mm, "600 STATES")
    c.setFont("M", 10)
    c.drawString(x0, 80 * mm, state_id)
    c.setFont("S", 10)
    c.drawString(x0, 70 * mm, datum)
    c.setFont("S", 7.5)
    c.setFillColor(GRA_LJUS)
    c.drawString(x0, 20 * mm,
                 "600 observations. One day. One irreversible visual state.")
    c.showPage()


PANEL = [
    ("24 hours",
     "of the monitored global news flow, reviewed for qualifying "
     "information states.", white),
    ("600 observations",
     "frozen before any colour exists. The same event is allowed. The same "
     "information state is not.", white),
    ("1 800 readings",
     "every observation classified three times, independently. The tile "
     "carries the consensus.", SVART),
    ("1 image",
     "rendered deterministically, its manifest hashed and published the "
     "same day.", SVART),
]
PANELFARG = [HexColor("#2F5B8C"), HexColor("#7B2C3B"),
             HexColor("#E3BE4E"), white]


def panelsida(c):
    """Svart botten, fyra block, taglinen under dem. Allt uppmatt."""
    x0 = satsyta(2)
    c.setFillColor(SVART)
    c.rect(0, 0, SIDA[0], SIDA[1], stroke=0, fill=1)
    c.setFont("L", 19)
    c.setFillColor(white)
    c.drawString(x0, SIDA[1] - 30 * mm,
                 "Observe, select, read three times, render")

    bh = 44 * mm
    by = SIDA[1] - 60 * mm - bh
    bw = (SATSYTA - 4 * 1.2) / 4
    for i, ((rubrik, brod, blackfarg), ruta) in enumerate(zip(PANEL, PANELFARG)):
        bx = x0 + i * (bw + 1.2)
        c.setFillColor(ruta)
        c.rect(bx, by, bw, bh, stroke=0, fill=1)
        c.setFont("SB", 7.5)
        c.setFillColor(blackfarg)
        c.drawString(bx + 3.5 * mm, by + bh - 8 * mm, rubrik)
        skriv(c, bx + 3.5 * mm, by + bh - 14 * mm, brod, "S", 5.4,
              blackfarg, bw - 7 * mm, 6.8)

    skriv(c, x0, 35 * mm,
          "The colour model is unreachable until the 600-observation manifest "
          "is frozen. A chain that can reach colour at any point cannot show "
          "that it did not.", "S", 6.5, Color(0.62, 0.62, 0.62), SATSYTA, 11)
    c.showPage()


# Textsidans flode, uppmatt pa sidorna 3, 4, 610 och 611 och verifierat mot
# alla fyra: rubriken returnerar y - 27,54; ett brodstycke ritas dar y star och
# returnerar sista raden - 11 - 7,37; en monorad-grupp ritas dar y star och
# returnerar sista raden - 9,6; en mellanrubrik ritas 5,67 UNDER y och
# returnerar sin egen rad - 13,64.
LED_BROD = 11.0
LED_MONO = 9.6
EFTER_TITEL = 27.54
EFTER_RUBRIK = 13.64
EFTER_BROD = 7.37
FORE_RUBRIK = 5.67
# Golvet dar en spalt bryts. Matningen ramar in det men pinnar det inte: inget
# block ritades under y = 75,14 och tva block som skulle ha slutat pa 55,94
# respektive 25,58 flyttades till nasta spalt. 25 mm ligger i det spannet.
GOLV = 25 * mm
SPALTGAP = 9 * mm


def textsida(c, titel, bitar, state_id, sidnr, spalter=1):
    """Rubrik, sedan poster som floder: ("rubrik"|"brod"|"mono", innehall)."""
    x0 = satsyta(sidnr)
    spaltbredd = (SATSYTA - SPALTGAP) / 2 if spalter == 2 else SATSYTA
    kolumner = [x0, x0 + spaltbredd + SPALTGAP][:spalter]

    c.setFont("SB", 12)
    c.setFillColor(SVART)
    c.drawString(x0, SIDA[1] - 26 * mm, titel)
    y = SIDA[1] - 26 * mm - EFTER_TITEL
    k = 0

    for sort, innehall in bitar:
        x = kolumner[k]
        if sort == "rubrik":
            c.setFont("SB", 8)
            c.setFillColor(SVART)
            c.drawString(x, y - FORE_RUBRIK, innehall)
            y = y - FORE_RUBRIK - EFTER_RUBRIK
            continue
        if sort == "brod":
            n = radantal(innehall, "S", 7.6, spaltbredd)
            hojd = n * LED_BROD + EFTER_BROD
        else:
            n = sum(max(1, len(str(v)) // 32 + (1 if len(str(v)) % 32 else 0))
                    for _, v in innehall)
            hojd = n * LED_MONO
        if y - hojd < GOLV and k + 1 < len(kolumner):
            k += 1
            x = kolumner[k]
            y = SIDA[1] - 30 * mm
        if sort == "brod":
            y = skriv(c, x, y, innehall, "S", 7.6, SVART, spaltbredd, LED_BROD)
            y -= EFTER_BROD
        else:
            for etikett, varde in innehall:
                c.setFont("M", 6.2)
                c.setFillColor(GRA)
                c.drawString(x, y, etikett)
                c.setFillColor(SVART)
                v = str(varde)
                for i in range(0, max(len(v), 1), 32):
                    c.drawString(x + 34 * mm, y, v[i:i + 32])
                    y -= LED_MONO

    sidfot(c, state_id, str(sidnr))
    c.showPage()


def plattsida(c, png, state_id, datum, sidnr):
    """Planschen. Centrerad i SATSYTAN, aldrig pa arket - BOKEN_SPEC 3.1.

    Kvoten ar bildens egen, 3087/2057 = 1.5007292, och tvingas inte mot 3:2.
    Hojden styr: 300,47 pt over 2057 pixlar ger 493 dpi, vilket ligger over
    specens krav pa 300.
    """
    from reportlab.lib.utils import ImageReader

    x0 = satsyta(sidnr)
    bild = ImageReader(str(png))
    pxb, pxh = bild.getSize()
    h = SIDA[1] - 17 * mm - 27 * mm
    b = h * pxb / pxh
    if b > SATSYTA:
        b, h = SATSYTA, SATSYTA * pxh / pxb
    bx = x0 + (SATSYTA - b) / 2
    c.drawImage(bild, bx, 27 * mm, b, h)
    c.setFont("M", 6.2)
    c.setFillColor(GRA)
    c.drawString(bx, 17 * mm,
                 f"{state_id}   {datum}   {RUTOR_X} x {RUTOR_Y}")
    sidfot(c, state_id, str(sidnr))
    c.showPage()


# ------------------------------------------------------------- indata -----
def dygnsdatum(state_id):
    """2026/315 -> (date(2026, 11, 11), '11 NOVEMBER 2026').

    Dygnet harleds ur state_id och aldrig ur klockan. Det ar ocksa den enda
    kalla det frysta datumet i PDF:en har.
    """
    ar, dag = state_id.split("/")
    d = date(int(ar), 1, 1) + timedelta(days=int(dag) - 1)
    manader = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
               "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
    return d, f"{d.day} {manader[d.month - 1]} {d.year}"


def las_dygnet(nyckel):
    kat = config.require_data() / "08_V3_STATES" / ("STATE_" + nyckel)
    if not kat.exists():
        raise SystemExit("Hittar inte dygnet: " + str(kat))

    def en(monster):
        traff = sorted(kat.glob(monster))
        if len(traff) != 1:
            raise SystemExit(
                f"{len(traff)} filer matchar {monster} i {kat.name}, vantade 1")
        return traff[0]

    def csvfil(p):
        return list(csv.DictReader(p.read_text(encoding="utf-8").splitlines()))

    pre = en("*_PRE_EMOTION_MANIFEST_*.csv")
    farg = en("*_EMOTION_COLOR_MANIFEST_*_CONSENSUS.csv")
    rapport = en("*_SELECTION_REPORT_*.json")
    png = en("*_CONSENSUS.png")
    sidecar = Path(str(farg) + ".sha256")
    return {
        "pre": csvfil(pre),
        "farg": csvfil(farg),
        "rapport": json.loads(rapport.read_text(encoding="utf-8")),
        "png": png,
        "manifestnamn": farg.name,
        "manifest_sha": sidecar.read_text(encoding="utf-8").split()[0],
    }


def rakna(rader, kolumn):
    """Antal per varde, storst forst. Lika manga: forsta forekomsten forst.

    Ordningen far INTE bero pa en datastruktur. Se FYND 016: urvalet berodde en
    gang pa PYTHONHASHSEED darfor att determinismen var en egenskap hos en
    mangd i stallet for en regel. Har ar regeln utskriven.
    """
    antal, forst = {}, {}
    for i, r in enumerate(rader):
        v = r[kolumn]
        antal[v] = antal.get(v, 0) + 1
        forst.setdefault(v, i)
    return sorted(antal.items(), key=lambda kv: (-kv[1], forst[kv[0]]))


# -------------------------------------------------------------- bygget -----
def bygg(ut, nyckel="2026_315"):
    las_typsnitt()
    d = las_dygnet(nyckel)
    pre = sorted(d["pre"], key=lambda r: int(r["tile_index"]))
    # Registret ska sta i RUTNATETS ordning, inte i filens. Manifestet ar
    # redan sorterat, men boken ska inte vila pa det: ordningen ar en regel
    # har, inte en egenskap hos en fil. Se FYND 016.
    farg_rader = sorted(d["farg"], key=lambda r: int(r["tile_index"]))
    farg = {int(r["tile_index"]): r for r in farg_rader}
    state_id = pre[0]["state_id"]
    dag, datum = dygnsdatum(state_id)
    sha = d["manifest_sha"]

    # FRYST DATUM. Bada falten satts ur dygnet, inte ur klockan.
    rl_config.invariant = 1
    c = rl_canvas.Canvas(str(ut), pagesize=SIDA, invariant=1)
    c.setAuthor("600 STATES")
    c.setCreator("anonymous")
    c.setTitle(f"600 STATES {state_id}")
    c.setSubject(f"{len(pre)} observations of {datum}")
    # PDFInfo skriver ModDate och CreationDate ur samma PDFDate. Formatteraren
    # far (yyyy, mm, dd, hh, m, s) och ignorerar dem alla: dygnets midnatt i
    # UTC ar svaret oavsett nar bygget kors.
    stampel = "D:%s000000+00'00'" % dag.strftime("%Y%m%d")
    c._doc.info._dateFormatter = lambda *_: stampel

    med_bevis = sum(1 for r in pre if r["evidence_basis"] != "NO_EVIDENCE")
    rap = d["rapport"]

    titelsida(c, state_id, datum)
    panelsida(c)

    n = 2
    n += 1
    textsida(c, "What this book is", [
        ("brod", "This book is not about the work. It is the work's "
                 "evidence, printed."),
        ("brod", "Every page that follows is one tile of the image, in the "
                 "order the manifest holds them, which is the order the day "
                 "held them. The page carries the claim the instrument read, "
                 "the reading it produced, the colour that reading became, "
                 "and the address of the page it was read from. Nothing on a "
                 "page was chosen for this book."),
        ("brod", "The book is generated from the frozen manifest by code. "
                 "Change the manifest and the book changes with it; the "
                 "manifest cannot be changed, because its hash is published."),
        ("rubrik", "This day, measured"),
        ("mono", [("observation day", datum),
                  ("state id", state_id),
                  ("candidates seen", rap["kandidater"]),
                  ("after story cap", rap["efter_storytak"]),
                  ("removed by cap", rap["bortsorterade_av_tak"]),
                  ("near-duplicates", rap["near_duplicate_observed"]),
                  ("selected", rap["valda"]),
                  ("distinct publishers", rap["unika_domaner"]),
                  ("rows with evidence",
                   f"{med_bevis} of {len(pre)} = "
                   f"{100.0 * med_bevis / len(pre):.1f}%")]),
        ("mono", [("manifest sha256", sha)]),
    ], state_id, n, spalter=2)

    n += 1
    textsida(c, "How to read a page", [
        ("rubrik", "The number"),
        ("brod", "The tile's position in time. Tile 001 is the earliest "
                 "first mention of the day, tile 600 the latest. The grid "
                 "reads left to right, top to bottom, so the image runs "
                 "chronologically from its top-left corner."),
        ("rubrik", "The colour"),
        ("brod", "Produced by a frozen mathematical model from the reading "
                 "alone. No colour was chosen, adjusted, or balanced against "
                 "its neighbours."),
        ("rubrik", "The claim"),
        ("brod", "The instrument's own neutral formulation of what the "
                 "source reported. Not a quotation, and not an "
                 "interpretation of the event."),
        ("rubrik", "The grey note"),
        ("brod", "The classifier's stated reason for the reading it gave, "
                 "printed unedited, including where it is thin."),
        ("rubrik", "agreement"),
        ("brod", "Three independent readings per observation. 3/3 means all "
                 "three agreed on the primary state. The instrument does not "
                 "hide where it was split."),
        ("rubrik", "evidence basis"),
        ("brod", "CAPTURED_IN_WINDOW: fetched while the day was still the "
                 "day. RETROSPECTIVE: fetched after the day closed. "
                 "NO_EVIDENCE: no page could be hashed, and the page says "
                 "so."),
        ("rubrik", "The code"),
        ("brod", "Points at the source as published. If the publisher has "
                 "removed the article, the hash on the page is what remains, "
                 "and it is still enough to show what was read."),
    ], state_id, n, spalter=2)

    n += 1
    plattsida(c, d["png"], state_id, datum, n)

    for p in pre:
        n += 1
        rutsida(c, p, farg[int(p["tile_index"])], state_id, datum, n)

    n += 1
    n += hexindex(c, farg_rader, state_id, n) - 1

    n += 1
    textsida(c, "The day in numbers", [
        ("rubrik", "Evidence basis"),
        ("mono", [(k, f"{v} of {len(pre)}") for k, v in
                  rakna(pre, "evidence_basis")]),
        ("rubrik", "Primary states"),
        ("mono", rakna(farg_rader, "primary_emotion")),
    ], state_id, n)

    n += 1
    textsida(c, "Colophon", [
        ("brod", f"600 STATES {state_id}. One UTC day, {len(pre)} news "
                 "observations, one irreversible field of colour."),
        ("rubrik", "Hashes"),
        ("mono", [("manifest sha256", sha)]),
        ("rubrik", "Licence"),
        ("brod", "The code is MIT. The manifest and the hashes are CC0. The "
                 "work itself is all rights reserved; the buyer holds the "
                 "token and a licence, never the copyright."),
        ("rubrik", "Generated"),
        ("brod", "Generated from the frozen manifest by code. Not laid out "
                 "by hand, and no page was reviewed for appearance before "
                 "printing."),
        ("rubrik", "One copy"),
        ("brod", f"This book exists in a single copy, for {state_id}, and is "
                 "never printed again."),
    ], state_id, n)

    c.save()
    return n


def main(argv):
    if not 2 <= len(argv) <= 3:
        raise SystemExit("python tools/bygg_bok.py <ut.pdf> [2026_315]")
    ut = Path(argv[1])
    if ut.suffix.lower() != ".pdf":
        raise SystemExit("malet ska vara en .pdf: " + str(ut))
    ut.parent.mkdir(parents=True, exist_ok=True)
    sidor = bygg(ut, argv[2] if len(argv) == 3 else "2026_315")
    print(f"{ut}  {sidor} sidor  {ut.stat().st_size} byte")


if __name__ == "__main__":
    main(sys.argv)
