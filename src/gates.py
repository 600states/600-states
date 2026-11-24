"""Grindar. En regel som inte kan stoppa en korning ar inte en regel.

Varje grind mater manifestet eller kandidatlistan. Ingen grind tittar nagonsin
pa den renderade bilden - se parameterregistret avsnitt 0.
"""
import collections

class GateFailure(Exception):
    pass

def _say(name, ok, detail):
    print(("  OK   " if ok else "  STOPP") + f" {name}: {detail}")
    if not ok:
        raise GateFailure(f"{name}: {detail}")

def gate_candidates(cands, day):
    _say("kandidater finns", len(cands) > 0, f"{len(cands)} kandidater")
    bad = [c for c in cands if not c.get("mention_rows")]
    _say("alla har mention_rows", not bad, f"{len(bad)} utan")
    bad = [c for c in cands if not str(c.get("first_mention_utc", "")).startswith(day)]
    _say("alla ligger i dygnet", not bad, f"{len(bad)} utanfor {day}")

def gate_pool_evidence(pool, floor=0.60):
    have = sum(1 for c in pool if c.get("page_title"))
    frac = have / len(pool) if pool else 0
    _say("rubriker i poolen", frac >= floor,
         f"{have}/{len(pool)} = {frac:.1%} (golv {floor:.0%})")

def gate_selection(chosen, report, regions, per_region, cap):
    _say("exakt 600 rutor", len(chosen) == 600, f"{len(chosen)}")
    short = {r: n for r, n in report["regional_per_region"].items() if n < per_region}
    _say("regionkvoter uppfyllda", not short, short or f"alla >= {per_region}")
    _say("publisher cap hallen", report["max_per_publicist"] <= cap,
         f"max {report['max_per_publicist']} (tak {cap})")
    _say("unika observation_id", report["unika_observation_id"] == len(chosen),
         f"{report['unika_observation_id']}")
    _say("unika url", report["unika_urler"] == len(chosen), f"{report['unika_urler']}")

def gate_evidence_time(rows, nivaer):
    """Ett dygn utan datering pa bevisen far inte frysas. FYND 011.

    Bevisen samlades in och bars hela vagen till sista steget - och tappades i
    det ogonblick som gor en post permanent. I den publicerade posten sag ett
    dygn fangat samma dygn darfor identiskt ut som ett fangat tva veckor
    senare, och det ar den enda skillnad v3.0 finns till for att gora.

    Grinden stod aldrig har forut, sa tystnaden kostade ingenting. Nu kostar
    den dygnet: saknas tidsstampeln eller nivan pa en enda rad gar manifestet
    inte att skriva.

    nivaer kommer fran den som satter faltet, aldrig fran en egen lista har -
    tva definitioner av samma vokabular ar hur FYND 003 uppstod.
    """
    print("        evidence_basis:", dict(collections.Counter(
        r.get("evidence_basis") or "SAKNAS" for r in rows)))
    utan = [r for r in rows if not r.get("evidence_retrieved_at")]
    _say("varje rad bar hamtningstidpunkt", not utan,
         f"{len(utan)} rader utan" + (f" (t.ex. ruta {utan[0].get('tile_index')})" if utan else ""))
    fel = [r for r in rows if r.get("evidence_basis") not in nivaer]
    _say("varje rad bar en bevisniva ur specen", not fel,
         f"{len(fel)} rader utanfor {list(nivaer)}"
         + (f" (t.ex. ruta {fel[0].get('tile_index')}: {fel[0].get('evidence_basis')!r})" if fel else ""))

def gate_claims(items, is_readable, is_digest=None):
    """is_readable ar SAMMA funktion som urvalsfiltret anvander. Tva egna
    definitioner av "lasbar" var orsaken till att urvalet slappte igenom rader
    som inputbygget inte kunde lasa - se FYND 003."""
    empty = [i for i in items if not is_readable(str(i["neutral_source_claim"]))]
    dist = collections.Counter(i["claim_source"] for i in items)
    print("        claim_source:", dict(dist))
    _say("varje rad har lasbar text", not empty,
         f"{len(empty)} rader utan" + (f" (t.ex. ruta {empty[0]['tile_index']})" if empty else ""))
    if is_digest is not None:
        d = [i for i in items if is_digest(i["neutral_source_claim"])]
        _say("ingen sammanfattningsartikel", not d,
             f"{len(d)} rader" + (f" (t.ex. ruta {d[0]['tile_index']}: {d[0]['neutral_source_claim'][:50]})" if d else ""))

