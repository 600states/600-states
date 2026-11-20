"""Urval och klassificeringsinput for ett dygn. SEPARAT PROGRAM.

    python3 src/run_state.py [dygn] [--stage NAMN] [--budget N]

PROGRAMMET AGER DYGNET. Utan dygnargument harleder main() det UTC-dygn som
senast stangde och kor en forkontroll fore forsta steget. Den som startar
korningen bestammer alltsa inte langre vilket dygn det ar, och en feltryckning
kan inte bli ett felaktigt verk. Schemalaggaren knackar pa; tiden ager
programmet.

Anges dygnet gar korningen precis som forut. Det ar arkiv- och
reparationsvagen, och den far aldrig bero pa vad klockan ar.

KLOCKAN LASES PA ETT STALLE, i main(), och nar aldrig berakningen. Den valjer
vilket dygn som ska koras och provas mot forkontrollens fonster; darefter ar
dygnet en strang som alla andra. Daglig korning och efterhandskorning av en
aldre dag gar genom exakt samma kodvag, annars ar dagarna inte jamforbara.

DETTA PROGRAM NAR ALDRIG FARGEN. Det importerar inte color_protocol och far
aldrig gora det. Farg och rendering ligger i run_color.py, som kors forst nar
emotionsmanifestet ar fryst. Separationen ar funktionen, inte stadning.

Steg, i ordning:
    preflight   bara i det harledda laget         grind: frirymd, korningsfonster
    candidates  GDELT -> kandidatlista            grind: dygn, mention_rows, register
    pool        bevisfangst pa hela poolen        grind: rubriktackning
    select      600 valda bland lasbara           grind: 600, regionkvoter, cap
    input       klassificerarens input            grind: varje rad har text
    --- klassificeringen kors har och lagger passen pa plats ---
    emotion     kontroll av emotionsmanifestet    grind: ID-mangd, vokabular, spridning

    --- darefter: python3 src/run_color.py <dygn> ---

Avbryter med felkod nar en grind stoppar. En regel som inte kan stoppa en
korning ar inte en regel.
"""
import csv, json, shutil, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
from atomic import atomic_write, write_text
from config import (DATA, RAW_GDELT, REGISTRY_FILE as REGISTRY, registry_version,
                    raw_day_dir, canonical_batch_size, require_data, LUCKLOGG)
import candidates, ranking, select_day, pool_evidence, gates
from vocab import EMOTION_STATES
from build_classifier_input import claim_of, readable, is_digest

STAGES = ["candidates", "pool", "select", "input", "emotion"]

def senast_stangda_dygnet(nu_utc):
    """Det UTC-dygn som senast stangde. Enda stallet dar en klocka blir ett dygn."""
    return (nu_utc.date() - timedelta(days=1)).strftime("%Y%m%d")

def _dag(katalognamn):
    """STATE_2026_308 -> date(2026, 11, 4). Aret ar aldrig hardkodat."""
    return date(int(katalognamn[6:10]), 1, 1) + timedelta(days=int(katalognamn[11:14]) - 1)

def _dygnskataloger():
    """Seriens kataloger, aldst forst. Pilotserien heter STATE_001 och matchar inte."""
    return sorted((DATA / sp.GENERATION_DIR).glob("STATE_[0-9][0-9][0-9][0-9]_[0-9][0-9][0-9]"))

def _luckor(day):
    """Kalenderdygn utan fryst pre-manifest, fran seriens forsta dygn till dygnet fore day.

    EN LUCKA STOPPAR INGENTING. Kedjan ar en kedja av kanoniska dygn, inte av
    kalenderdygn, sa en missad dag bryter den inte - och att stoppa nasta dygn
    skulle gora ett haveri till tva. Luckan ska synas, inte blockera.
    """
    kataloger = _dygnskataloger()
    if not kataloger:
        return []
    d, slut = _dag(kataloger[0].name), _dag("STATE_" + sp.state_key(day))
    ut = []
    while d < slut:
        dygn = d.strftime("%Y%m%d")
        if not sp.har_pre_manifest(DATA, dygn):
            ut.append(dygn)
        d += timedelta(days=1)
    return ut

