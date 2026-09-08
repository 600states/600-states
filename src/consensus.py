"""Konsensus over tre oberoende klassificeringspass. Execution Spec v2.2.

Majoritet pa emotionstillstanden, median pa intensity och confidence, fixerad
vokabularordning som skiljedomare. Fargen raknas fram sist, ur den frusna
formeln, och ar aldrig en input till nagot beslut har.

    python3 src/consensus.py 001 <katalog med pass{1,2,3}_batch_*.json>
"""
import collections, csv, glob, json, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
from color_protocol import hex_of, VOCAB
from config import DATA

ORDER = {e: i for i, e in enumerate(VOCAB)}

def _load(d, n):
    out = {}
    for f in sorted(Path(d).glob(f"pass{n}_batch_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            out[r["observation_id"]] = r
    return out

def _vote(values):
    c = collections.Counter(values)
    top = max(c.values())
    return sorted([v for v, n in c.items() if n == top], key=lambda v: ORDER[v])[0], top

def build(state, passdir):
    P = [_load(passdir, i) for i in (1, 2, 3)]
    ids = set(P[0]) & set(P[1]) & set(P[2])
    if not (len(ids) == len(P[0]) == len(P[1]) == len(P[2])):
        sys.exit(f"passen tacker inte samma observationer: {[len(p) for p in P]}, gemensamma {len(ids)}")

    inp = {}
    for f in sorted((DATA / "08_V3_STATES" / f"STATE_{state}" / "classifier_input").glob("batch_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            inp[r["observation_id"]] = r

    rows, agree = [], collections.Counter()
    for oid in sorted(ids, key=lambda o: inp[o]["tile_index"]):
        rs = [p[oid] for p in P]
        pri, n_pri = _vote([r["primary_emotion"] for r in rs])
        alt = [r["secondary_emotion"] for r in rs if r["secondary_emotion"] != pri]
        if alt:
            sec = _vote(alt)[0]
        else:
            med = {e: statistics.median([r["scores"][e] for r in rs]) for e in VOCAB}
            sec = sorted([e for e in VOCAB if e != pri], key=lambda e: (-med[e], ORDER[e]))[0]
        inten = round(statistics.median([float(r["intensity"]) for r in rs]), 2)
        conf = round(statistics.median([float(r["confidence"]) for r in rs]), 2)
        src = next(r for r in rs if r["primary_emotion"] == pri)
        agree[f"{n_pri}/3"] += 1
        rows.append({"tile_index": inp[oid]["tile_index"], "observation_id": oid,
                     "neutral_event_representation": src["neutral_event_representation"],
                     "primary_emotion": pri, "secondary_emotion": sec,
                     "intensity": f"{inten:.2f}", "confidence": f"{conf:.2f}",
                     "hex": hex_of(pri, sec, inten, conf),
                     "primary_agreement": f"{n_pri}/3",
                     "classification_note": src["classification_note"],
                     "claim_source": inp[oid]["claim_source"]})

    out = DATA / "08_V3_STATES" / f"STATE_{state}" / f"600_STATES_2026_{state}_EMOTION_COLOR_MANIFEST_v3.1_CONSENSUS.csv"
    cols = list(rows[0])
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    sec_same = sum(1 for o in ids if len({p[o]["secondary_emotion"] for p in P}) == 1)
    print(f"rader {len(rows)} · agreement {dict(agree)} · secondary lika i alla tre {sec_same} · "
          f"unika farger {len({r['hex'] for r in rows})}")
    return out

if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2]))
