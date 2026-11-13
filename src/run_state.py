"""Urval och klassificeringsinput for ett dygn. SEPARAT PROGRAM.

    python3 src/run_state.py 20261201 [--stage NAMN] [--budget N]

Dygnet ar enda indata. Ingen kod har laser systemklockan: daglig korning och
efterhandskorning av en aldre dag gar genom exakt samma kodvag, annars ar
dagarna inte jamforbara.

DETTA PROGRAM NAR ALDRIG FARGEN. Det importerar inte color_protocol och far
aldrig gora det. Farg och rendering ligger i run_color.py, som kors forst nar
emotionsmanifestet ar fryst. Separationen ar funktionen, inte stadning.

Steg, i ordning:
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
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
from atomic import atomic_write, write_text
from config import (DATA, RAW_GDELT, REGISTRY_FILE as REGISTRY, registry_version,
                    raw_day_dir, canonical_batch_size)
import candidates, ranking, select_day, pool_evidence, gates
from vocab import EMOTION_STATES
from build_classifier_input import claim_of, readable, is_digest

STAGES = ["candidates", "pool", "select", "input", "emotion"]

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
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    day = sys.argv[1]
    sp.state_id(day)                      # validerar formatet, kastar vid fel
    args = sys.argv[2:]
    start = args[args.index("--stage") + 1] if "--stage" in args else "candidates"
    budget = int(args[args.index("--budget") + 1]) if "--budget" in args else None

    hits = (sorted(raw_day_dir(day).glob(f"*{day}*MENTIONS.zip"))
            or sorted(RAW_GDELT.glob(f"*{day}*MENTIONS.zip")))
    if not hits:
        print(f"hittar inget rasnapshot for {day} — kor forst: python3 src/acquire.py {day}")
        sys.exit(4)

    todo = STAGES[STAGES.index(start):]
    print(f"=== {sp.state_id(day)} — urval och klassificeringsinput ===")
    try:
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
