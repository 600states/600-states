"""Klassificeringssteget. Anropar API:et direkt, inte som agent.

    python3 src/classify.py <AAAAMMDD> [--pass N] [--budget N] [--model ID]
                                      [--dry-run] [--live] [--slapp] [--en-i-taget]

Leveransen ar Batch API (halva listpriset, faststallt 2026-11-06). --live kor
direkta anrop i stallet, till fullt pris: for en enskild batch man vill se
svaret pa med en gang. --slapp skickar batchjobbet och gar ur; nasta korning
hamtar det. Jobbfilen pa disk ar skyddet mot att betala for samma jobb tva
ganger.

--en-i-taget skickar EN observation per begaran i stallet for femtio. Matvag for
FYND 009: med en observation finns ingen rad att halka mellan, och identiteten
kommer ur begaran. Den frysta prompten och specen ar oforandrade - avvikelsen
galler canonical_batch_size, och den noteras. Passfilerna blir identiska i form.
Journalen markerar dygnet med delivery_form, sa att det aldrig kan forvaxlas med
ett dygn kort pa den beslutade formen.

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
from config import DATA, FROZEN, SPEC_FILE

PROMPT_FILE = FROZEN / "600_STATES_Emotion_Classification_Execution_Prompt_v2.1_FROZEN.txt"
PASSES      = (1, 2, 3)
MAX_TRIES   = 3
DEFAULT_MODEL = os.environ.get("STATES_MODEL", "claude-opus-5")

# TAENKANDET AR EN INSTRUMENTPARAMETER. Hur den uttrycks skiljer sig per modell,
# och det ar transport, inte instruktion - ingen modell far en annan prompt.
# Men att en modell inte KAN uppfylla parametern ar ett resultat, inte en
# teknikalitet: uppmatt 2026-11-06 gav claude-opus-5-5 felet
# '"thinking.type.disabled" is not supported for this model', alltsa finns bara
# adaptivt taenkande med effort-reglering. Ett resonemangssteg vars innehall
# inte returneras gar da inte att undvika, och det ar vad vi avvisade.
TANKANDE = {
    "claude-opus-5":     {"type": "disabled"},
    "claude-haiku-5-5":  {"type": "disabled"},
    "claude-sonnet-5-5": {"type": "between_tools"},   # modellen taenker inte fore svaret
    # claude-opus-5-5 star med avsikt INTE har. Den accepterar bara "adaptive":
    # tankandet gar inte att stanga av. Tankandets innehall returneras inte, sa
    # det vore ett resonemangssteg utan harledning i ett instrument vars hela
    # anspraak ar granskbarhet. Beslutet 2026-11-05 galler, och det ar modellen
    # som faller pa det, inte tvartom. Priset ar lagre ($4/$20 mot $5/$25) och
    # saknar betydelse. Faller den bort ur tabellen av misstag ger anropet 400.
}

# EFFORT SKRIVS UT, DEN ARVS INTE.
#
# Det har ar INGEN parameterandring. Varje varde nedan ar modellens egna
# API-standardvarde per 2026-11-06, sa utfallet blir identiskt med alla
# korningar hittills - inklusive kalibreringen och 2026/308. Det som andras ar
# att vardet star i instrumentet i stallet for hos leverantoren.
#
# Tva skal, bada konkreta:
#   1. Standardvardena skiljer sig redan at mellan modeller - high pa opus-5 och
#      sonnet-5-5, medium pa haiku-5-5. Ett blankt "high" over alla hade andrat
#      haikus beteende och gjort dess kalibreringssiffror oreproducerbara.
#   2. "disabled" och "between_tools" accepteras BARA vid effort high eller
#      lagre; vid xhigh eller max svarar API:et 400. Hojs leverantorens
#      standardvarde nagon gang slutar klassificeraren fungera mitt i serien,
#      utan att en rad i var kod har andrats. Ett utskrivet varde kan det inte.
#
# Skillnaden mot temperaturen, som star kvar osatt: temperaturen ar ingen mater
# och ingen har beslutat, sa att satta den vore att hitta pa. Det har ar att
# skriva ned det som redan galler. Man far skriva ned det som ar sant. Man far
# inte hitta pa det ingen mätt.
EFFORT = {
    "claude-opus-5":     "high",
    "claude-sonnet-5-5": "high",
    "claude-haiku-5-5":  "medium",
}

# TEMPERATUREN FINNS INTE. Uppmatt 2026-11-06, efter ett misslyckat forsok att
# mata den.
#
# Temperaturen stod som projektets sista osatta parameter, med noten "ej satt;
# leverantorens standardvarde galler; omatt". Kalibreringsbatteriet byggdes ut
# for att mata vad den gor med utfallet. Anropet foll pa TypeError innan det
# lamnade maskinen:
#
#   Messages.stream() got an unexpected keyword argument 'temperature'
#
# Kontrollerat i tre led:
#   - anthropic 2.5.0, Messages.stream(): ingen temperature, ingen top_p i
#     signaturen
#   - samma paket, types/message_create_params.py: orden forekommer inte alls
#   - API-referensen for Messages: kroppens parametrar ar max_tokens, messages,
#     model, cache_control, container, diagnostics, inference_geo, metadata,
#     output_config, service_tier, speed, stop_sequences, stream, system,
#     thinking, tool_choice, tools. Varken temperature eller top_p namns.
#
# Samplingen ar alltsa inte en parameter nagon kan satta for den har
# modellgenerationen. Kontrollen heter effort, och den star utskriven ovan.
#
# Fragan ar darmed stangd, men inte genom en matning: det fanns ingenting att
# mata. Falten star kvar i korjournalen, for ett falt som forsvinner ur
# provenienskedjan laser som om fragan aldrig stallts.
TEMPERATUR = None
TEMPERATUR_NOT = ("API:et for denna modellgeneration tar ingen temperatur-"
                  "parameter; kontrollerat mot SDK:ns signatur och "
                  "API-referensen 2026-11-06; effort ar kontrollen")

def tankande_for(model):
    return TANKANDE.get(model, {"type": "disabled"})

def effort_for(model):
    """Modellens utskrivna effort. Saknas modellen hojs inget tyst: high ar det
    hogsta varde dar tankandet gar att stanga av alls."""
    return EFFORT.get(model, "high")

def ska_forsoka_igen(e):
    """Bara fel som kan bli ratt vid nasta forsok.

    Ett 400 blir aldrig ratt vid forsok tva: fel parameter ar fel parameter.
    Uppmatt 2026-11-06 i kalibreringen - nio rundresor av tre konfigurationsfel,
    eftersom BadRequestError arver APIError. Samma gransdragning som for
    ValueError: ett fel som uppstod innan begaran accepterades ar ett
    konfigurationsfel, och tre tysta omforsok doljer signalen."""
    import anthropic
    if isinstance(e, json.JSONDecodeError):
        return True                      # svaret kom fram, det var trasigt
    if isinstance(e, anthropic.APIStatusError):
        return e.status_code == 429 or e.status_code >= 500
    return isinstance(e, anthropic.APIError)   # anslutning, timeout

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
    "no spaces after separators.\n"
    # Uppmatt 2026-11-05 pa 2026/308 batch 03-05: modellen tappade en
    # observation, markte att antalet inte stamde, och hittade pa en rad med
    # suffixat id ("...-DUP") och nollfyllda poang - "No content supplied for
    # this slot". Fabricering for att uppfylla ett antal, och nollfyllningen ar
    # defekten som ogiltigforklarade pilotserien.
    "Echo observation_id exactly as supplied. Never modify, suffix or mark an "
    "id, and never invent one. Classify every supplied observation and nothing "
    "else. If you cannot produce a row for an input, omit that row rather than "
    "substituting a placeholder: a missing row is a measurement, a fabricated "
    "row is not. Two observations may carry near-identical text; that is "
    "intended, and each is classified independently under its own id."
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

def _for_manga_decimaler(v, prec):
    """Fler decimaler an specen tillater.

    Jamfor mot round() och inte mot repr(): ett varde som kom ur JSON som 0.06
    ar narmaste double till 0.06, och repr av ett BERAKNAT varde kan ge
    0.060000000000000005 utan att modellen skrivit nagot fel. Toleransen gor
    kontrollen till en fraga om vad modellen skrev, inte om flyttal."""
    return abs(float(v) - round(float(v), prec)) > 1e-9

def spec_precision():
    """Decimalkravet ur den frysta specen, aldrig hardkodat."""
    import json as _j
    sp_ = _j.loads(SPEC_FILE.read_text(encoding="utf-8"))
    v = {sp_.get("score_precision"), sp_.get("intensity_precision"),
         sp_.get("confidence_precision")}
    v.discard(None)
    if len(v) != 1:
        raise SystemExit(f"specens tre precisionsfalt sager olika: {sorted(v)}")
    return int(v.pop())

def validate(rows, inp):
    """Returnerar lista med fel. Tom lista = godkant. Foljer specens validation_policy."""
    fel = []
    if len(rows) != len(inp):
        # Ingen tidig retur: antalet ensamt sager inte vilka rader som fattas,
        # och id-diagnosen nedan ar det som gor felet atgardbart.
        fel.append(f"{len(rows)} rader mot {len(inp)} observationer")
    # Felet ska namna skillnaden. "stammer inte mot indata" kravde att nagon
    # lade sig i rasvaret for att forstas - tredje stallet i rad med den luckan.
    want = {i["observation_id"] for i in inp}
    got = [r.get("observation_id") for r in rows]
    saknas, over = sorted(want - set(got)), sorted(set(got) - want)
    dubbletter = sorted({x for x in got if got.count(x) > 1})
    if saknas or over or dubbletter:
        fel.append(f"observation_id stammer inte mot indata — "
                   f"saknas {saknas or 'inget'}, over {over or 'inget'}, "
                   f"dubbletter {dubbletter or 'inga'}")
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
        for k in ("stated_primary", "stated_secondary", "stated_observation_id"):
            if not str(r.get(k) or "").strip():
                fel.append(f"{oid}: {k} saknas i svaret")
        if r.get("primary_emotion") == r.get("secondary_emotion"):
            fel.append(f"{oid}: primary och secondary lika")
        for k in ("intensity", "confidence"):
            v = r.get(k)
            if not isinstance(v, (int, float)) or not 0 <= v <= 1:
                fel.append(f"{oid}: {k} utanfor 0-1")
        # Specen anger score_precision, intensity_precision och
        # confidence_precision = 2, och ingenting kontrollerade det. Ett krav
        # utan efterkontroll ar ett onskemal. Referensmodellen bryter det aldrig
        # - uppmatt 2026-11-06 pa 1800 rader, noll overtradelser - sa grinden
        # utesluter ingen modell som gor det specen kraver.
        prec = spec_precision()
        for namn, v in [(f"scores[{k}]", vv) for k, vv in (s.items() if isinstance(s, dict) else [])] \
                       + [("intensity", r.get("intensity")), ("confidence", r.get("confidence"))]:
            if isinstance(v, (int, float)) and _for_manga_decimaler(v, prec):
                fel.append(f"{oid}: {namn} har fler an {prec} decimaler: {v}")
                break
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
    return {"stated_id_differs":
                sum(1 for r in rows
                    if r.get("stated_observation_id") != r.get("observation_id")),
            "authored_scores_median": statistics.median(nz),
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

    INGEN SAMPLINGSPARAMETER SKICKAS, for det finns ingen att skicka. Se noten
    vid TEMPERATUR: varken temperature eller top_p star i API:ets kropp for den
    har modellgenerationen. Ett argument for det hade bara kunnat ge TypeError,
    och ett argument som alltid faller ar en falla, inte en mojlighet.
    """
    with client.messages.stream(**anropsparametrar(model, prompt, items)) as s:
        return s.get_final_message()

