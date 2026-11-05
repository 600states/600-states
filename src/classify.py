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
from vocab import EMOTION_STATES, ORDER
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
    "No prose before or after the array.\n"
    # Formatering, inte innehall: protokollet specificerar vad raderna ska
    # innehalla, inte hur de ska se ut. Indraget svar kostade 1 134 rader for
    # 41 objekt, och blanksteg debiteras som output.
    "Return compact JSON: no indentation, no line breaks between objects, "
    "no spaces after separators."
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
        # Felet ska namna skillnaden. "scores har inte exakt 16 nycklar" kraver
        # ett nytt anrop for att forstas; vilka nycklar som saknas och vilka som
        # ar over gar att atgarda direkt. Valideringen ar oforandrat strikt -
        # ingenting fylls i, droppas eller normaliseras, vi mater bara battre.
        if not isinstance(s, dict):
            fel.append(f"{oid}: scores saknas eller ar inte ett objekt"); continue
        if set(s) != V:
            fel.append(f"{oid}: scores matchar inte protokollets 16 nycklar "
                       f"({len(s)} angivna) — saknar {sorted(V - set(s)) or 'inget'}, "
                       f"over {sorted(set(s) - V) or 'inget'}"); continue
        ut = {k: v for k, v in s.items()
              if not isinstance(v, (int, float)) or not 0 <= v <= 1}
        if ut:
            fel.append(f"{oid}: poang utanfor 0-1: {ut}")
        # Rankkontrollerna mot primary och secondary ar borta: falten harleds nu
        # ur scores i parse(), sa en kontroll av dem vore en kontroll av var egen
        # aritmetik. Kvar star kravet att modellen LEVERERAR sin egen bedomning.
        # Vi slutar krava att den stammer, inte att den finns.
        for k in ("stated_primary", "stated_secondary"):
            if not str(r.get(k) or "").strip():
                fel.append(f"{oid}: {k} saknas i svaret")
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
    """Specen kraver att gleshet och numerisk upplosning rapporteras.

    Dartill hur ofta modellens egen etikett skiljer sig fran den harledda. En
    modell vars narrativ och siffror drar isar ofta ar matbart samre, oavsett
    pris, och siffran ar gratis har - kalibreringsbatteriet far den utan eget
    anrop."""
    nz = [sum(1 for v in r["scores"].values() if v > 0) for r in rows]
    return {"authored_scores_median": statistics.median(nz),
            "rows_with_two_or_fewer": sum(1 for n in nz if n <= 2),
            "unique_intensity": len({r["intensity"] for r in rows}),
            "unique_confidence": len({r["confidence"] for r in rows}),
            "stated_primary_differs":
                sum(1 for r in rows if r.get("stated_primary") != r.get("primary_emotion")),
            "stated_secondary_differs":
                sum(1 for r in rows if r.get("stated_secondary") != r.get("secondary_emotion"))}

def call(client, model, prompt, items):
    """Ett anrop. Prefixet cachas, batchen ar det enda som varierar.

    TAENKANDET AR AVSTANGT, och det ar en instrumentparameter. Opus 5 taenker
    adaptivt som standard; taenkandets tokens raknas mot max_tokens och kommer
    tillbaka tomma. Forsta anropet matte stop_reason=max_tokens med 16000
    output-tokens och noll tecken text — modellen taenkte upp hela budgeten
    innan svaret boerjade. Taenkandets innehall returneras inte heller, sa det
    ar ett resonemangssteg utan harledning i ett instrument vars hela ansprak
    ar granskbarhet. Ett verk klassificerat med taenkande ar inte samma
    instrument som ett utan.

    TAKET AR MAETT, INTE VALT. Med taenkandet av gav 16000 output-tokens
    41-42 kompletta rader av 60 i alla tre forsoken — matt 2026-11-05 pa
    batch 01, alltsa 387 output-tokens per rad. Sextio rader kraver 23 250.
    32000 ar den matta storheten plus marginal, inte ett runt tal.

    STROEMMAT. SDK:n vagrar ett vanligt anrop med sa hogt max_tokens — den
    kastar ValueError lokalt, innan begaran skickas, for att svaret kan ta
    langre tid an tiominutersgransen. Stroemning har ingen sadan grans.
    get_final_message() ger samma Message-objekt som create() gav, sa
    raw_text(), parse(), usage och stop_reason ar oforandrade.
    """
    with client.messages.stream(
        model=model, max_tokens=32000,
        thinking={"type": "disabled"},
        system=[{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": OUTPUT_RULE, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": json.dumps(
            [{k: it[k] for k in ("observation_id", "tile_index", "observation_timestamp_utc",
                                 "neutral_source_claim", "review_region", "selection_layer",
                                 "source_tier", "representative_domain") if k in it} for it in items],
            ensure_ascii=False)}],
    ) as s:
        return s.get_final_message()

