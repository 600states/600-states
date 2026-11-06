"""Kalibreringsbatteriet kors mot en eller flera modeller och matningen skrivs.

Oppet beslut 8.1: ett modellbyte ska foregas av ett kalibreringsbatteri och
avvikelsen ska publiceras. Detta ar det verktyget.

SAMMA FRYSTA PROMPT till varje modell. Ingen modellspecifik prompt - behover en
modell en annan instruktion ar det en annan instrument, inte en annan modell.
Promptgrinden mot spechashen galler som i drift.

TRE PASS PER MODELL, som i drift. Instrumentet ar konsensus over tre oberoende
pass med median pa intensity och confidence; en modell som ar bra enskilt men
ostadig mellan pass beter sig annorlunda har.

GRIND OCH RAPPORT AR SKILDA SAKER.
  Grinden ar mekanisk efterlevnad och harleds UR SPECENS EGNA FALT, se
  grind_ur_spec(). Den tidigare texten har angav "median 13-15 av 16 egna
  poang". Den siffran kom ur en observation i handovern, inte ur specen, och
  uteslot modeller pa fel grund. Uppmatt pa referensmodellens egna 600 rader
  ar de atta lagsta poangen exakt 0.00 i 33.8% av fallen: bandet matte
  svansens granularitet, inte om modellen gor matningen. Borttaget 2026-11-06.
  Rapporten ar sjalvoverensstammelse over passen, deltaE mot referensen, och
  kostnad. deltaE RAPPORTERAS, det ar ALDRIG en grind: regel 0.1 forbjuder att
  ett matt pa den renderade bilden blir ett mal. Att valja modell efter vilken
  som ger vackrast farg vore brott mot den regeln.

SJALVOVERENSSTAMMELSE MATS PA TVA NIVAER, och skillnaden avgjorde modellvalet.
  Pa etiketten: andel observationer dar alla tre passen ger samma primary
  respektive secondary. 50 observationer ger standardfelet +/-0.059 vid p=0.78,
  sa tva modeller som skiljer nagra rader ar inte atskiljbara pa det mattet.
  Pa de 16 poangen: medelavvikelsen mellan passen per poang (MAD). 800 varden
  i stallet for 50 etiketter. Det ar dessutom den storhet fargmodellen laser -
  fargen kommer ur hela vektorn och intensity, inte ur etiketten.

Beslutsregeln ska sattas fore matningen, annars ar den efterhandsrationalisering:
modeller som faller pa grinden ar ute; bland dem som klarar den valjs den
billigaste vars sjalvoverensstammelse ligger inom referensens band.

    python3 tools/calibrate.py <modell>[,<modell>...] [--passes 3] [--dry-run]
"""
import json, statistics, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src")); sys.path.insert(0, str(HERE.parent))
import classify, consensus, color_protocol
from atomic import write_text
from config import REMEDIATION
from vocab import EMOTION_STATES

BATTERI  = REMEDIATION / "600_STATES_KALIBRERINGSBATTERI_v1.0.json"
REFERENS = REMEDIATION / "600_STATES_KALIBRERINGSBATTERI_v1.0_REFERENS.json"

