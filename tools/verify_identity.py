"""Verifiera oberoende att evidence_row_sha256 i frysta manifest kan reproduceras.
Ingen ny standard uppfinns - vi provar dokumenterade kanoniseringar och rapporterar."""
import csv, json, hashlib, sys, itertools

FIELD = "evidence_row_sha256"

def variants(row):
    d = {k: v for k, v in row.items() if k != FIELD}
    out = {}
    # A: tomma varden -> None, sorterade nycklar, kompakt
    a = {k: (None if v == "" else v) for k, v in d.items()}
    out["A none/compact/sorted"] = json.dumps(a, sort_keys=True, separators=(",", ":"))
    # B: som A men ensure_ascii=False
    out["B none/compact/sorted/utf8"] = json.dumps(a, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    # C: tomma varden kvar som ""
    out["C empty-str/compact/sorted"] = json.dumps(d, sort_keys=True, separators=(",", ":"))
    # D: som A men med mellanslag efter separatorer
    out["D none/spaced/sorted"] = json.dumps(a, sort_keys=True)
    # E: som A men osorterade (csv-ordning)
    out["E none/compact/csv-order"] = json.dumps(a, separators=(",", ":"))
    return out

def run(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    names = list(variants(rows[0]).keys())
    hits = dict.fromkeys(names, 0)
    for r in rows:
        exp = (r.get(FIELD) or "").lower()
        for name, payload in variants(r).items():
            if hashlib.sha256(payload.encode("utf-8")).hexdigest() == exp:
                hits[name] += 1
    n = len(rows)
    print(f"{path.split('/')[-1]}  ({n} rader)")
    for name in names:
        mark = "  <-- TRAFF" if hits[name] == n else ""
        print(f"   {name:32s} {hits[name]:4d}/{n}{mark}")
    return hits, n

if __name__ == "__main__":
    for p in sys.argv[1:]:
        run(p); print()
