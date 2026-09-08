"""Grindar. En regel som inte kan stoppa en korning ar inte en regel.

Varje grind mater manifestet eller kandidatlistan. Ingen grind tittar nagonsin
pa den renderade bilden - se parameterregistret avsnitt 0.
"""
import collections

class GateFailure(Exception):
    pass

def _say(name, ok, detail):
    print(("  OK   " if ok else "  STOPP") + f" {name}: {detail}")
    if not ok:
        raise GateFailure(f"{name}: {detail}")

def gate_candidates(cands, day):
    _say("kandidater finns", len(cands) > 0, f"{len(cands)} kandidater")
    bad = [c for c in cands if not c.get("mention_rows")]
    _say("alla har mention_rows", not bad, f"{len(bad)} utan")
    bad = [c for c in cands if not str(c.get("first_mention_utc", "")).startswith(day)]
    _say("alla ligger i dygnet", not bad, f"{len(bad)} utanfor {day}")

def gate_pool_evidence(pool, floor=0.60):
    have = sum(1 for c in pool if c.get("page_title"))
    frac = have / len(pool) if pool else 0
    _say("rubriker i poolen", frac >= floor,
         f"{have}/{len(pool)} = {frac:.1%} (golv {floor:.0%})")

def gate_selection(chosen, report, regions, per_region, cap):
    _say("exakt 600 rutor", len(chosen) == 600, f"{len(chosen)}")
    short = {r: n for r, n in report["regional_per_region"].items() if n < per_region}
    _say("regionkvoter uppfyllda", not short, short or f"alla >= {per_region}")
    _say("publisher cap hallen", report["max_per_publicist"] <= cap,
         f"max {report['max_per_publicist']} (tak {cap})")
    _say("unika observation_id", report["unika_observation_id"] == len(chosen),
         f"{report['unika_observation_id']}")
    _say("unika url", report["unika_urler"] == len(chosen), f"{report['unika_urler']}")

def gate_claims(items, is_readable, is_digest=None):
    """is_readable ar SAMMA funktion som urvalsfiltret anvander. Tva egna
    definitioner av "lasbar" var orsaken till att urvalet slappte igenom rader
    som inputbygget inte kunde lasa - se FYND 003."""
    empty = [i for i in items if not is_readable(str(i["neutral_source_claim"]))]
    dist = collections.Counter(i["claim_source"] for i in items)
    print("        claim_source:", dict(dist))
    _say("varje rad har lasbar text", not empty,
         f"{len(empty)} rader utan" + (f" (t.ex. ruta {empty[0]['tile_index']})" if empty else ""))
    if is_digest is not None:
        d = [i for i in items if is_digest(i["neutral_source_claim"])]
        _say("ingen sammanfattningsartikel", not d,
             f"{len(d)} rader" + (f" (t.ex. ruta {d[0]['tile_index']}: {d[0]['neutral_source_claim'][:50]})" if d else ""))

def gate_emotion(inputs, rows, vocab):
    ids_in = {i["observation_id"] for i in inputs}
    ids_out = {r["observation_id"] for r in rows}
    _say("ID-mangd in = ut", ids_in == ids_out,
         f"in {len(ids_in)}, ut {len(ids_out)}, diff {len(ids_in ^ ids_out)}")
    bad = [r for r in rows if r["primary_emotion"] not in vocab or r["secondary_emotion"] not in vocab]
    _say("etiketter i vokabularet", not bad, f"{len(bad)} utanfor")
    bad = [r for r in rows if r["primary_emotion"] == r["secondary_emotion"]]
    _say("primary != secondary", not bad, f"{len(bad)} lika")
    bad = [r for r in rows if not (0 <= float(r["intensity"]) <= 1 and 0 <= float(r["confidence"]) <= 1)]
    _say("intensity/confidence i [0,1]", not bad, f"{len(bad)} utanfor")
    n_i = len({r["intensity"] for r in rows}); n_c = len({r["confidence"] for r in rows})
    _say("varden ar inte konstanta", n_i > 5 and n_c > 5,
         f"{n_i} unika intensity, {n_c} unika confidence")

def gate_color(rows, hex_of_row):
    bad = [r for r in rows if hex_of_row(r).upper() != str(r["hex"]).upper()]
    _say("varje hex reproduceras av protokollet", not bad,
         f"{len(rows)-len(bad)}/{len(rows)}" + (f", forsta fel ruta {bad[0]['tile_index']}" if bad else ""))
