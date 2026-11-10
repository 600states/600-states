"""Bygger ett nytt referensmanifest for kalibreringsbatteriet.

    python3 tools/bygg_referens.py [--dry-run]

VARFOR DET BEHOVS. Batteriet mater en kandidatmodell mot en referens: hur manga
primartillstand som stammer, och hur langt fargen hamnar (deltaE). Referensen
ar inte sanningen - den ar en fast punkt. Men en fast punkt byggd i en form
instrumentet inte langre anvander mater kandidaten mot nagot vi inte ar.

Den 2026-11-10 beslutades en observation per begaran (FYND 009 och 010).
Referens v1.0 ar konsensus ur 2026/308, kord med femtio observationer i samma
anrop. Darfor byggs en ny.

TRE SAKER SOM GOR DEN HAR VERSIONEN HEDERLIG:

  REFERENSEN AR INTE MATKORNINGEN. Kalibreringskorningen 2026-11-10 jamfordes
  mot v1.0 och den jamforelsen ar publicerad. Byggde vi referensen ur samma
  svar skulle den korningen fa 50/50 mot sig sjalv, och en rad i
  jamforelsetabellen vore samtidigt tabellens nollpunkt. Darfor kors tre nya
  pass. Det kostar under en dollar.

  DEN GAMLA SKRIVS INTE OVER. v1.0 ligger kvar med sin hash. Matningar gjorda
  mot den ar fortfarande lasbara, och varje resultatrad bar hadanefter vilken
  referens den matts mot - det gick inte att se forut.

  FORMEN STAR I META. En referens vars form inte framgar ar precis det problem
  det har programmet finns for att losa.
"""
import json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "src")); sys.path.insert(0, str(HERE.parent))
import classify, consensus
import calibrate
from atomic import write_text
from config import REMEDIATION

BATTERI = REMEDIATION / "600_STATES_KALIBRERINGSBATTERI_v1.0.json"
NY      = REMEDIATION / "600_STATES_KALIBRERINGSBATTERI_v1.0_REFERENS_v2.0.json"
GAMMAL  = REMEDIATION / "600_STATES_KALIBRERINGSBATTERI_v1.0_REFERENS.json"
MODELL  = "claude-opus-5"
PASS    = 3

def main():
    dry = "--dry-run" in sys.argv[1:]
    prompt, spec = classify.gate_instrument()
    bat = json.loads(BATTERI.read_text(encoding="utf-8"))
    obs = bat["observationer"]
    inp = {o["observation_id"]: o for o in obs}
    print(f"=== nytt referensmanifest · {len(obs)} observationer ur {bat['meta']['kalla_dygn']} ===")
    print(f"    modell {MODELL}, {PASS} pass, en observation per begaran")

    # En referens skrivs en gang. Finns den redan ar det inte den har korningens
    # sak att avgora om den ska ersattas - samma regel som for ett fryst dygn.
    if NY.exists():
        sys.exit(f"{NY.name} finns redan. En referens skrivs en gang; vill du "
                 f"bygga en ny, ge den ett eget versionsnummer.")

    if dry:
        n = PASS * len(obs)
        print(f"\n  TORRKORNING — inget anrop gors")
        print(f"  {n} begaran via Batch API, uppskattat $0.77")
        print(f"  skulle skriva {NY.name}")
        return 0

    import os, anthropic
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("\n  ANTHROPIC_API_KEY saknas."); return 4
    client = anthropic.Anthropic(api_key=key)
    stampel = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    P, usage, fel, art = calibrate.kor_en_i_taget(client, MODELL, prompt, obs, PASS, stampel)
    if len(P) != PASS:
        print(f"\n  bara {len(P)} av {PASS} pass kom hela. Ingen referens skrivs."); return 1

    kon = consensus.rows(P, inp)
    rader = [{k: r[k] for k in ("observation_id", "tile_index", "primary_emotion",
                                "secondary_emotion", "intensity", "confidence",
                                "primary_agreement")} for r in kon]
    # Samma faltuppsattning som v1.0. Fargen harleds ur primary, secondary,
    # intensity och confidence, sa referensen behover inte bara hela vektorn.

    enighet = {n: sum(1 for r in rader if r["primary_agreement"] == f"{n}/3") for n in (3, 2, 1)}
    meta = dict(bat["meta"])
    meta.update({
        "referens_version": "2.0",
        "ersatter": GAMMAL.name,
        "byggd": stampel,
        "form": "en observation per begaran, Batch API",
        "pass": PASS,
        "prompt_sha256": classify.sha(classify.PROMPT_FILE),
        "spec_sha256": classify.sha(classify.SPEC_FILE),
        "batteri_sha256": classify.sha(BATTERI),
        "rasvar": f"kalibrering_rasvar/{MODELL}_en_i_taget_{stampel}/",
        "enighet_3_2_1": enighet,
        "not": (bat["meta"].get("not", "") + " v2.0 ar byggd under formen en observation "
                "per begaran, beslutad 2026-11-10 (FYND 009 och 010). v1.0 ar byggd med "
                "femtio observationer i samma anrop och ligger kvar med sin hash; "
                "matningar gjorda mot den ar fortfarande lasbara. Referensen ar inte "
                "sanningen - den ar en fast punkt, och formen den byggdes i hor till "
                "punkten.").strip(),
    })
    write_text(NY, json.dumps({"meta": meta, "rader": rader}, ensure_ascii=False, indent=1))
    sha = classify.sha(NY)
    write_text(NY.with_suffix(".json.sha256"), f"{sha}  {NY.name}\n")
    print(f"\n  {NY.name}")
    print(f"    sha256 {sha[:16]}")
    print(f"    enighet 3/3: {enighet[3]}, 2/3: {enighet[2]}, 1/3: {enighet[1]}")
    print(f"    kastade emissionsartefakter: {art}, fallna begaran: {len(fel)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
