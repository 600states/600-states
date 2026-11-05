"""Konsensus over tre oberoende klassificeringspass. Execution Spec v2.1.

Majoritet pa emotionstillstanden, median pa intensity och confidence, den
frysta vokabularordningen som skiljedomare.

FARGEN BERAKNAS INTE HAR. Denna fil importerar inte fargprotokollet och ska
aldrig gora det: emotionsmanifestet maste kunna frysas och hashas innan farg
existerar. Hex laggs pa av run_color.py, som ar ett separat program.

    python3 src/consensus.py 20261201 <katalog med pass{1,2,3}_*.json>
"""
import csv, hashlib, json, statistics, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
from atomic import atomic_write
from vocab import EMOTION_STATES, ORDER, arbitrate
from config import DATA

COLUMNS = ["tile_index", "observation_id", "neutral_event_representation",
           "primary_emotion", "secondary_emotion", "intensity", "confidence",
           "primary_agreement", "classification_note", "claim_source"]

def load_passes(passdir):
    P = []
    for n in (1, 2, 3):
        out = {}
        for f in sorted(Path(passdir).glob(f"pass{n}_*.json")):
            for r in json.loads(f.read_text(encoding="utf-8")):
                out[r["observation_id"]] = r
        P.append(out)
    return P

def load_inputs(d):
    inp = {}
    for f in sorted(Path(d).glob("batch_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            inp[r["observation_id"]] = r
    return inp

def rows(P, inp):
    """Ren funktion: tre passuppslag + inputs -> konsensusrader. Ingen IO."""
    ids = (set(P[0]) & set(P[1]) & set(P[2])) & set(inp)
    if len(ids) != len(inp):
        raise SystemExit(f"passen tacker inte alla observationer: input {len(inp)}, "
                         f"gemensamma {len(ids)}, pass {[len(p) for p in P]}")
    out = []
    for oid in sorted(ids, key=lambda o: inp[o]["tile_index"]):
        rs = [p[oid] for p in P]
        pri, n_pri = arbitrate([r["primary_emotion"] for r in rs])
        alt = [r["secondary_emotion"] for r in rs if r["secondary_emotion"] != pri]
        if alt:
            sec = arbitrate(alt)[0]
        else:
            med = {e: statistics.median([r["scores"][e] for r in rs]) for e in EMOTION_STATES}
            sec = sorted([e for e in EMOTION_STATES if e != pri], key=lambda e: (-med[e], ORDER[e]))[0]
        src = next(r for r in rs if r["primary_emotion"] == pri)
        out.append({
            "tile_index": inp[oid]["tile_index"], "observation_id": oid,
            "neutral_event_representation": src["neutral_event_representation"],
            "primary_emotion": pri, "secondary_emotion": sec,
            "intensity": f"{round(statistics.median([float(r['intensity']) for r in rs]), 2):.2f}",
            "confidence": f"{round(statistics.median([float(r['confidence']) for r in rs]), 2):.2f}",
            "primary_agreement": f"{n_pri}/3",
            "classification_note": src["classification_note"],
            "claim_source": inp[oid]["claim_source"]})
    return out

def build(day, passdir, data=DATA):
    rs = rows(load_passes(passdir), load_inputs(sp.classifier_input(data, day)))
    out = sp.emotion_manifest(data, day)
    with atomic_write(out) as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS); w.writeheader(); w.writerows(rs)
    # Frys manifestet. Fargen far inte roras forran detta ligger fast - sidecar
    # med SHA256 ar det run_color.py kontrollerar innan den slapper fram hex.
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    with atomic_write(sp.sha_sidecar(out)) as fh:
        fh.write(f"{digest}  {out.name}\n")
    agree = Counter(r["primary_agreement"] for r in rs)
    print(f"{sp.state_id(day)}: {len(rs)} rader · agreement {dict(agree)} · sha256 {digest[:16]}")
    return out

if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2]))
