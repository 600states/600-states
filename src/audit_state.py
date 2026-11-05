"""Revision av ett fardigt State. Rapporterar, andrar ingenting.

Kontrollerar att lankar, ID:n, hashar och bevis hanger ihop mellan filerna -
det som en kopare eller en granskare ska kunna gora sjalv.
"""
import csv, hashlib, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
from config import DATA
from color_protocol import hex_of_row

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def audit(day, data=DATA):
    D = sp.outdir(data, day)
    pre = list(csv.DictReader(open(sp.pre_manifest(data, day), encoding="utf-8")))
    emo = list(csv.DictReader(open(sp.color_manifest(data, day), encoding="utf-8")))
    inp = {}
    for f in sorted(sp.classifier_input(data, day).glob("batch_*.json")):
        for it in json.loads(f.read_text(encoding="utf-8")): inp[it["observation_id"]] = it
    ev = {}
    p = DATA / "07_EVIDENCE" / "pool_titles.jsonl"
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line); ev[r["url"]] = r

    out = []
    def chk(name, ok, detail): out.append((ok, name, detail))

    chk("rader", len(pre) == 600 and len(emo) == 600, f"pre {len(pre)}, emotion {len(emo)}")
    chk("tile_index 1..600 utan lucka",
        sorted(int(r["tile_index"]) for r in pre) == list(range(1, 601)), "")
    chk("unika observation_id", len({r["observation_id"] for r in pre}) == 600, "")
    chk("unika url", len({r["representative_url"] for r in pre}) == 600, "")
    chk("ID-mangd pre = emotion",
        {r["observation_id"] for r in pre} == {r["observation_id"] for r in emo}, "")
    chk("ID-mangd pre = klassificerarens input",
        {r["observation_id"] for r in pre} == set(inp), f"input {len(inp)}")
    chk("tile_index matchar mellan filerna",
        all(int(a["tile_index"]) == int(b["tile_index"])
            for a, b in zip(sorted(pre, key=lambda r: int(r["tile_index"])),
                            sorted(emo, key=lambda r: int(r["tile_index"])))), "")

    bad = [r["tile_index"] for r in emo if hex_of_row(r).upper() != r["hex"].upper()]
    chk("hex reproduceras av protokollet", not bad, f"{600-len(bad)}/600")

    badu = [r["tile_index"] for r in pre if not re.match(r"^https?://[^\s]+\.[^\s]+", r["representative_url"])]
    chk("url ar valformade", not badu, f"{len(badu)} trasiga")

    dom = [r["tile_index"] for r in pre
           if r["representative_domain"].split(".")[0] not in r["representative_url"].lower()]
    chk("domankolumnen finns i url", not dom, f"{len(dom)} avvikande")

    have = sum(1 for r in pre if r["representative_url"] in ev)
    chk("varje url har en bevispost", have == 600, f"{have}/600")
    withhash = sum(1 for r in pre if ev.get(r["representative_url"], {}).get("content_sha256"))
    chk("bevispost med innehallshash", True, f"{withhash}/600 (ovriga ar 403/404/betalvagg)")

    from datetime import date
    dd = date(int(day[:4]), int(day[4:6]), int(day[6:8])).strftime("%Y%m%d")
    ts = [r["tile_index"] for r in pre if not r["first_mention_utc"].startswith(dd)]
    chk("alla tidsstamplar i ratt dygn", not ts, f"{len(ts)} utanfor")
    order = [r["first_mention_utc"] for r in sorted(pre, key=lambda r: int(r["tile_index"]))]
    chk("kronologisk ordning", order == sorted(order), "")

    caps = {}
    for r in pre: caps[r["representative_domain"]] = caps.get(r["representative_domain"], 0) + 1
    chk("publisher cap <= 10", max(caps.values()) <= 10, f"max {max(caps.values())}, {len(caps)} publicister")

    files = {
        "pre-emotion": sp.pre_manifest(data, day),
        "emotion+farg": sp.color_manifest(data, day),
        "near-duplicate": sp.near_duplicate(data, day),
        "PNG": sp.png(data, day),
    }
    site = json.loads(sp.site_json(data, day).read_text(encoding="utf-8"))
    m = site["meta"]
    chk("sajtens preHash = filen", m["preHash"] == sha(files["pre-emotion"]), "")
    chk("sajtens emoHash = filen", m["emoHash"] == sha(files["emotion+farg"]), "")
    chk("sajtens ndHash = filen", m["ndHash"] == sha(files["near-duplicate"]), "")
    chk("sajtens rutor = manifestet",
        [t["h"] for t in site["tiles"]] == [r["hex"] for r in sorted(emo, key=lambda r: int(r["tile_index"]))], "")
    chk("sajtens url = manifestet",
        [t["u"] for t in site["tiles"]] == [r["representative_url"] for r in sorted(pre, key=lambda r: int(r["tile_index"]))], "")

    print(f"\n=== STATE {sp.state_id(day)} ===")
    for ok, name, detail in out:
        print(("  OK   " if ok else "  FEL  ") + f"{name}" + (f": {detail}" if detail else ""))
    print("  hashar:")
    for k, f in files.items(): print(f"    {k:<15} {sha(f)}")
    return all(o for o, _, _ in out)

if __name__ == "__main__":
    ok = all([audit(s) for s in sys.argv[1:]])
    print("\nALLT STAMMER" if ok else "\nAVVIKELSER HITTADE")
    sys.exit(0 if ok else 1)
