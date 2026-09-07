"""Lager 2a — kandidathamtning for materialitetsgrinden.

Hittar grupper som KAN vara samma informationstillstand. Tar inga beslut.
Enligt frozen Gate v1.0: likhet ar bara kandidathamtning, aldrig beslut.
"""
import re, collections

STOP = set("""a an and are as at be been but by for from has have he her his in is it its
la le of on or that the their they this to was were will with news international world
story html htm cms article articleshow live latest update updates video photos com www
say says said new after over into more than about against amid ahead
""".split())

def slug_tokens(url):
    """Innehallsord ur URL:ens sokvag."""
    path = re.sub(r"^https?://[^/]+", "", url or "")
    path = re.sub(r"[?#].*$", "", path)
    toks = [t for t in re.split(r"[^a-zA-Z0-9]+", path.lower()) if t]
    out = []
    for t in toks:
        if t.isdigit():            # datum- och artikel-id-segment
            continue
        if any(c.isdigit() for c in t) and len(t) > 6:
            continue
        if len(t) < 3 or t in STOP:
            continue
        out.append(t)
    return set(out)

class UnionFind:
    def __init__(self): self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[rb] = ra

def group(cands, jaccard=0.5, event_jaccard=0.25, min_shared_tokens=3):
    """Returnerar (grupper, ensamma) plus parlista med skal.

    Ett par kvalificerar om:
      A. lexikalisk Jaccard >= jaccard, ELLER
      B. delat GDELT-event-ID OCH Jaccard >= event_jaccard

    Delat event-ID rackER INTE ensamt. GDELT overmergear event (dokumenterat i
    PE-004), och transitiv sammanslagning pa enbart event-ID kedjar ihop helt
    orelaterade nyheter till jattekluster. Lexikaliskt stod kravs alltid.
    """
    for c in cands:
        c["_tok"] = slug_tokens(c["url"])
    by_url = {c["url"]: c for c in cands}

    shares_event = collections.defaultdict(set)
    by_event = collections.defaultdict(list)
    for c in cands:
        for e in c["event_ids"]:
            by_event[e].append(c["url"])
    for urls in by_event.values():
        if 1 < len(urls) <= 40:
            for i in range(len(urls)):
                for j in range(i + 1, len(urls)):
                    shares_event[urls[i]].add(urls[j])
                    shares_event[urls[j]].add(urls[i])

    cand_pairs = set()
    by_tok = collections.defaultdict(list)
    for c in cands:
        for t in c["_tok"]:
            by_tok[t].append(c["url"])
    for t, lst in by_tok.items():
        if len(lst) > 200:
            continue
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                cand_pairs.add((lst[i], lst[j]) if lst[i] < lst[j] else (lst[j], lst[i]))
    for u, others in shares_event.items():
        for v in others:
            cand_pairs.add((u, v) if u < v else (v, u))

    uf = UnionFind()
    for c in cands:
        uf.find(c["url"])
    pairs = []
    for u, v in cand_pairs:
        a, b = by_url[u], by_url[v]
        inter = a["_tok"] & b["_tok"]
        if len(inter) < min_shared_tokens:
            continue
        un = a["_tok"] | b["_tok"]
        jac = len(inter) / len(un) if un else 0.0
        ev = v in shares_event.get(u, ())
        if jac >= jaccard:
            reason = "LEXICAL"
        elif ev and jac >= event_jaccard:
            reason = "EVENT_ID+LEXICAL"
        else:
            continue
        pairs.append({"a": u, "b": v, "jaccard": round(jac, 3), "reason": reason})
        uf.union(u, v)

    groups = collections.defaultdict(list)
    for c in cands:
        groups[uf.find(c["url"])].append(c)
    multi = [g for g in groups.values() if len(g) > 1]
    single = [g[0] for g in groups.values() if len(g) == 1]
    return multi, single, pairs
