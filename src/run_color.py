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
    site    publika vyns datafil         grind: forankrad tidsstampel

Stampelgrinden sitter pa site och ingen annanstans. Ett fryst manifest vars
.ots annu inte forankrats publiceras inte, men det produceras: frysning, farg
och rendering ror inte stampeln. Steget tas om med --stage site nar
forankringen gatt igenom - se src/stamp.py.
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

def step_color(day, data=DATA):
    print("\n[color]")
    emo = gates.gate_frozen_emotion(day, data)
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
    """Verket renderas och FAR SIN EGEN SIDECAR.

    Manifestet ar hashat, stamplat och signerat. Bilden - som ar Proof of
    State - hade ingen publicerad hash alls: fargsteget skriver en sidecar
    bredvid sitt manifest, renderingssteget skrev ingen bredvid sin PNG.
    Hashen rakandes redan har, men bara for att skrivas ut i loggen och
    glommas. A43.

    SAMMA FORM SOM FARGSTEGETS, ordagrant: digest, tva blanksteg, filnamn,
    radslut. En granskare som kan prova det ena ska inte behova lara sig
    ett andra format for det andra.

    SIGNATURENS OMFANG UTVIDGAS INTE. Bilden ar harledbar ur manifestet,
    sa dess integritet foljer redan av manifestets; sidecaren gor den
    kontrollerbar utan att harleda om. Vad signaturen ska tacka ar en
    annan och storre fraga.
    """
    print("\n[render]")
    from render import render_state
    png = render_state(day, data)
    digest = _sha(png)
    with atomic_write(sp.sha_sidecar(png)) as fh:
        fh.write(f"{digest}  {png.name}\n")
    print(f"        {png.name}  sha256 {digest[:16]}")
    print(f"        {sp.sha_sidecar(png).name}")
    return png

def step_site(day, data=DATA):
    """Publiceringssteget: den publika vyns datafil. HAR SITTER BEVISGRINDARNA.

    Inte pa frysningen. Fyra externa kalendrar som inte svarar 00:06 far inte
    kosta ett annars felfritt dygn - ett dygn gar inte att gora om. Har kostar
    samma avbrott en fordrojning: dygnet ar fryst, fargat och renderat, och
    steget tas om med --stage site nar forankringen gatt igenom.

    TVA GRINDAR, TVA OBEROENDE BEVIS. Stampeln binder manifestets hash till ett
    Bitcoin-block, signaturen binder den till upphovsidentiteten. Det ena sager
    nar, det andra vem, och dygnet publiceras forst nar bada sager det.

    Bada laser en JSON-fil ur arkivet och ror inget nat. Stamplingen ligger i
    src/stamp.py och signeringen i src/sign.py; bada kors i stampelcontainern,
    ingen av dem har.
    """
    print("\n[site]")
    import stamp
    import sign
    gates.gate_forankrad_stampel(sp.state_id(day), stamp.las_post(day, data))
    gates.gate_signerat_manifest(sp.state_id(day), sign.las_post(day, data))
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
