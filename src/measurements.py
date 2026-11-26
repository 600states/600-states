"""Nattens matpost: en maskinlasbar fil per dygn. PARAMETER_REGISTER 1.17.

ETT TAL SOM RAKNAS FOR HAND AR ETT TAL SOM INTE FINNS. Poolens bevisandel
raknades for hand tre natter i rad - 21, 24 och 25 november - i en egen
container med skrivskyddat arkiv, for att korningen inte skrev den. Ett tal
som en manniska raknar varje natt i aratal raknas forr eller senare fel.

POSTEN VAXER, DEN SKRIVS INTE OM. Korning A skriver sina falt, korning B sina,
och stamplingen sina langt senare. Ett steg som skriver over hela filen raderar
det ett tidigare steg matte - samma skal som att snapshotet skrivs UT och inte
OM nar Events kommer till. notera() slar darfor ihop pa toppnivan och ror
aldrig en nyckel den inte fick.

INGA MALVARDEN, INGENSTANS. Ingen av de tio matpunkterna har ett riktvarde, en
budget eller en trend att sla, och det far ingen kod harunder infora. Avsnitt 0
forbjuder att ett matt pa den renderade bilden blir ett mal; 1.17 strackte ut
forbudet till matposten. Golvet i 1.15 ar en GRIND - den stoppar ett dygn och
belonar ingen. Ett mal pa en matning bjuder in till att matningen styrs, vilket
ar det enda instrumentet finns for att forhindra.

MATPUNKT 2 OCH 3 AR TVA STORHETER OCH DELAR INGENTING. Bada kommer ur
pool_evidence.basis(), den ena over HELA POOLEN och den andra over DE VALDA.
De har var sin nyckel, var sitt variabelnamn och var sin rad i den har filen.
Det ar samma felform som de tva golven i den andra granskningens fynd 8, dar
ordet "andel" betydde tva saker pa tva sidor; botemedlet var att namnge matten,
inte att sla ihop dem.

VAD SOM FAR PASTAS OM TALEN star i MESSAGE_BANK 0.5 och inte har. Kortversionen:
en natt ar en OBSERVATION och behover en matning; en EGENSKAP hos instrumentet
kraver n, min, max, median och datum for sista matningen - och sa lange tecknet
inte ar lika over alla n far ingen riktning pastas alls.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
from atomic import write_text
from config import DATA
import pool_evidence

# NYCKLARNA STAR HAR OCH INGEN ANNANSTANS. Den som skriver ett falt och den som
# grindar det ar olika steg i olika korningar; stavades nyckeln pa bada
# stallena skulle en stavfelad skrivning se ut som ett saknat falt. FYND 004.
KANDIDATER = "kandidater_i_fonstret"        # 1
POOLENS_ANDEL = "poolens_fonsterandel"      # 2  HELA POOLEN
DE_VALDAS_ANDEL = "de_valdas_fonsterandel"  # 3  DE 600 VALDA
TEXTKALLAN = "textkallan_over_de_valda"     # 4
DOMANER = "unika_domaner"                   # 5
SERIEN = "serien"                           # 6
EVENTS = "events"                           # 7
KORNING = "korning"                         # 8
STAMPEL = "stampel"                         # 9
MANIFEST_SHA = "manifest_sha256"            # 10

# MATPUNKT 11, tillagd 2026-11-26. De tio i 1.17 mater DYGNET; den har mater
# MILJON dygnet kordes i. NAS:ens .env bar ANTHROPIC_API_KEY= med tomt varde
# i fyra natter utan att en enda rapport sa ifran: korning B stannar vid
# emotionsgrinden med rc 3 och nar aldrig classify.py, som har sin egen
# grind. En kedja som inte kan klassificera nagonting alls ska inte behova
# en manniska som rakar lagga marke till det.
#
# Den ar obligatorisk utan att nagot steg behovde flytta sig: notera()
# skriver den vid varje skrivning, alltsa langt fore frysningen.
NYCKELN = "nyckel_narvarande"               # 11

# OBLIGATORISK BETYDER "gar att skriva nar dygnet fryses". Grinden sitter fore
# atomic_write(pre) i step_select, och ett falt vars kalla kors EFTER den
# punkten kan omojligt finnas dar. En grind som kraver ett falt ingen kan
# skriva stoppar varje natt, och da ar det grinden som ar fel, inte natten.
#
#   4  textkallan     byggs i step_input, som kor efter frysningen
#   8  korningen      agas av schemalaggaren, som inte ar uppsatt
#   9  stampeln       kors i en egen container efter emotionsmanifestet
#   10 manifestets sha256  finns forst nar emotionsmanifestet fryses
#
# Listan ar inte en ambitionsniva. Flyttas ett falt hit maste dess kalla forst
# ha flyttat fore frysningen.
OBLIGATORISKA = (KANDIDATER, POOLENS_ANDEL, DE_VALDAS_ANDEL, DOMANER, SERIEN,
                 EVENTS, NYCKELN)
VALFRIA = (TEXTKALLAN, KORNING, STAMPEL, MANIFEST_SHA)


def _nu():
    """Nar steget kordes. Mater omvarlden och valjer ingenting - samma undantag
    som bevisens hamtningstidpunkt, se AGENTS.md."""
    return f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}"


def nyckel_narvarande():
    """Ar ANTHROPIC_API_KEY satt och icketom i den har miljon? En bool.

    VARDET LAMNAR ALDRIG FUNKTIONEN. Inte nyckeln, inte ett prefix, inte de
    sista fyra tecknen, inte langden - en langd ar ocksa en upplysning om en
    hemlighet, och posten ligger i arkivet, som inte ar hemligt.

    Den mater omvarlden och valjer ingenting - samma undantag som _nu().
    """
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def fonsterandel(nivaer):
    """{"av": n, "i_fonstret": m, "andel": m/n} ur en folj av bevisnivaer.

    EN FUNKTION, TVA ANROP, TVA NYCKLAR. Matpunkt 2 och 3 raknas likadant och
    heter olika; det ar hela poangen med att de delar den har funktionen och
    ingenting annat.

    NIVAERNA RAKNAS INTE OM HAR. Anroparen skickar de nivaer den redan har -
    step_select har dem i raderna som ska frysas, och en andra beraikning av
    samma tal ar FYND 004 i berakningsform.

    Kvoten skrivs ut aven om den gar att rakna ur de tva talen. Skalet ar
    MESSAGE_BANK 0.5: det ar kvoten som citeras publikt, och raknar varje
    lasare sin egen blir 0,94877 tre olika publicerade tal.
    """
    nivaer = list(nivaer)
    i = sum(1 for n in nivaer if n == pool_evidence.FONSTERNIVAN)
    return {"niva": pool_evidence.FONSTERNIVAN, "av": len(nivaer), "i_fonstret": i,
            "andel": (i / len(nivaer)) if nivaer else None}


def las(day, data=DATA):
    p = sp.measurement_record(data, day)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def notera(day, steg, data=DATA, **falt):
    """Slar ihop falt in i dygnets matpost och skriver den atomiskt.

    skrivningar ar postens egen journal: vilket steg som skrev vad och nar. En
    omkorning av ett steg skriver om sina EGNA falt, och det ska synas att den
    gjorde det - en journal som tiger om sina luckor ar ett tyst osant
    pastaende, FYND 001.
    """
    post = las(day, data)
    post["day"] = day
    post["state_id"] = sp.state_id(day)
    # MATPUNKT 11 SKRIVS AV SKRIVNINGEN, inte av ett steg. Den mater miljon
    # posten skrevs i, och den miljon ar det skrivande stegets egen - ett
    # falt som bara ETT steg skrev hade sagt lika lite om de ovriga som
    # loggen sa i fyra natter. Den star i journalen vid varje skrivning av
    # samma skal: en journal som tiger om vad den skrev ar FYND 001.
    post[NYCKELN] = nyckel_narvarande()
    post.update(falt)
    post.setdefault("skrivningar", []).append(
        {"steg": steg, "at": _nu(), "falt": sorted(set(falt) | {NYCKELN})})
    write_text(sp.measurement_record(data, day),
               json.dumps(post, ensure_ascii=False, indent=1))
    return post
