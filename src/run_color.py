"""Fargsidan av kedjan. SEPARAT PROGRAM.

    python3 src/run_color.py 20261201

Det har ar det enda programmet som nar fargprotokollet. Urvals- och
klassificeringsprogrammet (run_state.py) importerar det aldrig, och denna fil
importerar aldrig urval eller klassificering.

Separationen ar inte stadning, den ar funktionen: Observation Day Rule sager
att fargmodell v0.4 ar otillganglig tills 600-observationsmanifestet ar fryst.
En kedja som kan rakna fram farg i samma process som den valjer observationer
kan inte visa att den inte gjorde det.

Grinden: emotionsmanifestets SHA256 maste stamma mot sidecar-filen som
klassificeringen lade. Stammer den inte har manifestet andrats efter frysning
och korningen avbryts.

Steg:
    color   hex ur protokollet -> fargmanifest + sha256
    render  PNG ur fargmanifestet
    site    publika vyns datafil
"""
import csv, hashlib, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
import gates
from atomic import atomic_write
from config import DATA
from color_protocol import hex_of_row

STAGES = ["color", "render", "site"]

def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def gate_frozen_emotion(day, data=DATA):
    emo = sp.emotion_manifest(data, day)
    side = sp.sha_sidecar(emo)
    gates._say("emotionsmanifestet finns", emo.exists(), emo.name)
    gates._say("det ar fryst (sha256-sidecar finns)", side.exists(), side.name)
    want = side.read_text(encoding="utf-8").split()[0]
    got = _sha(emo)
    gates._say("manifestet ar orort sedan frysningen", want == got, f"{got[:16]} mot {want[:16]}")
    return emo

def step_color(day, data=DATA):
    print("\n[color]")
    emo = gate_frozen_emotion(day, data)
    rows = list(csv.DictReader(open(emo, encoding="utf-8")))
    for r in rows:
        r["hex"] = hex_of_row(r)
    out = sp.color_manifest(data, day)
    cols = list(rows[0])
    with atomic_write(out) as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    digest = _sha(out)
    with atomic_write(sp.sha_sidecar(out)) as fh:
        fh.write(f"{digest}  {out.name}\n")
    gates._say("alla rutor har farg", all(r["hex"] for r in rows), f"{len(rows)} rutor")
    print(f"        {out.name}  sha256 {digest[:16]}  ·  {len({r['hex'] for r in rows})} unika farger")
    return out

def step_render(day, data=DATA):
    print("\n[render]")
    from render import render_state
    png = render_state(day, data)
    print(f"        {png.name}  sha256 {_sha(png)[:16]}")
    return png

def step_site(day, data=DATA):
    print("\n[site]")
    from build_site import build
    out, meta = build(day, data)
    print(f"        {out.name}  ·  {meta['colours']} unika farger  ·  {meta['pubs']} publicister")
    return out

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    day = sys.argv[1]
    args = sys.argv[2:]
    start = args[args.index("--stage") + 1] if "--stage" in args else "color"
    todo = STAGES[STAGES.index(start):]
    print(f"=== {sp.state_id(day)} — fargsidan ===")
    try:
        if "color" in todo: step_color(day)
        if "render" in todo: step_render(day)
        if "site" in todo: step_site(day)
    except gates.GateFailure as e:
        print(f"\nKEDJAN STOPPAD: {e}"); sys.exit(1)
    print("\nKlart.")

if __name__ == "__main__":
    main()
