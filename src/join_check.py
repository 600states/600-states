"""Kontroll: gar varje vald observation i ett fryst manifest att aterfinna i raflodet?
Detta ar forutsattningen for att urvalet overhuvudtaget ska kunna reproduceras."""
import csv, sys, collections
sys.path.insert(0, "06_PIPELINE/src")
from gdelt import load_day

manifest_path, raw_zip = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(manifest_path, encoding="utf-8")))
_, by_url = load_day(raw_zip)

found = miss = 0
time_ok = time_bad = 0
missing_examples = []
for r in rows:
    url = r["representative_url"]
    hits = by_url.get(url)
    if not hits:
        miss += 1
        if len(missing_examples) < 5:
            missing_examples.append((r.get("tile_index"), r.get("representative_domain"), url[:95]))
        continue
    found += 1
    raw_times = {h["MentionTimeDate"] for h in hits}
    want = (r.get("observation_time_raw") or "").strip()
    if want and want in raw_times:
        time_ok += 1
    elif want:
        time_bad += 1

n = len(rows)
print(f"manifest: {manifest_path.split('/')[-1][:60]}")
print(f"  rader                        : {n}")
print(f"  URL aterfunnen i raflodet    : {found}/{n}  ({found/n*100:.1f}%)")
print(f"  URL saknas                   : {miss}")
print(f"  observation_time_raw matchar : {time_ok}   avviker: {time_bad}")
if missing_examples:
    print("  exempel pa saknade:")
    for t, d, u in missing_examples:
        print(f"    tile {t:>3}  {d:<28} {u}")