def anropsparametrar(model, prompt, items):
    """ANROPETS PARAMETRAR HAR ETT STALLE, och det ar inte stadning.

    Dygnet gar antingen genom Batch API (leveransvagen, se LEVERANS) eller
    genom ett direkt anrop. Byggde de var sin begaran skulle instrumentet med
    tiden bli tva: en modellparameter rattad pa ena stallet och glomd pa det
    andra ger tva olika laesningar av samma dygn, och ingenting i manifestet
    hade visat vilken som gallde. Samma skal som fick kallregistret att fa en
    enda definition efter FYND 004.

    Begaran ar identisk i bada vagarna. Det enda som skiljer ar leveransen:
    stroemmat svar nu, eller ett jobb som hamtas nar det ar klart."""
    return {
        "model": model, "max_tokens": 32000,
        "thinking": tankande_for(model),
        "output_config": {"effort": effort_for(model)},
        "system": [{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}},
                   {"type": "text", "text": OUTPUT_RULE, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": json.dumps(
            [{k: it[k] for k in ("observation_id", "tile_index", "observation_timestamp_utc",
                                 "neutral_source_claim", "review_region", "selection_layer",
                                 "source_tier", "representative_domain") if k in it} for it in items],
            ensure_ascii=False)}],
    }

# ================================ LEVERANS ================================
#
# BESLUTET FANNS, KODEN GJORDE DET INTE. Uppmatt 2026-11-07.
#
# Parameterregistret: "leverans | Batch API, 50 % av listpris | faststallt
# 2026-11-06". Projektbeskrivningen sager samma sak. Klassificeraren skickade
# anda vanliga anrop - service_tier "standard" i varje usage-rad i 2026/308
# och 2026/309 - och dygnet kostade dubbelt mot det beslutade.
#
# Det ar samma form som FYND 001-004: regeln star i ett dokument, aldrig i
# den kodvag som avgor. Den har gangen kostade den $7,50 per dygn, och den var
# direkt orsak till att takets slog i mitt i 2026/309.
#
# Darfor ar batchvagen nu standard och lever har, med tre egenskaper som
# daglig obevakad drift kraver:
#
#   JOBBET SKRIVS TILL DISK INNAN DET VANTAS PA. Ett jobb ar betalt i samma
#   stund det tas emot. Dor processen under vantan maste nasta korning HAMTA
#   det jobbet, inte skicka ett nytt - annars betalar ett schemalagt jobb
#   tva ganger for samma dygn och ingen ser det.
#
#   RONDER, INTE OMFORSOK I RAD. Ett batchjobb kommer tillbaka helt eller
#   delvis. De batchar som foll pa parsning eller validering skickas i en ny
#   rond, hogst MAX_TRIES ronder. Samma grindar som i direktvagen, samma kod.
#
#   DEN SOM INTE VILL VANTA SLAPPER. --slapp skickar jobbet, skriver
#   jobbfilen och gar ur. Nasta korning hamtar. Det ar den form schemalaggaren
#   behover: batchen far ta upp till 24 timmar utan att en process halls vid
#   liv under tiden.
LEVERANS = "batch"