def _logga_luckor(nu_utc, day, luckor):
    """Loggen skrivs aven nar det inte finns nagra luckor: en logg som bara
    skrivs nar nagot ar fel gar inte att skilja fran en som aldrig kordes."""
    rad = (f"{nu_utc:%Y-%m-%dT%H:%M:%SZ}  korning {day}  "
           + (f"luckor {len(luckor)}: " + ", ".join(luckor) if luckor else "inga luckor"))
    with open(LUCKLOGG, "a", encoding="utf-8") as fh:
        fh.write(rad + "\n")

def _fardiga_dygn():
    """Dygn med fryst pre-manifest, aldst forst. Fardig = formen finns pa disk;
    ett paborjat dygn sager inget om vad ett helt tar."""
    return [d for d in (_dag(k.name).strftime("%Y%m%d") for k in _dygnskataloger())
            if sp.har_pre_manifest(DATA, d)]

def _katalogstorlek(p):
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0

def _rastorlek(dygn, minne):
    """Dygnets filer i rasnapshotkatalogen - aven de i dess arbetskatalog.

    Katalogen bar hela arets filer, sa den listas en gang per ar och inte en
    gang per dygn: fem rglob over en katalog som vaxer till 600 dygn ar fem
    katalogtraversaler i en forkontroll som ska ta sekunder.
    """
    rot = raw_day_dir(dygn)
    if rot not in minne:
        minne[rot] = ([(str(f), f.stat().st_size) for f in rot.rglob("*") if f.is_file()]
                      if rot.exists() else [])
    return sum(n for s, n in minne[rot] if dygn in s)

def _bevisandel(antal_fardiga):
    """Ett dygns del av bevisfilerna, som SNITT - och ordet star i utskriften.

    PA V3-VAGEN FINNS INGEN BEVISKATALOG PER DYGN. Bevisen gar i en cache
    nycklad pa URL och delad mellan dygn, sa att overlapp aldrig hamtas om, och
    raderna bar ingen dygnsmarkning. Vad ett enskilt dygn lade dit gar inte att
    lasa ut i efterhand; bara snittet gar att mata. Att presentera det som en
    matning per dygn vore samma fel en gang till.

    Katalogen tas ur pool_evidence.CACHE, dar bevisen faktiskt skrivs, aldrig ur
    en egen strang: tva definitioner av samma sokvag ar hur FYND 004 borjade.
    """
    bevis = pool_evidence.CACHE.parent
    return _katalogstorlek(bevis) // max(antal_fardiga, 1) if bevis.exists() else 0

def _dygnets_avtryck(dygn, minne, bevisandel):
    """Allt ett dygn lagger i arkivet, pa alla tre stallen det vaxer:
    STATE-katalogen, dygnets rasnapshot, och dess del av bevisen."""
    return (_katalogstorlek(sp.outdir(DATA, dygn))
            + _rastorlek(dygn, minne)
            + bevisandel)

def _frirymdsbehov():
    """(behov, fri, matt_pa). Tre ganger det storsta HELA avtrycket bland de fem
    senast fardiga dygnen.

    INGET TAL AR HARDKODAT och inget tal bars vidare mellan korningar: troskeln
    raknas ut pa nytt varje gang, av arkivet som det ser ut da. Den forra
    versionen matte bara STATE-katalogen och kravde darfor mindre fri rymd an
    ett dygn kostar - en grind som inte kunde stoppa det den fanns till for.
    """
    fardiga = _fardiga_dygn()
    fri = shutil.disk_usage(DATA).free
    if not fardiga:
        return None, fri, "inget fardigt dygn att mata pa"
    minne, andel = {}, _bevisandel(len(fardiga))
    senaste = fardiga[-5:]
    storsta = max(_dygnets_avtryck(d, minne, andel) for d in senaste)
    return 3 * storsta, fri, (
        f"tre ganger det storsta hela avtrycket bland de {len(senaste)} senast fardiga "
        f"dygnen, {storsta / 2**30:.3f} GiB: STATE-katalog + rasnapshot + bevisandel "
        f"({andel / 2**20:.0f} MiB, snitt over {len(fardiga)} dygn)")

