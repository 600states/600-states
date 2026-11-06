"""Kalibreringsbatteriet: samma sextio observationer, for alltid.

Oppet beslut 8.1 kraver ett batteri som kors fore varje modellbyte. Poangen ar
att det ar SAMMA observationer varje gang - annars gar en modell matt 2026 inte
att jamfora med en modell matt 2029. Ett batteri som byts mellan matningarna ar
ingen matning.

Batteriet stratifieras over alla sexton primartillstand ur ett dygn som redan
ar klassificerat av referensmodellen, sa att aven sallsynta tillstand provas.
2026/308 har alla sexton representerade, men Awe och Fatigue bara en gang var -
dygnets verklighet, inte ett fel, och det skrivs ut i fordelningsrapporten.

Batteriet fryses med sha256. Referensraderna - samma observationer som de
klassificerades av referensmodellen - skrivs bredvid, sa att en kandidat kan
jamforas utan ett enda nytt anrop till referensen.

    python3 tools/build_battery.py <AAAAMMDD> [--size 50]
"""
import csv, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src")); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
from atomic import write_text
from config import DATA, REMEDIATION
from vocab import EMOTION_STATES

BATTERI = REMEDIATION / "600_STATES_KALIBRERINGSBATTERI_v1.0.json"
REFERENS = REMEDIATION / "600_STATES_KALIBRERINGSBATTERI_v1.0_REFERENS.json"

def bygg(day, storlek=50):
    d = sp.outdir(DATA, day)
    kon = {r["observation_id"]: r for r in csv.DictReader(
        open(sp.emotion_manifest(DATA, day), encoding="utf-8"))}
    inp = {}
    for f in sorted(sp.classifier_input(DATA, day).glob("batch_*.json")):
        for it in json.loads(f.read_text(encoding="utf-8")):
            inp[it["observation_id"]] = it
    saknas = set(kon) - set(inp)
    if saknas:
        raise SystemExit(f"{len(saknas)} manifestrader saknar klassificerarinput")

    # Stratifierat: ga varvet runt de sexton tillstanden och ta en i taget, i
    # tile-ordning, tills storleken ar nadd. Sallsynta tillstand kommer med
    # forst; vanliga fyller ut. Deterministiskt - ingen slump, ingen seed.
    per = {e: [] for e in EMOTION_STATES}
    for oid, r in sorted(kon.items(), key=lambda kv: int(kv[1]["tile_index"])):
        per[r["primary_emotion"]].append(oid)
    valda, varv = [], 0
    while len(valda) < storlek:
        lade_till = False
        for e in EMOTION_STATES:
            if len(valda) >= storlek: break
            if varv < len(per[e]):
                valda.append(per[e][varv]); lade_till = True
        if not lade_till:
            raise SystemExit(f"slut pa observationer vid {len(valda)} av {storlek}")
        varv += 1

    valda.sort(key=lambda o: int(kon[o]["tile_index"]))
    batteri = [inp[o] for o in valda]
    referens = [{k: kon[o][k] for k in
                 ("observation_id", "tile_index", "primary_emotion", "secondary_emotion",
                  "intensity", "confidence", "primary_agreement")} for o in valda]

    meta = {"kalla_dygn": sp.state_id(day), "storlek": len(batteri),
            "referensmodell": "claude-opus-5",
            "fordelning": {e: sum(1 for o in valda if kon[o]["primary_emotion"] == e)
                           for e in EMOTION_STATES},
            "not": ("Samma observationer vid varje matning. Byts de gar matningar fran "
                    "olika ar inte att jamfora. Referensraderna ar referensmodellens "
                    "konsensus for exakt dessa rader.")}
    write_text(BATTERI, json.dumps({"meta": meta, "observationer": batteri},
                                   ensure_ascii=False, indent=1))
    write_text(REFERENS, json.dumps({"meta": meta, "rader": referens},
                                    ensure_ascii=False, indent=1))
    for f in (BATTERI, REFERENS):
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        write_text(f.with_suffix(f.suffix + ".sha256"), f"{h}  {f.name}\n")
        print(f"  {f.name}  sha256 {h[:16]}")
    print(f"\n  {len(batteri)} observationer ur {sp.state_id(day)}")
    tomma = [e for e, n in meta["fordelning"].items() if n == 0]
    for e in EMOTION_STATES:
        print(f"     {e:<14} {meta['fordelning'][e]:>3}")
    if tomma:
        print(f"\n  SAKNAS HELT: {tomma} — batteriet provar inte dessa tillstand")
    return meta

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    a = sys.argv[2:]
    bygg(sys.argv[1], int(a[a.index("--size") + 1]) if "--size" in a else 50)