def jobbfil(day):
    return passdir(day) / "batch_jobb.json"

def kund_id(p, n):
    return f"pass{p}_batch{n:02d}"

def tyd_kund_id(cid):
    m = re.fullmatch(r"pass(\d+)_batch(\d+)", cid)
    if not m:
        raise ValueError(f"okant custom_id i batchsvaret: {cid!r}")
    return int(m.group(1)), int(m.group(2))

def las_jobb(day):
    f = jobbfil(day)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

def rensa_jobb(day):
    f = jobbfil(day)
    if f.exists():
        f.unlink()

def skicka_jobb(client, model, prompt, day, todo):
    """Skickar ronden och skriver jobbfilen INNAN nagon vantan borjar."""
    begaran = [{"custom_id": kund_id(p, n),
                "params": anropsparametrar(model, prompt, items)}
               for p, n, items in todo]
    jobb = client.messages.batches.create(requests=begaran)
    write_text(jobbfil(day), json.dumps(
        {"id": jobb.id, "model": model, "prompt_sha256": sha(PROMPT_FILE),
         "skickat": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
         "begaran": [b["custom_id"] for b in begaran]}, ensure_ascii=False, indent=1))
    print(f"  batchjobb {jobb.id} skickat — {len(begaran)} begaran")
    print(f"    jobbfil: {jobbfil(day).name} (hamtas av nasta korning om denna avbryts)")
    return jobb.id

def vanta_pa_jobb(client, bid, pauser=(15, 30, 60), tak=24 * 3600):
    """Pollar till jobbet har slutat. Returnerar sista statusen."""
    t0, i, sist = time.time(), 0, None
    while True:
        jobb = client.messages.batches.retrieve(bid)
        c = jobb.request_counts
        nu = (c.succeeded, c.errored, c.processing, c.canceled, c.expired)
        if nu != sist:
            print(f"    {jobb.processing_status}: {c.succeeded} klara, {c.processing} kvar"
                  + (f", {c.errored} fel" if c.errored else "")
                  + (f", {c.expired} utgangna" if c.expired else ""))
            sist = nu
        if jobb.processing_status == "ended":
            return jobb
        if time.time() - t0 > tak:
            raise gates.GateFailure(
                f"batchjobb {bid} har inte slutat efter {tak // 3600} timmar — "
                "jobbfilen ligger kvar, kor steget igen for att hamta det")
        time.sleep(pauser[min(i, len(pauser) - 1)]); i += 1