def step_preflight(day, nu_utc):
    """Forkontrollen, fore allt annat och bara i det harledda laget.

    Ordningen ar avsiktlig: luckorna skrivs ut aven nar nagot langre ner
    stoppar korningen, for det ar da de ar som mest varda att se.
    """
    print(f"\n[preflight] {day}")
    require_data()
    luckor = _luckor(day)
    print(f"        luckor: {len(luckor)} kalenderdygn utan fryst pre-manifest"
          + (" (" + ", ".join(luckor) + ")" if luckor else ""))
    _logga_luckor(nu_utc, day, luckor)
    gates.gate_frirymd(*_frirymdsbehov())
    gates.gate_korningsfonster(nu_utc, day)

def step_candidates(day, mentions):
    print(f"\n[candidates] {day}")
    cands = candidates.build(day, mentions)
    gates.gate_candidates(cands, day)
    gates.gate_registry(cands, REGISTRY, registry_version(), candidates.load_registry())
    # Poolen ar HELA kandidatlistan, inte topp 1500. Urvalet maste kunna uppfylla
    # regionkvoter och publisher cap bland kandidater som har bevis; en avhuggen
    # pool ger for fa lasbara i de tunna regionerna och kedjan stannar pa 579.
    pool = ranking.rank(cands)
    for c in pool:
        c["event_ids"] = sorted(c["event_ids"]) if isinstance(c["event_ids"], set) else c["event_ids"]
    write_text(sp.workdir(DATA, day) / "pool.json", json.dumps(pool, ensure_ascii=False))
    print(f"        {len(cands)} kandidater i poolen")
    return pool

def step_pool(day, budget):
    print("\n[pool] bevisfangst fore urval")
    pj = sp.workdir(DATA, day) / "pool.json"
    pool = json.loads(pj.read_text(encoding="utf-8"))
    new, left = pool_evidence.capture(pool, REGISTRY, budget=budget)
    print(f"        hamtade {new}, kvar {left}")
    if left:
        print("        POOLEN AR INTE FARDIG - kor steget igen"); sys.exit(2)
    pool_evidence.attach(pool)
    gates.gate_pool_evidence(pool)
    write_text(pj, json.dumps(pool, ensure_ascii=False))
    return pool

