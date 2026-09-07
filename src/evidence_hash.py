"""Aterskapad kanonisering for evidence_row_sha256 (empiriskt verifierad).
SHA-256 av alla kolumner utom evidence_row_sha256, sammanfogade med '|' i CSV-kolumnordning."""
import csv, hashlib, sys
FIELD="evidence_row_sha256"

def row_hash(row, cols):
    return hashlib.sha256("|".join(str(row[c]) for c in cols).encode("utf-8")).hexdigest()

def check(path):
    rows=list(csv.DictReader(open(path,encoding="utf-8")))
    if not rows or FIELD not in rows[0]: return path,None,None
    cols=[c for c in rows[0].keys() if c!=FIELD]
    ok=sum(1 for r in rows if row_hash(r,cols)==r[FIELD].lower())
    return path, ok, len(rows)

if __name__=="__main__":
    for p in sys.argv[1:]:
        path,ok,n=check(p)
        name=path.split("/")[-1]
        if ok is None: print(f"{name[:70]:70s}  saknar {FIELD}")
        else: print(f"{name[:70]:70s}  {ok:4d}/{n}  {'OK' if ok==n else 'AVVIKER'}")