def jobbets_svar(client, bid):
    """(pass, batch, meddelande, fel) per begaran. Fel ar None nar svaret kom."""
    for rad in client.messages.batches.results(bid):
        p, n = tyd_kund_id(rad.custom_id)
        typ = getattr(rad.result, "type", None)
        if typ == "succeeded":
            yield p, n, rad.result.message, None
        else:
            fel = getattr(rad.result, "error", None)
            yield p, n, None, f"{typ}: {getattr(fel, 'message', fel) or 'utan meddelande'}"

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

def parse(msg, inp=None):
    """Text till rader, plus antalet strukna emissionsartefakter.

    Ingen forlatande parsning: JSON-regeln ar oforandrad. Darefter tre steg som
    alla ar protokollets egna, fore validate():

    OVERSKOTT KASTAS OCH RAKNAS. UNDERSKOTT FALLER.

    Uppmatt 2026-11-05 pa 2026/308, fem fall over tva batchar och fyra forsok:
    modellen lagger till, den tar aldrig bort. Extranycklarna var "", Surprise2,
    Surprise_dup, Fear_dup och Fear_note - alltid ett riktigt kanslonamn plus
    ett suffix, och alltid med alla sexton riktiga nycklar pa plats. Extraraden
    hette OBS-...-DUP respektive OBS-..._DUP_GUARD och var tom: tom text, alla
    sexton poang noll, noten "placeholder". Observationen den hangdes pa hade
    ingen nara dubblett - hogsta jaccard i batchen var 0,06 - sa det ar ingen
    deduplicering utan en defensiv markering.

    Sakerheten ligger i villkoret: overskott kastas BARA nar ingenting saknas.
    Saknas en nyckel kan den extra vara en felstavning av den - "Joie" dar
    "Joy" saknas - och da faller batchen som forut. Samma for rader: saknas en
    observation, eller forekommer nagon tva ganger, faller batchen, for da gar
    det inte att veta vilken klassificering som galler.

    Det kastade bar ingen information protokollet kraver, och ingenting
    rekonstrueras eller gissas. Allt kastat raknas och gar till korjournalen
    som emission_artifacts - nycklar och rader i samma tal. Att dela upp dem
    vore battre for kalibreringsbatteriet och ar en kvarstaende forbattring.

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
        # Overskottsnycklar kastas bara nar alla sexton finns.
        if isinstance(s, dict) and V <= set(s):
            for k in [k for k in s if k not in V]:
                del s[k]
                artefakter += 1
        r["stated_primary"] = r.get("primary_emotion")
        r["stated_secondary"] = r.get("secondary_emotion")
        # Harled bara nar poangen gar att harleda ur. Ar de trasiga lamnas
        # falten som modellen gav dem och validate() rapporterar poangfelet.
        if (isinstance(s, dict) and set(s) == V
                and all(isinstance(v, (int, float)) for v in s.values())):
            r["primary_emotion"], r["secondary_emotion"] = derive(s)

    for r in rows:
        if isinstance(r, dict):
            r["stated_observation_id"] = r.get("observation_id")

    # Overskottsrader kastas bara nar varje begard observation finns exakt en
    # gang. Annars lamnas raderna ororda och validate() rapporterar bristen.
    if inp is not None:
        want = {i["observation_id"] for i in inp}
        ids = [r.get("observation_id") for r in rows if isinstance(r, dict)]
        if want <= set(ids) and all(ids.count(w) == 1 for w in want):
            behall = [r for r in rows if isinstance(r, dict)
                      and r.get("observation_id") in want]
            artefakter += len(rows) - len(behall)
            rows = behall
        else:
            rows = repair_id(rows, want)
    return rows, artefakter


def repair_id(rows, want):
    """Ett stympat observation_id aterstalls genom UTESLUTNING, aldrig gissning.

    Modellen stympar eller konfabulerar ibland ett observation_id: OBS-231 i
    stallet for OBS-F3239B4CC67CBB1E, eller ett fullangdigt men pahittat
    OBS-D8238B561030425F. Uppmatt i korningen av 2026/308: 11 av 18 misslyckade
    forsok, 61 procent, var id-fel. Orsaken ar strukturell - sexton slumpmassiga
    hextecken ar den enda delen av utdatan som bar noll information och noll
    redundans, sa det finns ingenting for modellen att upptacka felet mot.

    EN INNEHALLSKONTROLL PROVADES OCH FORKASTADES. Jaccard mellan indatans
    rubrik och modellens neutral_event_representation, matt pa 1750 verifierat
    korrekta rader: korrekta par gar ner till 0,000 och slumppar upp till 0,700,
    sa ingen troskel separerar dem. Aven radvis sekvenskontroll faller: lagsta
    kvot mellan ratt linje och basta felstallning var 1,0x, och ett simulerat
    radbortfall kunde ge HOGRE poang an originalet. En sadan grind hade sett ut
    som en kontroll utan att vara en.

    Uteslutning kraver ingen troskel och inget antagande om ordning. Saknas
    exakt ett begart id och finns exakt ett okant, ar de ovriga 49 exakt
    matchade - och da finns det bara en observation kvar som den okanda raden
    kan vara. Det ar logik, inte likhet.

    Strikt: ett enda id per batch. Tva eller fler okanda, en dubblett, eller
    fel radantal - ingenting rors, och validate() faller batchen som forut.
    Modellens egna varde star kvar som stated_observation_id, sa att andelen
    gar att mata over tid.
    """
    ids = [r.get("observation_id") for r in rows if isinstance(r, dict)]
    if len(ids) != len(want) or len(set(ids)) != len(ids):
        return rows
    saknas = sorted(want - set(ids))
    over = [r for r in rows if isinstance(r, dict) and r.get("observation_id") not in want]
    if len(saknas) != 1 or len(over) != 1:
        return rows
    over[0]["observation_id"] = saknas[0]
    return rows

JOURNAL_FALT = ("model", "prompt_sha256", "spec_sha256")

def journalfil(day):
    return sp.outdir(DATA, day) / f"600_STATES_{sp.state_key(day)}_CLASSIFIER_RUN.json"

def las_journal(day, rec):
    """Dygnets befintliga journal, och grinden mot instrumentbyte.

    Ett dygns trettio anrop tas i flera omgangar. Ar modell, prompt eller spec
    en annan an i de tidigare omgangarna ar det ett annat instrument mitt i ett
    dygn, och dygnet kan inte bli ett verk. Grinden star fore anropen: upptacks
    bytet forst vid skrivningen ar pengarna redan utlagda."""
    fil = journalfil(day)
    if not fil.exists():
        return {}
    gammal = json.loads(fil.read_text(encoding="utf-8"))
    for f in JOURNAL_FALT:
        if f in gammal and gammal[f] != rec[f]:
            raise gates.GateFailure(
                f"{f} skiljer sig fran dygnets journal: {gammal[f]!r} tidigare, "
                f"{rec[f]!r} nu — ett annat instrument mitt i ett dygn")
    return gammal

def skriv_journal(day, gammal, rec, parse_fel):
    """Journalen vaxer, den skrivs inte over.

    Korjournalen ar manifestets proveniensansprak. Den far inte beskriva den
    sista omgangen av tre utan hela dygnets arbete, sa omgangens anrop laggs
    till de befintliga och totals raknas om over allt. Skrivningen gar genom
    atomic som alla manifestskrivningar.

    OCH DEN SAGER VAD DEN INTE TACKER. Passfilerna pa disk jamfors med
    journalens anrop, och de som saknas skrivs som unrecorded. En journal som
    tiger om sina luckor ar ett tyst osant pastaende - regeln star sedan
    FYND 001. Luckan uppstar nar en batch klassificerades utan att anropet hann
    skrivas, och usage gar inte att rekonstruera i efterhand. Listan raknas om
    vid varje skrivning, aldrig fran en tidigare journal: den ar en matning av
    disken, inte ett pastaende som arvs. En tom lista ar darfor ocksa ett
    besked - kontrollen gjordes."""
    if not rec["calls"] and not parse_fel:
        return
    c = gammal.get("calls", []) + rec["calls"]
    ut = {**gammal, **rec, "calls": c}
    ut["totals"] = {"calls": len(c),
                    "input": sum(x["input_tokens"] for x in c),
                    "output": sum(x["output_tokens"] for x in c),
                    "cache_read": sum(x["cache_read"] for x in c),
                    "parse_failures":
                        gammal.get("totals", {}).get("parse_failures", 0) + parse_fel}
    inspelade = {f"pass{x['pass']}_batch_{x['batch']:02d}" for x in c
                 if "pass" in x and "batch" in x}
    ut["unrecorded"] = sorted({f.stem for f in passdir(day).glob("pass*_batch_*.json")}
                              - inspelade)
    ut.pop("unrecorded_note", None)
    if ut["unrecorded"]:
        ut["unrecorded_note"] = ("klassificerad utan att anropet hann skrivas i "
                                 "journalen; usage gar inte att rekonstruera i efterhand")
        print(f"  NOTERA {len(ut['unrecorded'])} passfiler utanfor journalen, "
              f"forst {ut['unrecorded'][0]}")
    write_text(journalfil(day), json.dumps(ut, ensure_ascii=False, indent=1))
    print(f"\n  {ut['totals']}")

def gate_dygnet_ar_oppet(day, data=DATA):
    """EN DAG, EN KORNING, ETT UTFALL. Beslut 2026-11-06.

    Lasningen fore frysningen ar inte unik - uppmatt i FYND 006 byter atta
    rutor av femtio primartillstand nar samma modell laser om samma dygn. Det
    ar en egenskap hos instrumentet och den doljs inte.

    Men den egenskapen haller bara om korningen ar den FORSTA. Far man kora om
    tills bilden blir snygg finns det inget svar pa fragan "varfor just den har
    lasningen" - och da ar "irreversible" ett loftesord utan tackning.

    Darfor: nar emotionsmanifestet har sin sha256-sidecar ar dygnet stangt.
    Omkorning av en ENSKILD batch vid valideringsfel ar oforandrat tillaten -
    det ar att fullborda korningen, inte att gora om den, och passfiler som
    redan finns hoppas over. Det som avvisas ar en ny korning av ett dygn som
    redan blivit ett verk.

    INGEN FLAGGA OPPNAR DEN HAR GRINDEN. Att gora om ett dygn kraver att man
    med handen raderar sidecaren, vilket ar en synlig och avsiktlig handling.
    Ett schemalagt jobb gor det aldrig av misstag."""
    side = sp.sha_sidecar(sp.emotion_manifest(data, day))
    if side.exists():
        raise gates.GateFailure(
            f"{sp.state_id(day)} ar redan fryst ({side.name}) — en dag, en "
            "korning, ett utfall. Dygnet kan inte klassificeras om.")


def kor_i_batch(client, model, prompt, day, todo, d, rec, omgang, slapp=False):
    """Dygnet genom Batch API. Returnerar (antal parse-fel, utgangskod).

    RONDER, INTE OMFORSOK I RAD. Ett jobb kommer tillbaka helt eller delvis;
    de batchar som foll pa parsning eller validering gar in i en ny rond.
    Hogst MAX_TRIES ronder, samma tak som direktvagen har per batch.

    JOBBFILEN AR SKYDDET MOT DUBBEL BETALNING. Finns den vid start hamtas det
    jobbet i stallet for att ett nytt skickas. Den skrivs fore vantan och
    raderas forst nar svaren ar omhandertagna."""
    parse_fel_totalt = 0
    for rond in range(1, MAX_TRIES + 1):
        kvar = [t for t in todo if not (d / f"pass{t[0]}_batch_{t[1]:02d}.json").exists()]
        if not kvar:
            break
        jobb = las_jobb(day)
        if jobb is None:
            print(f"\n  rond {rond}: {len(kvar)} begaran")
            bid = skicka_jobb(client, model, prompt, day, kvar)
            if slapp:
                print("\n  --slapp: jobbet ligger kvar hos leverantoren. "
                      "Kor steget igen for att hamta det.")
                return parse_fel_totalt, 2
        else:
            bid = jobb["id"]
            print(f"\n  hamtar jobb {bid} fran {jobb.get('skickat', 'tidigare korning')}"
                  f" — {len(jobb.get('begaran', []))} begaran")
            if jobb.get("prompt_sha256") not in (None, sha(PROMPT_FILE)):
                raise gates.GateFailure(
                    f"jobbet {bid} skickades med en annan prompt an den som galler nu — "
                    "ett annat instrument mitt i ett dygn")
        vanta_pa_jobb(client, bid)
        for pnr, nnr, msg, felmeddelande in jobbets_svar(client, bid):
            if (d / f"pass{pnr}_batch_{nnr:02d}.json").exists():
                continue                      # redan omhandertagen i en tidigare rond
            items = dict((n, it) for n, it in batches(day)).get(nnr)
            if felmeddelande:
                print(f"  pass{pnr} batch{nnr:02d}: {felmeddelande}")
                continue
            try:
                rows, artefakter = parse(msg, items)
            except json.JSONDecodeError as e:
                parse_fel_totalt += 1
                print(f"  pass{pnr} batch{nnr:02d}: JSONDecodeError: {e}")
                spara_misslyckat(d, pnr, nnr, rond, msg)
                continue
            fel, dg = godkann(rows, items)
            if fel:
                print(f"  pass{pnr} batch{nnr:02d}: {len(fel)} valideringsfel pa "
                      f"{len(rows)} rader")
                spara_misslyckat(d, pnr, nnr, rond, msg, fel)
                continue
            skriv_svar(d, pnr, nnr, rows, dg, artefakter, msg, rec, omgang,
                       None, jobb=bid)
        rensa_jobb(day)
    annu_kvar = [t for t in todo if not (d / f"pass{t[0]}_batch_{t[1]:02d}.json").exists()]
    if annu_kvar:
        print(f"\n  {len(annu_kvar)} batchar kvar efter {MAX_TRIES} ronder")
    return parse_fel_totalt, 0

def kund_id_en(p, n, i):
    return f"pass{p}_batch{n:02d}_obs{i:02d}"

def tyd_kund_id_en(cid):
    m = re.fullmatch(r"pass(\d+)_batch(\d+)_obs(\d+)", cid)
    if not m:
        raise ValueError(f"okant custom_id: {cid!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def endir(d):
    k = d / "_en_i_taget"
    k.mkdir(parents=True, exist_ok=True)
    return k

def kor_i_batch_en(client, model, prompt, day, todo, d, rec, omgang, slapp=False):
    """EN OBSERVATION PER BEGARAN. Matvag, annu inte beslutad leveransform.

    Varfor den finns: observation_id glider ett steg i svansen av en batch om
    femtio (FYND 009), och felet gar inte att reparera - tva rader gor anspraak
    pa samma observation. Med en observation per begaran finns ingen rad att
    halka mellan. Identiteten kommer ur begaran, inte ur modellens avskrift.

    DEN FRYSTA PROMPTEN RORS INTE. Prompten sager "one object per supplied
    observation"; med en observation ar svaret en array om ett objekt, och
    kontraktet haller ordagrant. Det enda som avviker fran specen ar
    canonical_batch_size, och den avvikelsen noteras redan i utskriften.

    PASSFILEN BLIR IDENTISK I FORM. De femtio enskilda svaren sats ihop i
    indatans ordning och skrivs som en vanlig passfil, sa att konsensus, farg
    och revision inte ser nagon skillnad alls.

    VARJE SVAR LIGGER KVAR PA DISK. Ett jobb pa artonhundra begaran kan behova
    flera ronder, och ett svar som redan ar betalt far aldrig hamtas en gang
    till. Delresultaten ligger i _en_i_taget/ och ronden fragar bara efter det
    som saknas."""
    k = endir(d)
    parse_fel_totalt = 0

    def saknas():
        ut = []
        for p, n, items in todo:
            if (d / f"pass{p}_batch_{n:02d}.json").exists():
                continue
            for i, it in enumerate(items, start=1):
                if not (k / f"{kund_id_en(p, n, i)}.json").exists():
                    ut.append((p, n, i, it))
        return ut

    for rond in range(1, MAX_TRIES + 1):
        kvar = saknas()
        if not kvar:
            break
        jobb = las_jobb(day)
        if jobb is None:
            print(f"\n  rond {rond}: {len(kvar)} begaran, en observation i varje")
            begaran = [{"custom_id": kund_id_en(p, n, i),
                        "params": anropsparametrar(model, prompt, [it])}
                       for p, n, i, it in kvar]
            jobbet = client.messages.batches.create(requests=begaran)
            bid = jobbet.id
            write_text(jobbfil(day), json.dumps(
                {"id": bid, "model": model, "prompt_sha256": sha(PROMPT_FILE),
                 "skickat": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
                 "form": "en_i_taget",
                 "begaran": [b["custom_id"] for b in begaran]},
                ensure_ascii=False, indent=1))
            print(f"  batchjobb {bid} skickat — {len(begaran)} begaran")
            print(f"    jobbfil: {jobbfil(day).name}")
            if slapp:
                print("\n  --slapp: jobbet ligger kvar hos leverantoren. Kor steget igen"
                      " for att hamta det. Leverantorens fonster ar 24 timmar.")
                return parse_fel_totalt, 2
        else:
            bid = jobb["id"]
            print(f"\n  hamtar jobb {bid} fran {jobb.get('skickat', 'tidigare korning')}"
                  f" — {len(jobb.get('begaran', []))} begaran")
            if jobb.get("prompt_sha256") not in (None, sha(PROMPT_FILE)):
                raise gates.GateFailure(
                    f"jobbet {bid} skickades med en annan prompt an den som galler nu")
        jobbet = vanta_pa_jobb(client, bid)
        # Fordrojningen ar det andra matet: leverantorens fonster ar 24 timmar
        # och schemalaggningen ska tala det, inte den observerade minuten.
        if getattr(jobbet, "created_at", None) and getattr(jobbet, "ended_at", None):
            sek = (jobbet.ended_at - jobbet.created_at).total_seconds()
            print(f"    jobbets fordrojning: {sek/60:.1f} minuter")
            rec.setdefault("batch_latency_seconds", []).append(
                {"batch_id": bid, "requests": len(jobb["begaran"]) if jobb else len(kvar),
                 "seconds": round(sek, 1)})
        for cid, msg, felmeddelande in [(r.custom_id,
                                         getattr(r.result, "message", None),
                                         None if getattr(r.result, "type", None) == "succeeded"
                                         else getattr(r.result, "type", "okant"))
                                        for r in client.messages.batches.results(bid)]:
            p, n, i = tyd_kund_id_en(cid)
            if felmeddelande:
                print(f"  {cid}: {felmeddelande}")
                continue
            items = dict(batches(day))[n]
            it = items[i - 1]
            try:
                rows, artefakter = parse(msg, [it])
            except json.JSONDecodeError as e:
                parse_fel_totalt += 1
                print(f"  {cid}: JSONDecodeError: {e}")
                write_text(k / f"FAILED_{cid}.txt", raw_text(msg))
                continue
            fel, dg = godkann(rows, [it])
            if fel:
                print(f"  {cid}: {len(fel)} valideringsfel — {fel[0][:80]}")
                write_text(k / f"FAILED_{cid}.txt", raw_text(msg))
                continue
            u = msg.usage
            write_text(k / f"{cid}.json", json.dumps(
                {"row": rows[0], "artefakter": artefakter, "batch_id": bid,
                 "usage": {"input_tokens": u.input_tokens,
                           "output_tokens": u.output_tokens,
                           "cache_read": getattr(u, "cache_read_input_tokens", 0),
                           "cache_write": getattr(u, "cache_creation_input_tokens", 0)}},
                ensure_ascii=False, indent=1))
        rensa_jobb(day)
        # Satt ihop de batchar som blivit kompletta.
        for p, n, items in todo:
            fil = d / f"pass{p}_batch_{n:02d}.json"
            if fil.exists():
                continue
            delar = [k / f"{kund_id_en(p, n, i)}.json" for i in range(1, len(items) + 1)]
            if not all(x.exists() for x in delar):
                continue
            svar = [json.loads(x.read_text(encoding="utf-8")) for x in delar]
            rows = [x["row"] for x in svar]
            fel, dg = godkann(rows, items)
            if fel:
                print(f"  pass{p} batch{n:02d} foll vid hopsattningen: {fel[0][:90]}")
                continue
            write_text(fil, json.dumps(rows, ensure_ascii=False, indent=1))
            summa = {f: sum(x["usage"][f] for x in svar)
                     for f in ("input_tokens", "output_tokens", "cache_read", "cache_write")}
            rec["calls"].append({"run": omgang, "pass": p, "batch": n, "rows": len(rows),
                                 "seconds": None, "delivery": "batch_en_i_taget",
                                 "requests": len(svar),
                                 "batch_id": sorted({x["batch_id"] for x in svar}),
                                 "emission_artifacts": sum(x["artefakter"] for x in svar),
                                 "parse_failures": 0, **summa, **dg})
            print(f"  pass{p} batch{n:02d}  {len(rows)} rader ur {len(svar)} begaran  "
                  f"{dg['authored_scores_median']:.0f}/16 egna poang  "
                  f"cache {summa['cache_read']:,}")
    annu = saknas()
    if annu:
        print(f"\n  {len(annu)} enskilda begaran kvar efter {MAX_TRIES} ronder")
    return parse_fel_totalt, 0

def godkann(rows, items):
    """Valideringen och glesgrinden — ETT STALLE for bada leveransvagarna.

    Nollfyllningsdefekten passerar validering men ar det fel som
    ogiltigforklarade pilotserien: fjorton av sexton poang mekaniskt satta till
    noll. Specen kallar det en diagnostisk varning; i drift kor vi om batchen i
    stallet for att spara den.

    Lag den har kontrollen i bada vagarna var for sig vore den rattad pa ett
    stalle den dag den andras. Ett dygn kort genom batch och ett kort direkt
    ska vara samma instrument eller inget av dem."""
    fel = validate(rows, items)
    if fel:
        # Diagnostiken raknas inte pa ett svar som anda faller. Den raknade
        # tidigare alltid, och ett tomt svar fallde da hela korningen med
        # StatisticsError i stallet for att falla den batchen - ett fel i
        # instrumenteringen som hade sett ut som ett fel i dygnet.
        return fel, {}
    dg = diagnostics(rows)
    if dg["authored_scores_median"] <= 2:
        fel = [f"glest poangvektor, median {dg['authored_scores_median']:.0f}/16 "
               f"egna poang — protokollet har inte foljts"]
    return fel, dg

def skriv_svar(d, p, n, rows, dg, artefakter, msg, rec, omgang, sekunder,
               parse_fel=0, jobb=None):
    """Passfilen och journalraden — ETT STALLE for bada leveransvagarna."""
    usage = msg.usage
    write_text(d / f"pass{p}_batch_{n:02d}.json",
               json.dumps(rows, ensure_ascii=False, indent=1))
    rad = {"run": omgang, "pass": p, "batch": n, "rows": len(rows),
           "seconds": sekunder,
           "input_tokens": usage.input_tokens,
           "output_tokens": usage.output_tokens,
           "cache_read": getattr(usage, "cache_read_input_tokens", 0),
           "cache_write": getattr(usage, "cache_creation_input_tokens", 0),
           "block_types": block_types(msg),
           "emission_artifacts": artefakter,
           "parse_failures": parse_fel, **dg}
    if jobb:
        rad["delivery"] = "batch"
        rad["batch_id"] = jobb
    rec["calls"].append(rad)
    print(f"  pass{p} batch{n:02d}  {len(rows)} rader  "
          f"{dg['authored_scores_median']:.0f}/16 egna poang  "
          f"cache {getattr(usage,'cache_read_input_tokens',0):,}")
    print(f"    uttalat mot harlett: primary {dg['stated_primary_differs']}, "
          f"secondary {dg['stated_secondary_differs']}  "
          f"emissionsartefakter {artefakter}")

def kor_direkt(client, model, prompt, todo, d, rec, omgang, budget=None):
    """Dygnet genom direkta anrop. Returnerar (antal parse-fel, utgangskod).

    Fullt listpris. Leveransvagen ar Batch API sedan 2026-11-07; den har
    vagen finns kvar for en enskild batch man vill se svaret pa med en gang,
    och for den dag batchkon ligger nere."""
    import anthropic
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
                rows, artefakter = parse(msg, items)
                usage = msg.usage
            except (anthropic.APIError, json.JSONDecodeError) as e:
                if not ska_forsoka_igen(e):
                    print(f"  pass{p} batch{n:02d}: {type(e).__name__}: {e}")
                    print("  INGET OMFORSOK — felet uppstod innan begaran accepterades")
                    spara_misslyckat(d, p, n, attempt, msg)
                    raise
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
            fel, dg = godkann(rows, items)
            if fel:
                print(f"  pass{p} batch{n:02d} forsok {attempt}: {len(fel)} valideringsfel "
                      f"pa {len(rows)} rader")
                spara_misslyckat(d, p, n, attempt, msg, fel)
                if attempt == MAX_TRIES:
                    print("  GER UPP pa denna batch"); break
                continue
            skriv_svar(d, p, n, rows, dg, artefakter, msg, rec, omgang,
                       round(time.time() - t0, 1), parse_fel)
            break
        gjorda += 1
    gjorda += 1
    return parse_fel_totalt, 0

def run(day, only_pass=None, budget=None, model=DEFAULT_MODEL, dry=False,
        leverans=None, slapp=False, en_i_taget=False):
    sp.state_id(day)
    print(f"=== {sp.state_id(day)} — klassificering ===")
    gate_dygnet_ar_oppet(day)
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
        if en_i_taget:
            # En torrkorning som rapporterar fel antal begaran ar varre an
            # ingen: siffrorna harifran citeras i beslutsunderlag.
            n_beg = sum(len(items) for _, _, items in todo)
            print(f"  EN I TAGET: {n_beg:,} begaran, en observation i varje")
            print(f"  prefixet lases da {n_beg:,} ganger i stallet for {len(todo)} —"
                  f" det ar hela kostnadsfragan")
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
    # temperature star som null med en not, inte utelamnad. Korjournalen ar
    # manifestets proveniensansprak; en samplingsparameter som ingen ager far
    # inte saknas i den - en okand parameter ska sta som okand. Vardet satts
    # forst nar kalibreringsbatteriet matt vad det gor med utfallet.
    rec = {"state_id": sp.state_id(day), "model": model,
           "thinking": tankande_for(model),
           "effort": effort_for(model),
           "effort_note": "utskriven; lika modellens API-standardvarde 2026-11-06",
           "temperature": TEMPERATUR,
           "temperature_note": TEMPERATUR_NOT,
           "prompt_sha256": sha(PROMPT_FILE), "spec_sha256": sha(SPEC_FILE),
           "batch_size": len(bs[0][1]), "calls": []}
    # Grinden gar fore anropen, inte efter: upptacks ett byte av instrument
    # forst vid skrivningen ar pengarna redan utlagda pa ett dygn som anda inte
    # kan bli ett verk.
    gammal = las_journal(day, rec)
    # En stampel per omgang. Ett dygns trettio anrop tas i flera omgangar, och
    # utan stampel gar det inte att se vilka anrop som hor ihop.
    omgang = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    gjorda = parse_fel_totalt = 0
    utgang = 0
    try:
        if en_i_taget:
            # Matvag, se FYND 009. Noteras i journalen sa att ett dygn kort sa
            # aldrig kan forvaxlas med ett kort pa den beslutade formen.
            rec["delivery_form"] = "en_observation_per_begaran"
            rec["delivery_form_note"] = (
                "matvag 2026-11-09, ej beslutad leveransform. Frysta prompten och "
                "specen oforandrade; avvikelsen galler canonical_batch_size. Se FYND 009")
            parse_fel_totalt, utgang = kor_i_batch_en(
                client, model, prompt, day, todo, d, rec, omgang, slapp)
        elif (leverans or LEVERANS) == "batch":
            parse_fel_totalt, utgang = kor_i_batch(
                client, model, prompt, day, todo, d, rec, omgang, slapp)
            if utgang:
                return utgang
        else:
            parse_fel_totalt, utgang = kor_direkt(
                client, model, prompt, todo, d, rec, omgang, budget)
            if utgang:
                return utgang
    finally:
        # Journalen skrivs pa VARJE utgang: budgettaket, ett grindfel, ett
        # avbrott mitt i, normal avslutning. Samma regel som instrumenteringen
        # i ovrigt - ett anrop som gjorts ska lamna spar, oavsett hur korningen
        # slutar. Forut lag skrivningen efter loopen, och --budget (normallaget
        # for en resumerbar korning) returnerade fore den: tokenrakningen for
        # ett betalt anrop fanns da ingenstans.
        skriv_journal(day, gammal, rec, parse_fel_totalt)

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
                     "--dry-run" in a,
                     "direkt" if "--live" in a else None,
                     "--slapp" in a,
                     "--en-i-taget" in a))
    except gates.GateFailure as e:
        print(f"\nKEDJAN STOPPAD: {e}"); sys.exit(1)

if __name__ == "__main__":
    main()