def step_select(day):
    print("\n[select]")
    pool = json.loads((sp.workdir(DATA, day) / "pool.json").read_text(encoding="utf-8"))
    pool_evidence.attach(pool)
    ok, dig = [], 0
    for c in pool:
        claim = claim_of(c.get("page_title"), c["domain"], c["url"])[0]
        if not readable(claim):
            continue
        if is_digest(claim):
            dig += 1; continue
        ok.append(c)
    print(f"        {len(ok)}/{len(pool)} kandidater har lasbar text ({dig} sammanfattningar bortsorterade)")

    chosen, report, near = select_day.select(ok, sp.state_id(day))
    gates.gate_selection(chosen, report, select_day.REGIONS,
                         select_day.PER_REGION, select_day.PUBLISHER_CAP)
    write_text(sp.workdir(DATA, day) / "chosen.json", json.dumps(chosen, ensure_ascii=False))

    # NAR SIDAN LASTES FOLJER MED IN I DET FRYSTA MANIFESTET. Det gjorde den inte
    # forut: hamtningen stamplades, stampeln bars genom hela kedjan och tappades
    # har, i steget som gor posten permanent. Utan den ar ett dygn fangat samma
    # dygn omojligt att skilja fran ett fangat tva veckor senare. Se FYND 011.
    cols = ["state_id", "tile_index", "grid_row", "grid_column", "observation_id", "family_key",
            "first_mention_utc", "representative_url", "representative_domain", "source_tier",
            "selection_layer", "review_region", "action_geo_country", "mention_rows",
            "registry_version", "evidence_http_status", "evidence_sha256",
            "evidence_retrieved_at", "evidence_basis",
            "series", "canonical_index", "prev_canonical_sha256"]
    rader = [{"state_id": c["state_id"], "tile_index": c["tile_index"],
              "grid_row": c["grid_row"], "grid_column": c["grid_column"],
              "observation_id": c["observation_id"], "family_key": c["family_key"],
              "first_mention_utc": c["first_mention_utc"], "representative_url": c["url"],
              "representative_domain": c["domain"], "source_tier": c["source_tier"],
              "selection_layer": c["selection_layer"], "review_region": c["review_region"],
              "action_geo_country": c.get("action_geo_country", ""),
              "mention_rows": c["mention_rows"], "registry_version": c["registry_version"],
              "evidence_http_status": c.get("http_status") or "",
              "evidence_sha256": c.get("content_sha256") or "",
              "evidence_retrieved_at": c.get("evidence_retrieved_at") or "",
              "evidence_basis": pool_evidence.basis(c, day)} for c in chosen]

    # KANONISKT MEDLEMSKAP. Beslut 2026-11-13. Rakningen sker pa raderna i
    # minnet, av samma skal som grinden nedan: talet ska vara avgjort innan
    # filen som gor det permanent finns pa disk.
    #
    # Golvet stoppar ingenting. Ett dygn under det fryses och publiceras som
    # alla andra och far bara inget nummer; serien ar numrerad, inte urvald.
    s = pool_evidence.serie(rader)
    fore, prev_sha, brott = pool_evidence.kedja(DATA, day)
    index = fore + 1 if s == "CANONICAL" else None
    gates.gate_kanonisk_kedja(s, index, brott)
    for r in rader:
        r["series"] = s
        r["canonical_index"] = f"{index:03d}" if index else ""
        r["prev_canonical_sha256"] = prev_sha
    med = sum(1 for r in rader if r["evidence_basis"] == "CAPTURED_IN_WINDOW")
    print(f"        series: {s} ({med}/{len(rader)} i fonstret = {med/len(rader):.1%}, golv "
          f"{pool_evidence.GOLV_KANONISK:.0%})"
          + (f", nummer {index:03d}" if index else "")
          + (f", bakat {prev_sha[:16]}" if prev_sha else ", forst i serien"))

    # GRINDEN GAR FORE SKRIVNINGEN. Raderna finns fardiga i minnet, sa att
    # "manifestet saknar datering" gar att veta innan filen ar skriven i stallet
    # for efterat, nar den redan ar den frysta posten. Jamfor 8f065a8.
    gates.gate_evidence_time(rader, pool_evidence.BEVISNIVAER)

    pre = sp.pre_manifest(DATA, day)
    with atomic_write(pre) as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rader)
    print(f"        {pre.name}")

    # near_duplicates() returnerar {"a": kandidat, "b": kandidat, "jaccard": tal}.
    # Skrivningen gjorde tidigare w.writerow([row]) for allt som inte var list
    # eller tuple, sa varje rad blev EN cell med en dict-repr av tva hela
    # kandidatposter under rubriken url_a,url_b,jaccard. Kolumnerna var tomma.
    # Loftet att gransfallen 0,20-0,25 syns offentligt uppfylldes alltsa inte,
    # och ingen upptackte det: audit_state hashar filen och build_site raknar
    # rader, men ingen laser kolumnerna.
    nd = sp.near_duplicate(DATA, day)
    with atomic_write(nd) as fh:
        w = csv.writer(fh)
        w.writerow(["url_a", "url_b", "jaccard", "domain_a", "domain_b"])
        for row in near:
            a, b = row["a"], row["b"]
            w.writerow([a["url"], b["url"], row["jaccard"], a["domain"], b["domain"]])
    print(f"        {nd.name} ({len(near)} rader)")

    write_text(sp.selection_report(DATA, day), json.dumps(report, ensure_ascii=False, indent=1))
    print("       ", {k: report[k] for k in ("kandidater", "efter_storytak", "valda")})
    return chosen