# Listpris per miljon tokens, USD. Star har och inte i koden som kor, sa att en
# prisandring aldrig kan paverka ett verk - bara rapporten.
PRIS = {
    "claude-opus-5":     (5.00, 25.00),
    "claude-opus-5-5":   (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5":  (0.10,  0.50),
}

def _lab(hexf):
    """sRGB -> CIE L*a*b*, D65. Bara for rapporterad deltaE."""
    r, g, b = (int(hexf[i:i+2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = f(r), f(g), f(b)
    x = (0.4124*r + 0.3576*g + 0.1805*b) / 0.95047
    y = (0.2126*r + 0.7152*g + 0.0722*b) / 1.00000
    z = (0.0193*r + 0.1192*g + 0.9505*b) / 1.08883
    t = lambda v: v ** (1/3) if v > 0.008856 else (7.787 * v + 16/116)
    fx, fy, fz = t(x), t(y), t(z)
    return (116*fy - 16, 500*(fx - fy), 200*(fy - fz))

def deltaE(h1, h2):
    """CIE76. Rapporterat matt, aldrig en grind."""
    a, b = _lab(h1), _lab(h2)
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

def mad_over_passen(P, falt):
    """Medelavvikelsen mellan de tre passen, per poang och per skalarfalt.

    Sjalvoverensstammelse pa etiketten raknar 50 varden per modell och har
    standardfelet +/-0.059 vid n=50: den kan inte skilja tva narliggande
    modeller at. Det har mattet raknar 50*16 = 800 varden ur samma svar, utan
    ett enda extra anrop, och det mater den storhet fargmodellen faktiskt
    laser. "egna" utesluter poang som ar noll i alla tre passen, annars skulle
    en modell som nollar halva vektorn fa battre siffra for att den avstod.
    "nollflip" ar ett tillstand som fick poang i ett pass och nollades i ett
    annat - det ar inte en justering utan ett byte av lasning.
    """
    ids = sorted(set.intersection(*(set(p) for p in P)))
    if not ids or len(P) < 2:
        return {}
    def spridning(v):
        return sum(abs(a - b) for i, a in enumerate(v) for b in v[i+1:]) / (len(v)*(len(v)-1)/2)
    alla, egna, flip, ngz = [], [], 0, 0
    for o in ids:
        for e in EMOTION_STATES:
            v = [float(p[o]["scores"][e]) for p in P]
            d = spridning(v)
            alla.append(d)
            if any(x > 0 for x in v):
                ngz += 1; egna.append(d)
                if any(x == 0 for x in v): flip += 1
    ut = {"mad_poang_alla": round(statistics.mean(alla), 4),
          "mad_poang_egna": round(statistics.mean(egna), 4),
          "nollflip_andel": round(flip / ngz, 4) if ngz else None}
    for f in falt:
        ut[f"mad_{f}"] = round(statistics.mean(
            [spridning([float(p[o][f]) for p in P]) for o in ids]), 4)
    return ut


def grind_ur_spec(P, spec, fel):
    """Grinden harleds ur specens egna falt, aldrig ur ett observerat snitt.

    DEN FORSTA VERSIONEN AV DEN HAR FUNKTIONEN VAR FEL, och felet ar vart att
    skriva ut. Den kravde 13-15 av 16 egenforfattade poang. Den siffran kom
    inte ur specen utan ur en observation i handovern om hur pilotens
    klassificerare betedde sig, och jag gjorde en beskrivning till en regel.

    Uppmatt 2026-11-06 pa referensmodellens 600 rader: de atta lagsta poangen i
    varje rad ar exakt 0.00 i 34 procent av fallen och har medianen 0.020.
    Referensmodellen nollar alltsa sjalv en tredjedel av svansen. Bandet 13-15
    matte darmed svansens granularitet, inte om modellen gor matningen - och
    uteslot claude-sonnet-5-5 pa fel grund.

    Specen gor foljande obligatoriskt, och det ar vad grinden provar:
      exact_16_score_keys_required
      all_scores_range_0_1
      score/intensity/confidence_precision
      mechanical_zero_fill_prohibited - specens eget skal beskriver fjorton av
        sexton mekaniskt satta till noll, alltsa tva kvar; mattet ar
        rows_with_two_or_fewer
      primary_must_rank_first / secondary_must_rank_second - harleds, alltid uppfyllt

    Specen sager uttryckligen att gleshet och numerisk upplosning ska
    RAPPORTERAS, inte falla en korning:
      two_sparse_batch_is_diagnostic_warning_not_automatic_semantic_failure
      batch_sparsity_and_numeric_resolution_must_be_reported
    De star darfor bland de rapporterade matten och inte i grinden.

    KVANTISERINGSFORBUDET SAKNADES I GRINDEN till 2026-11-06. Specen satter
    intensity_confidence_template_quantization_prohibited och prompten sager
    det i klartext: "Do not quantize intensity to a small preferred set of
    values" och samma mening for confidence. Ingenting provade det, sa regeln
    var ett onskemal. Se kvantiserad() for hur den provas utan trosklar."""
    skal = []
    if fel:
        skal.append(f"{len(fel)} valideringsfel, forst: {fel[0][:70]}")
    if spec.get("mechanical_zero_fill_prohibited"):
        glesa = sum(classify.diagnostics(list(p.values()))["rows_with_two_or_fewer"] for p in P)
        if glesa:
            skal.append(f"{glesa} rader med hogst tva egna poang "
                        f"(mechanical_zero_fill_prohibited)")
    if spec.get("intensity_confidence_template_quantization_prohibited"):
        for f in ("intensity", "confidence"):
            k = kvantiserad([float(r[f]) for pa in P for r in pa.values()],
                            classify.spec_precision())
            if k:
                skal.append(f"{f} {k} "
                            f"(intensity_confidence_template_quantization_prohibited)")
    return (not skal), (skal or ["uppfyller specens obligatoriska falt"])


def kvantiserad(varden, precision):
    """Har modellen anvant den upplosning specen ger den? Ja eller nej.

    INGEN TROSKEL, och det ar hela poangen. Forra gangen jag byggde en grind
    har satte jag ett band ur en observation och uteslot en modell pa fel
    grund. Det har mattet har ingen siffra att valja.

    Specen ger tva decimaler, alltsa 101 varden i [0,1]. Ett varde ligger pa
    ett grovre rutnat om det ar en multipel av ett storre steg. Fragan grinden
    staller ar inte "hur manga" utan "nagot alls": anvander modellen den givna
    upplosningen overhuvudtaget, eller ligger VARTENDA varde pa ett grovre
    rutnat? Det forsta ar efterlevnad, det andra ar en preferensmangd.

    Uppmatt 2026-11-06, 150 varden per modell och falt:
      opus-5      intensity 13% pa 0,05-rutnatet, confidence 20%
      sonnet-5-5  intensity 51%, confidence 30%
      haiku-5-5   intensity 100%, confidence 100% - sju olika varden pa 150
                  rader: 0.55 0.60 0.70 0.75 0.80 0.85 0.90
    Slumpen ger omkring 21% vid tva decimaler. 150 av 150 ar inte slump.

    Grinden tar bara det fullstandiga fallet. En modell som ligger pa rutnatet
    i 95 procent av fallen slipper igenom, och det ar en kand begransning:
    mattet skiljer efterlevnad fran total mall, inte goda vanor fran daliga."""
    if len(varden) < 20:
        return None
    steg = 10 ** -precision
    for grovre in (5, 10, 25, 50):        # 0,05  0,10  0,25  0,50 vid tva decimaler
        if all(round(v / steg) % grovre == 0 for v in varden):
            n = len({round(v, precision) for v in varden})
            return (f"ligger till 100% pa {grovre * steg:g}-rutnatet, "
                    f"{n} olika varden pa {len(varden)} rader")
    return None

def kor(modeller, passes=3, dry=False):
    prompt, spec = classify.gate_instrument()
    bat = json.loads(BATTERI.read_text(encoding="utf-8"))
    ref = json.loads(REFERENS.read_text(encoding="utf-8"))
    obs = bat["observationer"]
    refrad = {r["observation_id"]: r for r in ref["rader"]}
    inp = {o["observation_id"]: o for o in obs}
    print(f"=== kalibrering · batteri {len(obs)} observationer ur {bat['meta']['kalla_dygn']} ===")
    print(f"    referensmodell {bat['meta']['referensmodell']}")

    if dry:
        tkn = len(json.dumps(obs)) // 4
        print(f"\n  TORRKORNING — inget anrop gors")
        for m in modeller:
            i, u = PRIS.get(m, (0, 0))
            kost = passes * ((tkn + len(prompt)//4) * i + 50 * 320 * u) / 1e6
            print(f"    {m:<20} {passes} anrop, uppskattat ${kost:.2f}")
        return 0

    import anthropic, os
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: print("\n  ANTHROPIC_API_KEY saknas."); return 4
    client = anthropic.Anthropic(api_key=key)

    resultat = {}
    for m in modeller:
        print(f"\n--- {m} ---")
        P, usage, fel_tot, art_tot = [], [], [], 0
        for p in range(1, passes + 1):
            for forsok in range(1, classify.MAX_TRIES + 1):
                t0 = time.time()
                try:
                    msg = classify.call(client, m, prompt, obs)
                    rows, art = classify.parse(msg, obs)
                except Exception as e:
                    print(f"    pass{p} forsok {forsok}: {type(e).__name__}: {e}")
                    if not classify.ska_forsoka_igen(e):
                        print("      INGET OMFORSOK — felet uppstod innan begaran accepterades")
                        fel_tot.append(f"{type(e).__name__}: {e}")
                        break
                    continue
                fel = classify.validate(rows, obs)
                dg = classify.diagnostics(rows)
                if fel and forsok < classify.MAX_TRIES:
                    print(f"    pass{p} forsok {forsok}: {len(fel)} fel, forst: {fel[0][:70]}")
                    continue
                rap = REMEDIATION / "kalibrering_rasvar"
                rap.mkdir(parents=True, exist_ok=True)
                write_text(rap / f"{m}_pass{p}.txt", classify.raw_text(msg))
                P.append({r["observation_id"]: r for r in rows})
                usage.append(classify.usage_fields(msg)); fel_tot += fel; art_tot += art
                print(f"    pass{p}  {len(rows)} rader  {dg['authored_scores_median']:.0f}/16 "
                      f"egna poang  id-rep {dg['stated_id_differs']}  {time.time()-t0:.0f}s")
                break
        if len(P) != passes:
            resultat[m] = {"grind": "FALLER", "skal": f"bara {len(P)} av {passes} pass",
                           "tankande": classify.tankande_for(m),
                           "forsta_felet": fel_tot[0] if fel_tot else None}
            print(f"    GRIND: FALLER — bara {len(P)} av {passes} pass"); continue

        kon = consensus.rows(P, inp)
        inn, ut = PRIS.get(m, (0, 0))
        kost = sum(u.get("input_tokens", 0) * inn + u.get("output_tokens", 0) * ut
                   for u in usage) / 1e6
        sjalv = {f: sum(1 for oid in P[0] if len({p[oid][f] for p in P}) == 1) / len(P[0])
                 for f in ("primary_emotion", "secondary_emotion")}
        dE = [deltaE(color_protocol.hex_of_row(r), color_protocol.hex_of_row(refrad[r["observation_id"]]))
              for r in kon if r["observation_id"] in refrad]
        pri_lika = sum(1 for r in kon if r["primary_emotion"] == refrad[r["observation_id"]]["primary_emotion"])
        med = [classify.diagnostics(list(p.values()))["authored_scores_median"] for p in P]
        grind, skal = grind_ur_spec(P, spec, fel_tot)
        resultat[m] = {
            "grind": "KLARAR" if grind else "FALLER",
            "grindens_skal": skal,
            "tankande": classify.tankande_for(m),
            "valideringsfel": len(fel_tot), "emissionsartefakter": art_tot,
            "egna_poang_median": med,
            "poang_over_0_05_median": [statistics.median(
                [sum(1 for v in r["scores"].values() if v >= 0.05) for r in p.values()])
                for p in P],
            "unika_intensity": [classify.diagnostics(list(p.values()))["unique_intensity"] for p in P],
            "unika_confidence": [classify.diagnostics(list(p.values()))["unique_confidence"] for p in P],
            "sjalvoverensstammelse": {k: round(v, 3) for k, v in sjalv.items()},
            "mad_over_passen": mad_over_passen(P, ("intensity", "confidence")),
            "primary_lika_referensen": f"{pri_lika}/{len(kon)}",
            "deltaE_mot_referensen": {"median": round(statistics.median(dE), 2),
                                      "p90": round(sorted(dE)[int(.9*(len(dE)-1))], 2),
                                      "max": round(max(dE), 2)},
            "kostnad_usd_batteriet": round(kost, 4),
            "kostnad_usd_per_verk": round(kost * (1800 / (len(obs) * passes)), 2),
        }
        r = resultat[m]
        print(f"    GRIND: {r['grind']}   sjalv-primary {sjalv['primary_emotion']:.1%}   "
              f"lika referensen {r['primary_lika_referensen']}   "
              f"MAD egna {r['mad_over_passen'].get('mad_poang_egna')}   "
              f"nollflip {r['mad_over_passen'].get('nollflip_andel')}   "
              f"deltaE median {r['deltaE_mot_referensen']['median']}   "
              f"${r['kostnad_usd_per_verk']}/verk")

    # EN KORNING FICK TIDIGARE RADERA EN ANNAN. Filnamnet bars av datumet och
    # skrevs med write_text, som ersatter. Korde man opus efter sonnet samma
    # dag fanns bara opus kvar, utan ett ord om att nagot forsvunnit. Matningen
    # for sonnet och haiku 2026-11-06 gick forlorad sa. Nu slas resultaten
    # samman, och bara nar det ar samma batteri: ett annat batteri ar en annan
    # matning och far inte blandas in i samma fil.
    ut = REMEDIATION / f"600_STATES_KALIBRERING_{time.strftime('%Y%m%d')}.json"
    bsha = classify.sha(BATTERI)
    samlat = dict(resultat)
    if ut.exists():
        gammalt = json.loads(ut.read_text(encoding="utf-8"))
        if gammalt.get("batteri_sha256") != bsha:
            ut = ut.with_name(ut.stem + f"_{bsha[:8]}.json")
            print(f"\n  tidigare fil galler ett annat batteri — skriver {ut.name}")
        elif gammalt.get("passes") != passes:
            ut = ut.with_name(ut.stem + f"_{passes}pass.json")
            print(f"\n  tidigare fil har annat antal pass — skriver {ut.name}")
        else:
            for m, r in gammalt.get("resultat", {}).items():
                if m not in samlat:
                    samlat[m] = r
    write_text(ut, json.dumps({"batteri_sha256": bsha,
                               "referensmodell": bat["meta"]["referensmodell"],
                               "passes": passes, "resultat": samlat},
                              ensure_ascii=False, indent=1))
    print(f"\n  {ut.name}  ({len(samlat)} modeller: {', '.join(sorted(samlat))})")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    a = sys.argv[2:]
    sys.exit(kor(sys.argv[1].split(","),
                 int(a[a.index("--passes") + 1]) if "--passes" in a else 3,
                 "--dry-run" in a))