def raw_text(msg):
    """Svarets text, oforandrad. Separat fran parse sa att den gar att spara
    aven nar parsningen faller."""
    return "".join(b.text for b in msg.content if b.type == "text")

def usage_fields(msg):
    """Hela usage, inte de falt vi trodde oss behova. Sexton tusen tokens kunde
    forsvinna utan ett tecken text, och det syntes ingenstans."""
    u = getattr(msg, "usage", None)
    if u is None:
        return {}
    try:
        return u.to_dict()
    except Exception:
        return dict(vars(u))

def block_types(msg):
    """Vilka blocktyper svaret bestod av. Ett tomt textblock och ett uteblivet
    svar ser likadana ut i texten, men inte har."""
    try:
        return [b.type for b in msg.content]
    except Exception:
        return []

def spara_misslyckat(d, p, n, attempt, msg, fel=None):
    """Ett anrop som inte leder till en sparad batch ska lamna lika mycket spar
    som ett som gor det. Galler bada vagarna ut: undantag OCH valideringsmiss.
    Forut skrev valideringsgrenen ingenting, sa tre anrop som gav giltig JSON
    med nagra felaktiga rader lamnade bara ett antal och det forsta felet - och
    radarna som behovdes for att forsta varfor var borta."""
    raw = raw_text(msg) if msg is not None else ""
    fil = d / f"FAILED_pass{p}_batch_{n:02d}_forsok{attempt}.txt"
    write_text(fil, raw)
    if fel:
        # Hela fellistan, inte antalet och det forsta: ett fel som upprepas i
        # alla tre forsoken ar en annan sak an ett som varierar, och den
        # skillnaden syns bara i hela listan.
        write_text(d / (fil.stem + ".fel.txt"), "\n".join(fel))
    print(f"    stop_reason={getattr(msg, 'stop_reason', None)}  "
          f"svar {len(raw):,} tecken  block {block_types(msg)}")
    print(f"    usage {usage_fields(msg)}")
    print(f"    rasvar sparat: {fil.name}" + (f" + {fil.stem}.fel.txt" if fel else ""))
    return fil

def derive(s):
    """primary och secondary ur poangen.

    Specen sager primary_must_rank_first och secondary_must_rank_second. Den
    definierar alltsa faltet som harlett, och att rakna fram det ar den
    strangaste tillampningen av regeln - inte en uppmjukning av den.

    REN FUNKTION AV VARDENA. Vid lika poang vinner lagsta index i den frysta
    EMOTION_STATES-ordningen, samma skiljedomarregel som vocab.arbitrate()
    anvander vid konsensus. Nyckelordningen i modellens JSON far aldrig paverka
    resultatet - vore den med i sorteringen vore faltet inte reproducerbart."""
    rank = sorted(s, key=lambda e: (-s[e], ORDER[e]))
    return rank[0], rank[1]

