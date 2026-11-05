"""Klassificeringssteget. Anropar API:et direkt, inte som agent.

    python3 src/classify.py <AAAAMMDD> [--pass N] [--budget N] [--model ID] [--dry-run]

Kedjans andra ande. Tidigare kordes klassificeringen utanfor kedjan, for hand,
vilket gjorde ett dygn omojligt att kora oovervakat.

TRE OBEROENDE PASS. Konsensus tar majoritet pa tillstanden och MEDIAN pa
intensity och confidence. Median kraver tre varden - uppmatt pa 610
observationer ar p1 och p2 lika i 15,6 procent av fallen for intensity och
13,0 procent for confidence. Att hoppa over pass 3 nar de tva forsta ar
overens ger alltsa fel resultat i de allra flesta rutor.

TEMPERATUREN SATTS INTE TILL NOLL. Passens oberoende ar sjalva matningen.
Med deterministisk sampling blir de tre passen identiska och konsensus
meningslos - spridningen ar det instrumentet mater, inte brus att ta bort.

PROMPT CACHING. Instruktionen ar identisk i alla anrop, varje dygn, over alla
verk. Prefixet markeras cache_control sa att det kostar en brakdel efter
forsta anropet.

GRINDEN FORE FORSTA ANROPET: promptfilens sha256 maste stamma mot den som
exekveringsspecen anger. Stammer den inte ar instrumentet inte det som
beskrivs, och korningen avbryts.
"""
import hashlib, json, os, re, statistics, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
import gates
from atomic import write_text
from vocab import EMOTION_STATES
from config import DATA, FROZEN

PROMPT_FILE = FROZEN / "600_STATES_Emotion_Classification_Execution_Prompt_v2.1_FROZEN.txt"
SPEC_FILE   = FROZEN / "600_STATES_Emotion_Classification_Execution_Spec_v2.1_FROZEN.json"
PASSES      = (1, 2, 3)
MAX_TRIES   = 3
DEFAULT_MODEL = os.environ.get("STATES_MODEL", "claude-opus-5")

OUTPUT_RULE = (
    "Return ONLY a JSON array. One object per supplied observation, in the same order, "
    "with exactly these keys: observation_id, neutral_event_representation, scores, "
    "primary_emotion, secondary_emotion, intensity, confidence, classification_note.\n"
    "scores must contain all sixteen states as keys, each a number between 0 and 1, "
    "each independently authored. Do not zero-fill. primary_emotion is the highest "
    "score, secondary_emotion the second highest and different from it. "
    "intensity and confidence are numbers between 0 and 1 with two decimals. "
    "No prose before or after the array."
)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def gate_instrument():
    spec = json.loads(SPEC_FILE.read_text(encoding="utf-8"))
    want, got = spec["canonical_prompt_sha256"], sha(PROMPT_FILE)
    gates._say("exekveringsprompten finns", PROMPT_FILE.exists(), PROMPT_FILE.name)
    gates._say("promptens sha256 stammer mot specen", want == got, f"{got[:16]} mot {want[:16]}")
    return PROMPT_FILE.read_text(encoding="utf-8"), spec

def batches(day):
    d = sp.classifier_input(DATA, day)
    fs = sorted(d.glob("batch_*.json"))
    if not fs:
        raise SystemExit(f"ingen klassificerarinput for {sp.state_id(day)} — kor run_state forst")
    return [(int(re.search(r"batch_(\d+)", f.name).group(1)),
             json.loads(f.read_text(encoding="utf-8"))) for f in fs]

def passdir(day):
    d = sp.outdir(DATA, day) / "classifier_passes"
    d.mkdir(parents=True, exist_ok=True)
    return d