def gate_emotion(inputs, rows, vocab):
    ids_in = {i["observation_id"] for i in inputs}
    ids_out = {r["observation_id"] for r in rows}
    _say("ID-mangd in = ut", ids_in == ids_out,
         f"in {len(ids_in)}, ut {len(ids_out)}, diff {len(ids_in ^ ids_out)}")
    bad = [r for r in rows if r["primary_emotion"] not in vocab or r["secondary_emotion"] not in vocab]
    _say("etiketter i vokabularet", not bad, f"{len(bad)} utanfor")
    bad = [r for r in rows if r["primary_emotion"] == r["secondary_emotion"]]
    _say("primary != secondary", not bad, f"{len(bad)} lika")
    bad = [r for r in rows if not (0 <= float(r["intensity"]) <= 1 and 0 <= float(r["confidence"]) <= 1)]
    _say("intensity/confidence i [0,1]", not bad, f"{len(bad)} utanfor")
    n_i = len({r["intensity"] for r in rows}); n_c = len({r["confidence"] for r in rows})
    _say("varden ar inte konstanta", n_i > 5 and n_c > 5,
         f"{n_i} unika intensity, {n_c} unika confidence")

def gate_registry(cands, registry_path, version, allowed):
    """Manifestet far aldrig pasta en annan registerversion an den som anvandes.

    FYND 004: kandidatbyggaren laste v1.1 STRICT (75 domaner) medan manifestet
    skrev v2.0 (107). De 32 tillagda domanerna kunde aldrig valjas.
    """
    # TAUTOLOGIN SOM LAG HAR. Grinden testade "version in registry_path.name",
    # dar version kom ur registry_path.name via config.registry_version(). Den
    # kunde aldrig falla. Grinden skrevs som svar pa FYND 004 och skyddade
    # ingenting - det var enda-definition-fixen i config.py som gjorde jobbet.
    #
    # Den verkliga risken i FYND 004 var ratt filnamn med fel innehall. Darfor
    # jamfors registrets bytes nu mot den frysta sha256-sidecaren. Sidecaren
    # skrevs med en absolut sokvag fran en annan maskin, sa bara hashen lases.
    import hashlib, re
    sidecar = registry_path.with_name(registry_path.stem + "_SHA256.txt")
    if sidecar.exists():
        vill = re.match(r"[0-9a-f]{64}", sidecar.read_text(encoding="utf-8").strip())
        har = hashlib.sha256(registry_path.read_bytes()).hexdigest()
        _say("kallregistrets innehall matchar den frysta hashen",
             bool(vill) and vill.group(0) == har, f"{har[:16]} mot {vill.group(0)[:16] if vill else 'oläsbar sidecar'}")
    else:
        _say("kallregistret har en fryst sha256-sidecar", False, sidecar.name + " saknas")
    _say("kallregistrets version star i filnamnet", version in registry_path.name,
         f"{registry_path.name} -> {version}")
    doms = {c["domain"] for c in cands}
    bad = doms - set(allowed)
    _say("varje kandidat ligger i registret", not bad, f"{len(bad)} utanfor")
    print(f"        registret har {len(allowed)} domaner, {len(doms)} av dem forekommer i dygnet")


def gate_kanonisk_kedja(serie, index, brott, tak=600):
    """Kedjan bakat ska ga ihop, och ordningstalet ska rymmas i serien.

    DETTA AR INTE GOLVETS GRIND. Ett dygn under golvet produceras anda -
    klassificeras, fryses och hashas som alla andra - det far bara inget
    nummer. Att hoppa over dygnet skulle bryta "en dag, en korning, ett
    utfall", och ett dygn som saknas av metodskal gar inte att skilja fran ett
    som saknas av slarv.

    Det som DAREMOT stoppar korningen ar ett arkiv som inte gar att lasa
    ordningstalet ur. Talet skrivs in i ett manifest som hashas, alltsa
    permanent: raknas det fram ur ett arkiv dar ett manifest saknas eller en
    lank inte stammer blir felet fryst, och enda vagen ut ar att skriva om
    varje dygn efter det.

    Taket likasa. Serien ar 600 dygn. Ett 601:a nummer ar inte ett stort tal,
    det ar ett pastaende om att serien inte ar slut.
    """
    _say("kedjan bakat gar ihop", not brott,
         "; ".join(brott) if brott else "arkivets kanoniska dygn lanker i foljd")
    _say("ordningstalet ryms i serien", index is None or index <= tak,
         f"{index:03d} av {tak}" if index else f"inget ordningstal ({serie})")