def step_input(day):
    print("\n[input]")
    chosen = json.loads((sp.workdir(DATA, day) / "chosen.json").read_text(encoding="utf-8"))
    items = []
    for c in chosen:
        claim, src = claim_of(c.get("page_title"), c["domain"], c["url"])
        items.append({"observation_id": c["observation_id"], "tile_index": c["tile_index"],
                      "observation_timestamp_utc": c["first_mention_utc"],
                      "neutral_source_claim": claim, "claim_source": src,
                      "review_region": c["review_region"], "selection_layer": c["selection_layer"],
                      "source_tier": c["source_tier"], "representative_domain": c["domain"]})
    gates.gate_claims(items, readable, is_digest)
    d = sp.classifier_input(DATA, day); d.mkdir(parents=True, exist_ok=True)
    bs = canonical_batch_size()          # ur specen, aldrig hardkodad
    for k in range(0, len(items), bs):
        write_text(d / f"batch_{k//bs+1:02d}.json",
                   json.dumps(items[k:k+bs], ensure_ascii=False, indent=1))
    print(f"        {len(items)} observationer -> {d.name}/")
    return items

def step_emotion(day):
    print("\n[emotion]")
    items = []
    for f in sorted(sp.classifier_input(DATA, day).glob("batch_*.json")):
        items += json.loads(f.read_text(encoding="utf-8"))
    p = sp.emotion_manifest(DATA, day)
    if not p.exists():
        print(f"        emotionsmanifestet saknas: {p.name}"); sys.exit(3)
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    gates.gate_emotion(items, rows, set(EMOTION_STATES))
    print(f"        {p.name} godkant — kor nu: python3 src/run_color.py {day}")
    return rows

def main():
    args = sys.argv[1:]
    if "--help" in args or "-h" in args:
        sys.exit(__doc__)
    # ENDA KLOCKAVLASNINGEN I KEDJAN. Harifran ar dygnet en strang.
    nu = datetime.now(timezone.utc)
    harlett = not args or args[0].startswith("-")
    day = senast_stangda_dygnet(nu) if harlett else args.pop(0)
    sp.state_id(day)                      # validerar formatet, kastar vid fel
    start = args[args.index("--stage") + 1] if "--stage" in args else "candidates"
    budget = int(args[args.index("--budget") + 1]) if "--budget" in args else None

    todo = STAGES[STAGES.index(start):]
    print(f"=== {sp.state_id(day)} — urval och klassificeringsinput ==="
          + ("  (dygnet harlett ur klockan)" if harlett else ""))
    try:
        # FORE RASNAPSHOTET. Ar det for tidigt saknas snapshotet ocksa, och da
        # ska svaret vara att klockan inte ar slagen - inte att filen saknas.
        if harlett:
            step_preflight(day, nu)
        hits = (sorted(raw_day_dir(day).glob(f"*{day}*MENTIONS.zip"))
                or sorted(RAW_GDELT.glob(f"*{day}*MENTIONS.zip")))
        if not hits:
            print(f"hittar inget rasnapshot for {day} — kor forst: python3 src/acquire.py {day}")
            sys.exit(4)
        if "candidates" in todo: step_candidates(day, hits[0])
        if "pool" in todo: step_pool(day, budget)
        if "select" in todo: step_select(day)
        if "input" in todo: step_input(day)
        if "emotion" in todo: step_emotion(day)
    except gates.GateFailure as e:
        print(f"\nKEDJAN STOPPAD: {e}"); sys.exit(1)
    print("\nKlart.")

if __name__ == "__main__":
    main()