def validate(rows, inp):
    """Returnerar lista med fel. Tom lista = godkant. Foljer specens validation_policy."""
    fel = []
    if len(rows) != len(inp):
        fel.append(f"{len(rows)} rader mot {len(inp)} observationer")
        return fel
    want = {i["observation_id"] for i in inp}
    if {r.get("observation_id") for r in rows} != want:
        fel.append("observation_id stammer inte mot indata")
    V = set(EMOTION_STATES)
    for r in rows:
        oid = str(r.get("observation_id"))[:22]
        s = r.get("scores")
        if not isinstance(s, dict) or set(s) != V:
            fel.append(f"{oid}: scores har inte exakt 16 nycklar"); continue
        if any(not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in s.values()):
            fel.append(f"{oid}: poang utanfor 0-1")
        rank = sorted(s, key=lambda e: -s[e])
        if r.get("primary_emotion") != rank[0]:
            fel.append(f"{oid}: primary ar inte hogsta poang")
        if r.get("secondary_emotion") != rank[1]:
            fel.append(f"{oid}: secondary ar inte nast hogsta")
        if r.get("primary_emotion") == r.get("secondary_emotion"):
            fel.append(f"{oid}: primary och secondary lika")
        for k in ("intensity", "confidence"):
            v = r.get(k)
            if not isinstance(v, (int, float)) or not 0 <= v <= 1:
                fel.append(f"{oid}: {k} utanfor 0-1")
        if not str(r.get("classification_note", "")).strip():
            fel.append(f"{oid}: ingen classification_note")
    return fel

def diagnostics(rows):
    """Specen kraver att gleshet och numerisk upplosning rapporteras."""
    nz = [sum(1 for v in r["scores"].values() if v > 0) for r in rows]
    return {"authored_scores_median": statistics.median(nz),
            "rows_with_two_or_fewer": sum(1 for n in nz if n <= 2),
            "unique_intensity": len({r["intensity"] for r in rows}),
            "unique_confidence": len({r["confidence"] for r in rows})}

def call(client, model, prompt, items):
    """Ett anrop. Prefixet cachas, batchen ar det enda som varierar."""
    msg = client.messages.create(
        model=model, max_tokens=16000,
        system=[{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": OUTPUT_RULE, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": json.dumps(
            [{k: it[k] for k in ("observation_id", "tile_index", "observation_timestamp_utc",
                                 "neutral_source_claim", "review_region", "selection_layer",
                                 "source_tier", "representative_domain") if k in it} for it in items],
            ensure_ascii=False)}],
    )
    txt = "".join(b.text for b in msg.content if b.type == "text").strip()
    txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.M).strip()
    return json.loads(txt), msg.usage