def parse(msg):
    """Text till rader, plus antalet strukna emissionsartefakter.

    Ingen forlatande parsning: JSON-regeln ar oforandrad. Darefter tva steg som
    bada ar protokollets egna, fore validate():

    TOMNAMNAD NYCKEL STRYKS OCH RAKNAS. Matt 2026-11-05 pa batch 01: en rad av
    60 fick en sjuttonde poangnyckel med tomt namn, "Fatigue":0.28,"":0 — alla
    sexton riktiga nycklar ratta, plus ett emissionsfel i kompakt JSON. Bara
    exakt den tomma strangen stryks. VARJE annan extra nyckel faller
    valideringen som forut: en felstavad emotion som "Joie" ar en helt annan
    sak an ett emissionsfel och far aldrig smyga igenom. Defekten doljs inte,
    den raknas - antalet gar till korjournalen som emission_artifacts.

    PRIMARY OCH SECONDARY HARLEDS. Modellens egna varden behalls som
    stated_primary och stated_secondary; faltens varden kommer ur scores. Se
    derive()."""
    txt = re.sub(r"^```(?:json)?|```$", "", raw_text(msg).strip(), flags=re.M).strip()
    rows = json.loads(txt)
    V, artefakter = set(EMOTION_STATES), 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        s = r.get("scores")
        if isinstance(s, dict) and "" in s:
            del s[""]
            artefakter += 1
        r["stated_primary"] = r.get("primary_emotion")
        r["stated_secondary"] = r.get("secondary_emotion")
        # Harled bara nar poangen gar att harleda ur. Ar de trasiga lamnas
        # falten som modellen gav dem och validate() rapporterar poangfelet.
        if (isinstance(s, dict) and set(s) == V
                and all(isinstance(v, (int, float)) for v in s.values())):
            r["primary_emotion"], r["secondary_emotion"] = derive(s)
    return rows, artefakter

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
    # thinking_disabled star bredvid modell och prompthash for att det ar en
    # instrumentparameter, inte en implementationsdetalj: ett verk klassificerat
    # med taenkande ar inte samma instrument som ett utan.
    rec = {"state_id": sp.state_id(day), "model": model, "thinking_disabled": True,
           "prompt_sha256": sha(PROMPT_FILE), "spec_sha256": sha(SPEC_FILE),
           "batch_size": len(bs[0][1]), "calls": []}
    gjorda = parse_fel_totalt = 0
    for p, n, items in todo:
        if budget is not None and gjorda >= budget:
            print(f"\n  budget {budget} nadd, {len(todo) - gjorda} anrop kvar — kor steget igen")
            return 2
        parse_fel = 0
        for attempt in range(1, MAX_TRIES + 1):
            t0 = time.time()
            msg = None
            try:
                msg = call(client, model, prompt, items)
                rows, artefakter = parse(msg)
                usage = msg.usage
            except (anthropic.APIError, json.JSONDecodeError) as e:
                # Bara fel som uppstod efter att begaran gick ivag far ett nytt
                # forsok. Ett fel fore dess ar ett konfigurationsfel - fel
                # parameter, fel modellnamn, saknad nyckel - och det kan aldrig
                # lyckas vid forsok tva. Tre omforsok med sleep emellan doljer
                # da signalen i en obevakad daglig korning och kostar tid utan
                # att nagot anrop gors. JSONDecodeError hor till denna sida:
                # svaret kom fram men gick inte att lasa, och nasta forsok kan
                # ge ett annat svar.
                #
                # Ett anrop som misslyckas ska lamna lika mycket spar som ett som
                # lyckas. Forut skrevs bara undantagets klassnamn, och rasvaret -
                # det enda som kan saga varfor - kastades. Da ser ett avhugget
                # svar ut som ett trasigt svar.
                # Trasig JSON mitt i ett komplett svar raknas for sig. Ett fall
                # av tre forsok matt 2026-11-05: modellen stakade sig och skrev
                # halva faltet tva ganger. Haller den andelen i sig blir det ett
                # tiotal omkorningar om dygnet. Andelen ska matas over flera
                # dygn innan formatkravet ror sig - darfor en raknare, ingen
                # atgard.
                if isinstance(e, json.JSONDecodeError):
                    parse_fel += 1
                    parse_fel_totalt += 1
                print(f"  pass{p} batch{n:02d} forsok {attempt}: {type(e).__name__}: {e}")
                spara_misslyckat(d, p, n, attempt, msg)
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
                print(f"  pass{p} batch{n:02d} forsok {attempt}: {len(fel)} valideringsfel "
                      f"pa {len(rows)} rader")
                spara_misslyckat(d, p, n, attempt, msg, fel)
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
                                 "block_types": block_types(msg),
                                 "emission_artifacts": artefakter,
                                 "parse_failures": parse_fel, **dg})
            print(f"  pass{p} batch{n:02d}  {len(rows)} rader  "
                  f"{dg['authored_scores_median']:.0f}/16 egna poang  "
                  f"cache {getattr(usage,'cache_read_input_tokens',0):,}")
            print(f"    uttalat mot harlett: primary {dg['stated_primary_differs']}, "
                  f"secondary {dg['stated_secondary_differs']}  "
                  f"emissionsartefakter {artefakter}")
            break
        gjorda += 1

    # Ocksa nar ingen batch gick igenom: en korning dar allt foll pa trasig JSON
    # ar just den matning andelen ska bygga pa, och den far inte vara den enda
    # som inte lamnar nagon journal.
    if rec["calls"] or parse_fel_totalt:
        c = rec["calls"]
        rec["totals"] = {"calls": len(c), "input": sum(x["input_tokens"] for x in c),
                         "output": sum(x["output_tokens"] for x in c),
                         "cache_read": sum(x["cache_read"] for x in c),
                         "parse_failures": parse_fel_totalt}
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
