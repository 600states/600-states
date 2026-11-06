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
  Grinden ar mekanisk efterlevnad: kompletta rader, noll valideringsfel, noll
  rader med hogst tva egna poang, median 13-15 av 16. Antingen klarar modellen
  protokollet eller inte.
  Rapporten ar sjalvoverensstammelse over passen, deltaE mot referensen, och
  kostnad. deltaE RAPPORTERAS, det ar ALDRIG en grind: regel 0.1 forbjuder att
  ett matt pa den renderade bilden blir ett mal. Att valja modell efter vilken
  som ger vackrast farg vore brott mot den regeln.

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
        grind = (not fel_tot and min(med) >= 13 and max(med) <= 16
                 and all(classify.diagnostics(list(p.values()))["rows_with_two_or_fewer"] == 0 for p in P))
        resultat[m] = {
            "grind": "KLARAR" if grind else "FALLER",
            "tankande": classify.tankande_for(m),
            "valideringsfel": len(fel_tot), "emissionsartefakter": art_tot,
            "egna_poang_median": med,
            "sjalvoverensstammelse": {k: round(v, 3) for k, v in sjalv.items()},
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
              f"deltaE median {r['deltaE_mot_referensen']['median']}   "
              f"${r['kostnad_usd_per_verk']}/verk")

    ut = REMEDIATION / f"600_STATES_KALIBRERING_{time.strftime('%Y%m%d')}.json"
    write_text(ut, json.dumps({"batteri_sha256": classify.sha(BATTERI),
                               "referensmodell": bat["meta"]["referensmodell"],
                               "passes": passes, "resultat": resultat},
                              ensure_ascii=False, indent=1))
    print(f"\n  {ut.name}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    a = sys.argv[2:]
    sys.exit(kor(sys.argv[1].split(","),
                 int(a[a.index("--passes") + 1]) if "--passes" in a else 3,
                 "--dry-run" in a))
