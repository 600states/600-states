"""Revision av ett fardigt State. Rapporterar, andrar ingenting.

Kontrollerar att lankar, ID:n, hashar och bevis hanger ihop mellan filerna -
det som en kopare eller en granskare ska kunna gora sjalv.
"""
import csv, hashlib, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
import pool_evidence as pe
from config import DATA
from color_protocol import hex_of_row

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit(day, data=DATA):
    """Nitton kontroller. Rapporterar pa allt som gar att prova.

    TRE TILLSTAND, INTE TVA:

      OK          kontrollen stalldes och godkandes
      FEL         kontrollen stalldes och foll
      EJ PROVAD   kallan gick inte att lasa - kontrollen stalldes aldrig

    Revisionen dog forut pa forsta saknade filen, innan en enda kontroll
    skrivits ut: resultaten samlas och skrivs forst pa slutet. Uppmatt pa
    2026/330 - en saknad site_2026_330.json tog med sig de arton andra, dar
    ibland den enda kontroll som sager att 600 av 600 farger reproducerar ur
    det frysta protokollet. Den laser bara fargmanifestet och ska kunna
    stallas aven nar sajtfilen saknas. A42.

    Det ar projektets egen regel spegelvand: en grind som inte kan falla ar
    ett onskemal, och en kontroll som kraschar i stallet for att falla ar
    samma fel ett steg senare.

    OCH DARFOR RACKER INTE all(). Tva tillstand kan inte se det tredje: en
    revision som stallde fjorton kontroller och skrev ALLT STAMMER gor
    siffran nitton osann, och den siffran star i publik text. Funktionen
    returnerar (godkanda, fallna, ej_provade).
    """
    out, matt, fel = [], [], {}

    def chk(name, ok, detail=""):
        out.append(("OK" if ok else "FEL", name, detail))

    def kalla(namn, hur):
        """En indatakalla i sin egen try. Returnerar None och bokfor skalet.

        SOKVAGEN SKRIVS INTE UT. Rapporten kan citeras, och arkivets sokvag
        hor inte hemma dar - filnamnet sager vilken fil som saknas.
        """
        try:
            return hur()
        except FileNotFoundError as e:
            # TVA FORMER AV SAMMA FEL. open() och read_text() satter
            # .filename; sp.frozen() reser FileNotFoundError(path) med
            # sokvagen som ENDA argument, och da ar .filename None. Fem av
            # nio kallor gick genom den grenen och fick kallans etikett i
            # stallet for filnamnet - "FileNotFoundError: PNG" pa den rad
            # som ska saga vilken FORM som inte fanns. A46.
            #
            # Basnamnet tas ur det som finns, aldrig sokvagen: rapporten
            # kan citeras, och arkivets sokvag hor inte hemma dar.
            i_felet = e.filename or (e.args[0] if e.args else "")
            fel[namn] = "FileNotFoundError: " + (Path(str(i_felet)).name or namn)
        except Exception as e:
            fel[namn] = f"{type(e).__name__}: {e}"
        return None

    def prova(name, kallor, funk):
        """En kontroll, om dess kallor gick att lasa - annars EJ PROVAD.

        Kontrollen namnges i bada fallen. En utelamnad rad later en revision
        som provade fjorton se ut som en som provade nitton.

        funk returnerar (utfall, detalj) i ett, sa att talet i detaljen ar
        samma rakning som utfallet vilar pa.
        """
        saknas = [k for k in kallor if k in fel]
        if saknas:
            out.append(("EJ", name, "; ".join(f"{k}: {fel[k]}" for k in saknas)))
            return
        try:
            ok, detalj = funk()
        except Exception as e:
            # En kontroll som kastar ar samma fel som en revision som
            # kraschar, ett steg mindre. Den faller med sitt besked.
            chk(name, False, f"{type(e).__name__}: {e}")
            return
        chk(name, ok, detalj)

    # DYGNETS EGNA FILER, UPPSLAGNA EN GANG. Revisionen far inte kunna lasa en
    # form och redovisa en annan, sa samma uppslagning bar bade lasningen och
    # hashlistan langre ner. frozen() sager ifran nar den byter version.
    #
    # VARJE KALLA I SIN EGEN TRY. Fyra filuppslagningar, tva csv-lasningar, en
    # batchkatalog, en bevispool och en sajtfil - nio vagar in, och var och en
    # kunde forut ta med sig hela revisionen.
    FILNAMN = (("pre-emotion", sp.pre_manifest), ("emotion+farg", sp.color_manifest),
               ("near-duplicate", sp.near_duplicate), ("PNG", sp.png))
    files = {}
    for namn, bygg in FILNAMN:
        f = kalla(namn, lambda b=bygg: sp.frozen(b(data, day)))
        if f is not None:
            files[namn] = f

    pre = emo = None
    if "pre-emotion" in files:
        pre = kalla("pre-emotion", lambda: list(csv.DictReader(
            open(files["pre-emotion"], encoding="utf-8"))))
    if "emotion+farg" in files:
        emo = kalla("emotion+farg", lambda: list(csv.DictReader(
            open(files["emotion+farg"], encoding="utf-8"))))

    def las_input():
        d = sp.classifier_input(data, day)
        if not d.exists():
            raise FileNotFoundError(2, "katalogen saknas", str(d))
        ut = {}
        for f in sorted(d.glob("batch_*.json")):
            for it in json.loads(f.read_text(encoding="utf-8")):
                ut[it["observation_id"]] = it
        return ut

    def las_bevis():
        # ARKIVET SOM FUNKTIONEN FICK, inte modulens. FYND 029.
        ut = {}
        for line in (data / "07_EVIDENCE" / "pool_titles.jsonl").read_text(
                encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                ut[r["url"]] = r
        return ut

    inp = kalla("klassificerarinput", las_input)
    ev = kalla("bevispool", las_bevis)
    site = kalla("sajtfilen", lambda: json.loads(
        sp.site_json(data, day).read_text(encoding="utf-8")))
    # VERKETS EGEN HASH, sedan A43. Sidecaren lases bara om bilden finns:
    # saknas bilden ar det den som ska namnas, inte en sidecar till en fil
    # som inte ar dar.
    verkets_rad = kalla("verkets sidecar", lambda: sp.sha_sidecar(
        files["PNG"]).read_text(encoding="utf-8")) if "PNG" in files else None

    P = ("pre-emotion",)
    E = ("emotion+farg",)
    PE = ("pre-emotion", "emotion+farg")
    S = ("sajtfilen",)

    def i_ordning(rader):
        return sorted(rader, key=lambda r: int(r["tile_index"]))

    prova("rader", PE, lambda: (len(pre) == 600 and len(emo) == 600,
                                f"pre {len(pre)}, emotion {len(emo)}"))
    prova("tile_index 1..600 utan lucka", P,
          lambda: (sorted(int(r["tile_index"]) for r in pre) == list(range(1, 601)), ""))
    prova("unika observation_id", P,
          lambda: (len({r["observation_id"] for r in pre}) == 600, ""))
    prova("unika url", P,
          lambda: (len({r["representative_url"] for r in pre}) == 600, ""))
    prova("ID-mangd pre = emotion", PE,
          lambda: ({r["observation_id"] for r in pre} == {r["observation_id"] for r in emo}, ""))
    prova("ID-mangd pre = klassificerarens input", ("pre-emotion", "klassificerarinput"),
          lambda: ({r["observation_id"] for r in pre} == set(inp), f"input {len(inp)}"))
    prova("tile_index matchar mellan filerna", PE,
          lambda: (all(int(a["tile_index"]) == int(b["tile_index"])
                       for a, b in zip(i_ordning(pre), i_ordning(emo))), ""))

    # KONTROLL 8. Den laser BARA fargmanifestet och ska darfor kunna stallas
    # aven nar sajtfilen, bevispoolen eller indatakatalogen saknas. Det ar den
    # enda kontroll som sager att fargen reproducerar ur det frysta
    # protokollet, och den var en av de arton som gick forlorade pa 2026/330.
    def _hex():
        bad = [r["tile_index"] for r in emo if hex_of_row(r).upper() != r["hex"].upper()]
        return not bad, f"{600 - len(bad)}/600"

    prova("hex reproduceras av protokollet", E, _hex)

    def _url():
        bad = [r["tile_index"] for r in pre
               if not re.match(r"^https?://[^\s]+\.[^\s]+", r["representative_url"])]
        return not bad, f"{len(bad)} trasiga"

    prova("url ar valformade", P, _url)

    def _doman():
        bad = [r["tile_index"] for r in pre
               if r["representative_domain"].split(".")[0] not in r["representative_url"].lower()]
        return not bad, f"{len(bad)} avvikande"

    prova("domankolumnen finns i url", P, _doman)

    def _bevis():
        have = sum(1 for r in pre if r["representative_url"] in ev)
        return have == 600, f"{have}/600"

    prova("varje url har en bevispost", ("pre-emotion", "bevispool"), _bevis)

    # MATNING, INTE KONTROLL. Raden skickade tidigare hardkodat True till chk()
    # och skrev alltsa OK oavsett utfall - en kontroll som inte kunde falla, i
    # den fil som ar granskarens sista. Andelen med innehallshash ligger pa
    # 88-91 procent; resten ar 403, 404 eller betalvagg. Protokollets krav att
    # varje observation har en atkomlig kalla (Observation Verification V02) ar
    # alltsa INTE uppfyllt till hundra procent, och vilket golv som ska galla ar
    # ett obeslutat varde. Tills det ar beslutat redovisas siffran utan att
    # pasta att den ar godkand. Se AGENTS.md.
    if pre is not None and ev is not None:
        withhash = sum(1 for r in pre if ev.get(r["representative_url"], {}).get("content_sha256"))
        matt.append(("sidan gick att hamta alls - innehallshash finns",
                     f"{withhash}/600 = {withhash/6:.1f}% (ovriga ar 403/404/betalvagg)"))
    else:
        matt.append(("sidan gick att hamta alls - innehallshash finns",
                     "gar inte att mata: " + "; ".join(
                         f"{k}: {v}" for k, v in fel.items()
                         if k in ("pre-emotion", "bevispool"))))
    # DET ANDRA MATTET, OCH DET SOM GOLVET FAKTISKT RAKNAR PA. FYND 014 den 20
    # november forkastade hashandelen som matt pa serien: en innehallshash
    # sager att vi HAR sidan, inte att vi hade den i tid. Golvet raknar sedan
    # 9113f6e fonsternivan, och parameterregistret 1.15 och bevisspecen 3.1
    # rattades samma dag - revisionen gjorde det inte, och var darmed tredje
    # stallet dar det gamla mattet overlevde.
    #
    # BADA RADERNA STAR KVAR. De mater olika saker: den forsta hur stor del av
    # poolen som gick att hamta alls, den andra hur stor del som hanns med inom
    # fonstret. Ett retrospektivt dygn har hog forsta siffra och noll andra, och
    # det ar precis den skillnaden som inte gick att se harifran forut.
    #
    # EN FORM UTAN FALTET GER INGEN NOLLA. v3.2 bar inte evidence_basis, och
    # noll procent vore ett svar pa en fraga som aldrig stalldes. serie() lamnar
    # den formen UNQUALIFIED, men det ar ett omdome; den har raden mater.
    if pre is None:
        matt.append((f"sidan fangades i bevisfonstret - {pe.FONSTERNIVAN}",
                     "gar inte att mata: " + fel.get("pre-emotion", "okant")))
    elif "evidence_basis" in pre[0]:
        ifonstret = sum(1 for r in pre
                        if (r.get("evidence_basis") or "").strip() == pe.FONSTERNIVAN)
        matt.append((f"sidan fangades i bevisfonstret - {pe.FONSTERNIVAN}",
                     f"{ifonstret}/600 = {ifonstret/6:.1f}% "
                     f"(golv {pe.GOLV_KANONISK:.0%} for kanoniskt medlemskap)"))
    else:
        matt.append((f"sidan fangades i bevisfonstret - {pe.FONSTERNIVAN}",
                     f"gar inte att mata: formen {sp.version_of(files['pre-emotion'])} "
                     "bar inte evidence_basis"))

    from datetime import date
    dd = date(int(day[:4]), int(day[4:6]), int(day[6:8])).strftime("%Y%m%d")

    def _tid():
        bad = [r["tile_index"] for r in pre if not r["first_mention_utc"].startswith(dd)]
        return not bad, f"{len(bad)} utanfor"

    prova("alla tidsstamplar i ratt dygn", P, _tid)

    def _ordning():
        order = [r["first_mention_utc"] for r in i_ordning(pre)]
        return order == sorted(order), ""

    prova("kronologisk ordning", P, _ordning)

    def _cap():
        caps = {}
        for r in pre:
            caps[r["representative_domain"]] = caps.get(r["representative_domain"], 0) + 1
        return max(caps.values()) <= 10, f"max {max(caps.values())}, {len(caps)} publicister"

    prova("publisher cap <= 10", P, _cap)

    prova("sajtens preHash = filen", S + P,
          lambda: (site["meta"]["preHash"] == sha(files["pre-emotion"]), ""))
    prova("sajtens emoHash = filen", S + E,
          lambda: (site["meta"]["emoHash"] == sha(files["emotion+farg"]), ""))
    prova("sajtens ndHash = filen", S + ("near-duplicate",),
          lambda: (site["meta"]["ndHash"] == sha(files["near-duplicate"]), ""))
    prova("sajtens rutor = manifestet", S + E,
          lambda: ([t["h"] for t in site["tiles"]] == [r["hex"] for r in i_ordning(emo)], ""))
    prova("sajtens url = manifestet", S + P,
          lambda: ([t["u"] for t in site["tiles"]]
                   == [r["representative_url"] for r in i_ordning(pre)], ""))

    # KONTROLL 20. Revisionen fragade aldrig efter verket: PNG:en bar noll av
    # de nitton och anvandes bara i fillistan, sa ett dygn vars bild saknades
    # gav nitton av nitton och felkod 0. Ett projekt vars forsta mening ar
    # "The artwork is the Proof of State" kan inte ha en revision som godkanner
    # ett State vars verk saknas. A37.
    #
    # Namnet sager vad den laser - FYND 014:s regel - och inte vad den heter i
    # koden. Den jamfor bildens egen hash med sidecarens rad, samma jamforelse
    # som provet gor for en enskild bild.
    def _verket():
        bildens = sha(files["PNG"])
        delar = verkets_rad.split()
        sidecarens = delar[0] if delar else ""
        namnet = delar[1] if len(delar) > 1 else ""
        return (sidecarens == bildens and namnet == files["PNG"].name,
                f"{bildens[:16]} mot sidecarens {sidecarens[:16] or '(tom rad)'}")

    prova("verkets sha256 = sidecarens rad", ("PNG", "verkets sidecar"), _verket)

    MARKE = {"OK": "  OK       ", "FEL": "  FEL      ", "EJ": "  EJ PROVAD"}
    print(f"\n=== STATE {sp.state_id(day)} ===")
    for status, name, detail in out:
        print(MARKE[status] + f" {name}" + (f": {detail}" if detail else ""))
    for name, detail in matt:
        print(f"  MATT      {name}: {detail}")
    # VERSIONEN SOM LASTES, PER FIL. Den star inte i koden utan i filnamnet:
    # 2026/308 ar fryst som v3.2 och revideras av v3.3-kod, och en lasare ska
    # se vilken form raderna kom ur utan att gissa. En fil som inte gick att
    # lasa star med sitt skal i stallet for sin hash.
    print(f"  filer, med den version som faktiskt lastes (koden star pa {sp.MANIFEST_VERSION}):")
    for namn, _ in FILNAMN:
        if namn in files:
            print(f"    {namn:<15} {sp.version_of(files[namn]):<5} {sha(files[namn])}")
        else:
            print(f"    {namn:<15} {fel[namn]}")

    godkanda = sum(1 for s, _, _ in out if s == "OK")
    fallna = sum(1 for s, _, _ in out if s == "FEL")
    ej_provade = sum(1 for s, _, _ in out if s == "EJ")
    print(f"  stallda {godkanda + fallna} av {len(out)}, godkanda {godkanda}, "
          f"fallna {fallna}, ej provade {ej_provade}")
    return godkanda, fallna, ej_provade

if __name__ == "__main__":
    # TRE UTFALL, TRE FELKODER. all() over tva tillstand kan inte se det
    # tredje, och ett dygn dar fjorton kontroller stalldes far inte sluta med
    # samma kod som ett dar nitton gjorde det.
    #
    #   0  alla stallda och godkanda
    #   1  minst en fallen        - ett kant fel rapporteras fore ett okant
    #   2  minst en ej provad, ingen fallen
    tal = [audit(s) for s in sys.argv[1:]]
    godkanda = sum(t[0] for t in tal)
    fallna = sum(t[1] for t in tal)
    ej_provade = sum(t[2] for t in tal)
    print(f"\ngodkanda {godkanda}, fallna {fallna}, ej provade {ej_provade}")
    print("ALLT STAMMER" if not fallna and not ej_provade else
          "AVVIKELSER HITTADE" if fallna else
          "INTE ALLT GICK ATT PROVA")
    sys.exit(1 if fallna else (2 if ej_provade else 0))