def gate_korningsfonster(nu_utc, dygn):
    """Far korningen borja an? Grinden for KORNING_START_UTC.

    Vardet stod i pool_evidence och lastes ingenstans i hela src/. Ett tal som
    ingen kod laser ar ett onskemal, inte en regel; hela skillnaden mellan de
    tva ar att nagot stannar nar det bryts.

    DEN HINDRAR FOR TIDIGT, INTE FOR SENT. Ett dygn vars bevisfonster redan
    hunnit stanga gar fortfarande att kora. Det landar da under golvet och blir
    UNQUALIFIED av sig sjalvt, vilket ar ratt utfall och en matning vard att ha.
    En ovre grans har skulle i stallet gora ett missat dygn till ett dygn som
    aldrig funnits.

    Grinden galler bara det harledda laget. Anges dygnet explicit ar det arkiv-
    eller reparationsvagen, och den fragar aldrig vad klockan ar.

    nu_utc kommer fran anroparen, aldrig ur en egen klockavlasning har: en
    grind som laser klockan sjalv gar inte att prova med en forstalld klocka,
    och en grind som inte gar att prova ar ingen grind.
    """
    from datetime import datetime, timedelta, timezone
    from pool_evidence import KORNING_START_UTC       # en definition, aldrig en kopia

    stangde = datetime.strptime(dygn, "%Y%m%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    h, m = (int(x) for x in KORNING_START_UTC.split(":"))
    tidigast = stangde + timedelta(hours=h, minutes=m)
    _say("dygnet har stangt", nu_utc >= stangde,
         f"{dygn} stanger {stangde:%Y-%m-%d %H:%M}, klockan ar {nu_utc:%Y-%m-%d %H:%M} UTC")
    _say(f"klockan har passerat {KORNING_START_UTC}", nu_utc >= tidigast,
         f"tidigast {tidigast:%Y-%m-%d %H:%M}, klockan ar {nu_utc:%Y-%m-%d %H:%M} UTC")


def gate_frozen_emotion(day, data):
    """Emotionsmanifestet finns, ar fryst, och ar orort sedan frysningen.

    DEN BOR HAR, INTE I FARGSIDAN. Tva program stallde samma fraga: fargen,
    som inte far rakna hex pa ett manifest som andrats efter frysningen, och
    stamplingen, som inte far intyga en hash som inte langre ar filens. Skriven
    pa tva stallen hade den kunnat glida isar - och da hade de tva programmen
    haft var sin uppfattning om vad "fryst" betyder. Det ar FYND 004:s form.

    Returnerar manifestets sokvag, sa att anroparen slipper harleda den igen.
    """
    import hashlib
    import statepaths as sp
    emo = sp.emotion_manifest(data, day)
    side = sp.sha_sidecar(emo)
    _say("emotionsmanifestet finns", emo.exists(), emo.name)
    _say("det ar fryst (sha256-sidecar finns)", side.exists(), side.name)
    want = side.read_text(encoding="utf-8").split()[0]
    got = hashlib.sha256(emo.read_bytes()).hexdigest()
    _say("manifestet ar orort sedan frysningen", want == got, f"{got[:16]} mot {want[:16]}")
    return emo


def gate_forankrad_stampel(state_id, post):
    """Ett fryst manifest utan forankrad .ots publiceras inte.

    GRINDEN SITTER PA PUBLICERINGEN, INTE PA FRYSNINGEN, och det ar hela
    poangen. Fyra externa kalendrar som inte svarar 00:06 far inte kosta ett
    annars felfritt dygn - ett dygn gar inte att gora om. Pa publiceringen
    kostar samma avbrott en fordrojning, och en fordrojning gar att ta igen.

    Stamplingen och forankringen ligger darfor i egna korningar, i en egen
    container, och den har grinden laser bara deras post. DEN ROR INGET NAT och
    kraver inget av de nio stampelpaketen: den laser en JSON-fil ur arkivet.
    Det ar avsiktligt - en grind som bara gar att prova med natet uppe gar inte
    att prova.

    FORANKRAD BETYDER MINST EN BITCOIN-ATTESTERING, inte fyra. Fyra kalendrar
    stamplar, men en enda attestering binder redan manifestets hash till ett
    block, och antalet star i posten for den som vill se det. Ett hogre krav
    vore ett tal utan matning bakom sig.
    """
    _say("dygnet har en tidsstampelpost", bool(post),
         f"{state_id}: " + ("posten finns" if post else "ingen post - har dygnet stamplats?"))
    st = post.get("stampel") or {}
    _say("manifestet ar stamplat", bool(st.get("at")),
         st.get("ots") or "ingen .ots skriven")
    fo = post.get("forankring") or {}
    kal = fo.get("kalendrar") or []
    _say("stampeln ar forankrad i blockkedjan", bool(kal),
         f"{len(kal)} attestering(ar)" + (f", forst block {kal[0]['block_height']}" if kal
                                          else " - kor forankringen igen nasta dygn"))


def gate_frirymd(behov, fri, matt_pa):
    """Ett dygn far inte borja skrivas nar det inte finns plats for det.

    INGET TAL STAR HAR. Behovet mats pa de senast fardiga dygnen, sa att
    grinden foljer med nar dygnen vaxer; en hardkodad troskel blir fel atta
    manader in, och det marks forst nar halva manifestet ar skrivet.

    Finns inget fardigt dygn att mata pa provas ingenting - och det STAR i
    utskriften. En kontroll som tyst hoppas over ser likadan ut som en som gick
    igenom.
    """
    if behov is None:
        print(f"        FRIRYMDEN PROVADES INTE: {matt_pa}")
        return
    _say("fri rymd racker for dygnet", fri >= behov,
         f"{fri / 2**30:.2f} GiB fria, behover {behov / 2**30:.2f} GiB ({matt_pa})")