def run(day, only_pass=None, budget=None, model=DEFAULT_MODEL, dry=False):
    sp.state_id(day)
    print(f"=== {sp.state_id(day)} — klassificering ===")
    prompt, spec = gate_instrument()
    bs = batches(day)
    n_obs = sum(len(b) for _, b in bs)
    gates._say("input tacker 600 observationer", n_obs == 600, f"{n_obs} i {len(bs)} batchar")
    if len(bs[0][1]) != spec["canonical_batch_size"]:
        print(f"  NOTERA batchstorlek {len(bs[0][1])}, specen anger "
              f"{spec['canonical_batch_size']} — oavgjord divergens, se handover")

    d = passdir(day)
    todo = [(p, n, items) for p in (PASSES if only_pass is None else (only_pass,))
            for n, items in bs if not (d / f"pass{p}_batch_{n:02d}.json").exists()]
    print(f"\n  {len(todo)} anrop kvar av {len(PASSES) * len(bs)}")

    if dry:
        chars = len(prompt) + len(OUTPUT_RULE)
        print(f"  TORRKORNING — inget anrop gors")
        print(f"  cachat prefix {chars:,} tecken, cirka {chars // 4:,} tokens")
        print(f"  per anrop tillkommer batchen, cirka {len(json.dumps(bs[0][1])) // 4:,} tokens")
        print(f"  modell {model}")
        return 0

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("\n  ANTHROPIC_API_KEY saknas.")
        print('  Windows:  setx ANTHROPIC_API_KEY "sk-ant-..."  (starta om skalet efterat)')
        print('  bash:     export ANTHROPIC_API_KEY="sk-ant-..."')
        return 4

    import anthropic
    client = anthropic.Anthropic(api_key=key)
    rec = {"state_id": sp.state_id(day), "model": model,
           "prompt_sha256": sha(PROMPT_FILE), "spec_sha256": sha(SPEC_FILE),
           "batch_size": len(bs[0][1]), "calls": []}
    gjorda = 0
    for p, n, items in todo:
        if budget is not None and gjorda >= budget:
            print(f"\n  budget {budget} nadd, {len(todo) - gjorda} anrop kvar — kor steget igen")
            return 2
        for attempt in range(1, MAX_TRIES + 1):
            t0 = time.time()
            try:
                rows, usage = call(client, model, prompt, items)
            except Exception as e:
                print(f"  pass{p} batch{n:02d} forsok {attempt}: {type(e).__name__}")
                time.sleep(2 * attempt); continue
            fel = validate(rows, items)
            dg = diagnostics(rows)
            # Nollfyllningsdefekten passerar validering men ar det fel som
            # ogiltigforklarade pilotserien: fjorton av sexton poang mekaniskt
            # satta till noll. Specen kallar det en diagnostisk varning; i drift
            # kor vi om batchen i stallet for att spara den.
            if not fel and dg["authored_scores_median"] <= 2:
                fel = [f"glest poangvektor, median {dg['authored_scores_median']:.0f}/16 "
                       f"egna poang — protokollet har inte foljts"]
            if fel:
                print(f"  pass{p} batch{n:02d} forsok {attempt}: {len(fel)} valideringsfel, "
                      f"forst: {fel[0]}")
                if attempt == MAX_TRIES:
                    print("  GER UPP pa denna batch"); break
                continue
            write_text(d / f"pass{p}_batch_{n:02d}.json",
                       json.dumps(rows, ensure_ascii=False, indent=1))
            rec["calls"].append({"pass": p, "batch": n, "rows": len(rows),
                                 "seconds": round(time.time() - t0, 1),
                                 "input_tokens": usage.input_tokens,
                                 "output_tokens": usage.output_tokens,
                                 "cache_read": getattr(usage, "cache_read_input_tokens", 0),
                                 "cache_write": getattr(usage, "cache_creation_input_tokens", 0),
                                 **dg})
            print(f"  pass{p} batch{n:02d}  {len(rows)} rader  "
                  f"{dg['authored_scores_median']:.0f}/16 egna poang  "
                  f"cache {getattr(usage,'cache_read_input_tokens',0):,}")
            break
        gjorda += 1

    if rec["calls"]:
        c = rec["calls"]
        rec["totals"] = {"calls": len(c), "input": sum(x["input_tokens"] for x in c),
                         "output": sum(x["output_tokens"] for x in c),
                         "cache_read": sum(x["cache_read"] for x in c)}
        write_text(sp.outdir(DATA, day) / f"600_STATES_{sp.state_key(day)}_CLASSIFIER_RUN.json",
                   json.dumps(rec, ensure_ascii=False, indent=1))
        print(f"\n  {rec['totals']}")

    kvar = [f"pass{p}_batch_{n:02d}" for p in PASSES for n, _ in bs
            if not (d / f"pass{p}_batch_{n:02d}.json").exists()]
    gates._say("alla 3 pass tacker alla batchar", not kvar,
               "komplett" if not kvar else f"{len(kvar)} saknas, forst {kvar[0]}")
    print(f"\n  klart — kor nu: python3 src/consensus.py {day} {d}")
    return 0

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    a = sys.argv[2:]
    try:
        sys.exit(run(sys.argv[1],
                     int(a[a.index("--pass") + 1]) if "--pass" in a else None,
                     int(a[a.index("--budget") + 1]) if "--budget" in a else None,
                     a[a.index("--model") + 1] if "--model" in a else DEFAULT_MODEL,
                     "--dry-run" in a))
    except gates.GateFailure as e:
        print(f"\nKEDJAN STOPPAD: {e}"); sys.exit(1)

if __name__ == "__main__":
    main()
