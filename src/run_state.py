"""Kor hela kedjan for ett dygn. Ett kommando, grindar mellan varje steg.

    python3 src/run_state.py 20260101 001 [--stage NAMN] [--budget N]

Steg, i ordning:
    candidates  GDELT -> kandidatlista            grind: dygn, mention_rows
    pool        bevisfangst pa topp 1500          grind: rubriktackning
    select      600 valda bland lasbara           grind: 600, regionkvoter, cap
    input       klassificerarens input            grind: varje rad har text
    --- klassificeringen kors utanfor och lagger emotion-manifestet pa plats ---
    emotion     kontroll av emotionsmanifestet    grind: ID-mangd, vokabular, spridning
    color       hex ur protokollet                grind: varje hex reproduceras
    render      PNG + hashar

Avbryter med felkod nar en grind stoppar. En regel som inte kan stoppa en
korning ar inte en regel.
"""
import csv, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
from config import DATA
import candidates, ranking, select_day, pool_evidence, gates
from color_protocol import hex_of_row, VOCAB
from build_classifier_input import claim_of, readable

REGISTRY = DATA / "00_CANONICAL_PROJECT_DOCS/01_FROZEN_PROTOCOL_LIBRARY_v1.0/600_STATES_Source_Registry_v2.0_FROZEN.csv"
STAGES = ["candidates", "pool", "select", "input", "emotion", "color", "render"]

def outdir(state): return DATA / "08_V3_STATES" / f"STATE_{state}"
def work(state):
    d = outdir(state) / "_work"; d.mkdir(parents=True, exist_ok=True); return d

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def step_candidates(day, state, mentions):
    print(f"\n[candidates] {day}")
    cands = candidates.build(day, mentions)
    gates.gate_candidates(cands, day)
    # Poolen ar HELA kandidatlistan, inte topp 1500. Urvalet maste kunna uppfylla
    # regionkvoter och publisher cap bland kandidater som har bevis; en avhuggen
    # pool ger for fa lasbara i de tunna regionerna och kedjan stannar pa 579.
    pool = ranking.rank(cands)
    for c in pool: c["event_ids"] = sorted(c["event_ids"]) if isinstance(c["event_ids"], set) else c["event_ids"]
    (work(state) / "pool.json").write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
    print(f"        {len(cands)} kandidater, poolen ar topp {len(pool)}")
    return pool

def step_pool(state, budget):
    print("\n[pool] bevisfangst fore urval")
    pool = json.loads((work(state) / "pool.json").read_text(encoding="utf-8"))
    new, left = pool_evidence.capture(pool, REGISTRY, budget=budget)
    print(f"        hamtade {new}, kvar {left}")
    if left:
        print("        POOLEN AR INTE FARDIG - kor steget igen"); sys.exit(2)
    pool_evidence.attach(pool)
    gates.gate_pool_evidence(pool)
    (work(state) / "pool.json").write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
    return pool

def step_select(state, day):
    print("\n[select]")
    pool = json.loads((work(state) / "pool.json").read_text(encoding="utf-8"))
    pool_evidence.attach(pool)
    ok = [c for c in pool if readable(claim_of(c.get("page_title"), c["domain"], c["url"])[0])]
    print(f"        {len(ok)}/{len(pool)} kandidater har lasbar text")
    chosen, report, near = select_day.select(ok, f"2026-{state}")
    gates.gate_selection(chosen, report, select_day.REGIONS, select_day.PER_REGION, select_day.PUBLISHER_CAP)
    (work(state) / "chosen.json").write_text(json.dumps(chosen, ensure_ascii=False), encoding="utf-8")
    (outdir(state) / f"600_STATES_2026_{state}_SELECTION_REPORT_v3.1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("       ", {k: report[k] for k in ("kandidater", "efter_storytak", "valda")})
    return chosen

def step_input(state):
    print("\n[input]")
    chosen = json.loads((work(state) / "chosen.json").read_text(encoding="utf-8"))
    items = []
    for c in chosen:
        claim, src = claim_of(c.get("page_title"), c["domain"], c["url"])
        items.append({"observation_id": c["observation_id"], "tile_index": c["tile_index"],
                      "observation_timestamp_utc": c["first_mention_utc"],
                      "neutral_source_claim": claim, "claim_source": src,
                      "review_region": c["review_region"], "selection_layer": c["selection_layer"],
                      "source_tier": c["source_tier"], "representative_domain": c["domain"]})
    gates.gate_claims(items)
    d = outdir(state) / "classifier_input"; d.mkdir(parents=True, exist_ok=True)
    for k in range(0, len(items), 60):
        (d / f"batch_{k//60+1:02d}.json").write_text(
            json.dumps(items[k:k+60], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"        {len(items)} observationer -> {d.name}/")
    return items

def _load_emotion(state):
    p = outdir(state) / f"600_STATES_2026_{state}_EMOTION_COLOR_MANIFEST_v3.1_CONSENSUS.csv"
    if not p.exists():
        print(f"        emotionsmanifestet saknas: {p.name}"); sys.exit(3)
    return p, list(csv.DictReader(open(p, encoding="utf-8")))

def step_emotion(state):
    print("\n[emotion]")
    items = []
    for f in sorted((outdir(state) / "classifier_input").glob("batch_*.json")):
        items += json.loads(f.read_text(encoding="utf-8"))
    _, rows = _load_emotion(state)
    gates.gate_emotion(items, rows, set(VOCAB))
    return rows

def step_color(state):
    print("\n[color]")
    p, rows = _load_emotion(state)
    gates.gate_color(rows, hex_of_row)
    print(f"        manifest sha256 {sha(p)}")
    return rows

def step_render(state):
    print("\n[render]")
    from render import render_state
    png = render_state(state)
    print(f"        {Path(png).name}  sha256 {sha(png)}")

def main():
    day, state = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    start = args[args.index("--stage") + 1] if "--stage" in args else "candidates"
    budget = int(args[args.index("--budget") + 1]) if "--budget" in args else None
    raw = DATA / "01_RAW_GDELT_2026_001_010"
    hits = sorted(raw.glob(f"*{day}*MENTIONS.zip")) or sorted(raw.glob(f"*2026_{state}_GDELT2_MENTIONS.zip"))
    if not hits:
        print(f"hittar ingen mentions-zip for {day} i {raw.name}"); sys.exit(4)
    mentions = hits[0]
    todo = STAGES[STAGES.index(start):]
    try:
        if "candidates" in todo: step_candidates(day, state, mentions)
        if "pool" in todo: step_pool(state, budget)
        if "select" in todo: step_select(state, day)
        if "input" in todo: step_input(state)
        if "emotion" in todo: step_emotion(state)
        if "color" in todo: step_color(state)
        if "render" in todo: step_render(state)
    except gates.GateFailure as e:
        print(f"\nKEDJAN STOPPAD: {e}"); sys.exit(1)
    print("\nKlart.")

if __name__ == "__main__":
    main()
