"""Bygger sajtens datafil for ett State ur manifesten. Ingen tolkning, bara join.

Kors som sista steg i kedjan sa att den publika vyn aldrig kan visa en annan
uppsattning rutor an manifestet. audit_state.py kontrollerar likheten.
"""
import collections, csv, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
from atomic import write_text
from config import DATA

MONTHS = ["JANUARY","FEBRUARY","MARCH","APRIL","MAY","JUNE","JULY",
          "AUGUST","SEPTEMBER","OCTOBER","NOVEMBER","DECEMBER"]
SRC = {"LIVE_FETCH": "P", "ARCHIVE_SNAPSHOT": "A", "URL_SLUG": "S", "PAGE_TITLE_UNVERIFIED": "U"}

def build(day, data=DATA):
    D = sp.outdir(data, day)
    pre = {int(r["tile_index"]): r for r in csv.DictReader(
        open(sp.pre_manifest(data, day), encoding="utf-8"))}
    emo = list(csv.DictReader(open(sp.color_manifest(data, day), encoding="utf-8")))
    inp = {}
    for f in sorted(sp.classifier_input(data, day).glob("batch_*.json")):
        for it in json.loads(f.read_text(encoding="utf-8")): inp[it["tile_index"]] = it

    tiles = []
    for r in sorted(emo, key=lambda r: int(r["tile_index"])):
        i = int(r["tile_index"]); p = pre[i]; q = inp[i]; ts = p["first_mention_utc"]
        tiles.append({"i": i, "h": r["hex"], "e": r["primary_emotion"], "s": r["secondary_emotion"],
                      "in": float(r["intensity"]), "cf": float(r["confidence"]),
                      "a": r["primary_agreement"], "sc": q["neutral_source_claim"],
                      "cn": r["classification_note"], "r": p["review_region"],
                      "l": p["selection_layer"], "d": p["representative_domain"],
                      "u": p["representative_url"], "t": f"{ts[8:10]}:{ts[10:12]}",
                      "o": r["observation_id"], "cs": SRC.get(r["claim_source"], "S")})

    ag = collections.Counter(r["primary_agreement"] for r in emo)
    cs = collections.Counter(r["claim_source"] for r in emo)
    # day ar redan dygnet (AAAAMMDD) och ska inte skrivas over. Raden satte
    # tidigare day till forsta radens first_mention_utc, 14 tecken, vilket fick
    # statepaths att kasta ValueError och steget site att aldrig kunna avslutas.
    sha = lambda f: hashlib.sha256((D / f).read_bytes()).hexdigest()
    nd = sp.near_duplicate(data, day).name
    meta = {"id": sp.state_id(day).replace("/", " / "),
            "date": f"{int(day[6:8])} {MONTHS[int(day[4:6])-1]} {day[:4]}",
            "agree3": ag["3/3"], "agree2": ag["2/3"], "agree1": ag["1/3"],
            "colours": len({r["hex"] for r in emo}),
            "pub": cs["LIVE_FETCH"], "arch": cs["ARCHIVE_SNAPSHOT"],
            "slug": cs["URL_SLUG"], "unver": cs["PAGE_TITLE_UNVERIFIED"],
            "pubs": len({p["representative_domain"] for p in pre.values()}),
            "preHash": sha(sp.pre_manifest(data, day).name),
            "emoHash": sha(sp.color_manifest(data, day).name),
            "ndRows": sum(1 for _ in open(D / nd, encoding="utf-8")) - 1, "ndHash": sha(nd)}
    out = write_text(sp.site_json(data, day),
                     json.dumps({"meta": meta, "tiles": tiles}, ensure_ascii=False,
                                separators=(",", ":")))
    return out, meta

if __name__ == "__main__":
    for s in sys.argv[1:]:
        out, m = build(s)
        print(f"{out.name}: {m['agree3']} 3/3 · {m['colours']} unika farger · {m['pubs']} publicister")
