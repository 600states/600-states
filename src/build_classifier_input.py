"""Bygger klassificerarens input for en State. Deterministisk, testbar, versionerad.

Ordning i kedjan: urval -> BEVISFANGST -> denna fil -> klassificering -> farg.
Bevisfangsten producerar rubriken; darfor maste den ligga fore.

neutral_source_claim = publicistens satta rubrik (page_title) nar den finns,
annars ord ur artikelns webbadress. Vilket det blev skrivs ut i claim_source,
sa att den publika vyn kan saga det rakt ut.

Ingen modell ar inblandad i detta steg.
"""
import csv, html, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA

SEP = re.compile(r"\s+[|–—·•«»>-]\s+")
STOP = {"html", "htm", "index", "story", "article", "news", "amp", "cms", "ece"}

def _squash(x):
    return re.sub(r"[^a-z0-9]", "", x.lower())

def _brandish(seg, domain):
    """Sant om segmentet ar publicistens namn snarare an nyhetstext.

    Domanens registrerade etikett (newsday av newsday.co.tt) jamfors mot hela
    segmentet pa hopslagen form, med ledande "the" borttaget. Enskilda ord
    racker inte: en rubrik som namner publicistens hemort ("Jamaica receives...")
    ar inte ett varumarkessegment.
    """
    core = _squash(domain.split(".")[0])
    words = [w for w in re.split(r"[^A-Za-z0-9]+", seg) if w]
    if not core or not words: return False
    sq = re.sub(r"^the", "", _squash(seg))
    if sq and (sq in core or core in sq): return True
    if len(words) > 6: return False
    if seg.isupper() and len(sq) <= 12: return True
    segw = {w.lower() for w in words}
    return bool(segw & {"news", "online", "live", "today", "times", "post", "herald", "tribune"}) and len(segw) <= 5

def _strip_tail(parts, domain):
    while len(parts) > 1 and _brandish(parts[-1], domain):
        parts = parts[:-1]
    return parts

def from_title(title, domain):
    """Rensar publicistens namn ur sidtiteln.

    Tre kandidater provas i tur och ordning och den forsta som ser ut som en
    rubrik vinner: helrensad (ledande varumarke bort, allt fran forsta ovriga
    varumarkessegment bort, avslutande varumarken bort), bara avslutande
    varumarken bort, och till sist titeln som den star. Kandidaten forkastas
    om den ar kortare an fyra ord eller sjalv ar ett varumarkessegment - da
    har rensningen atit rubriken.
    """
    title = html.unescape(title)
    parts = [x.strip() for x in SEP.split(title) if x.strip()]
    if not parts: return ""

    full = list(parts)
    if len(full) > 1 and _brandish(full[0], domain): full = full[1:]
    for k in range(1, len(full)):
        if _brandish(full[k], domain):
            full = full[:k]; break
    full = _strip_tail(full, domain)

    for cand in (" - ".join(full), " - ".join(_strip_tail(list(parts), domain)), title):
        c = cand.strip()
        if len(c.split()) >= 4 and not _brandish(c, domain):
            return c
    return ""

def _words(x):
    return {w for w in re.split(r"[^a-z0-9]+", x.lower()) if len(w) > 3}

def _relates(claim, url):
    """Rubriken ska handla om artikeln. Delar den inget ord med adressen ar det
    sannolikt en startsida, en betalvagg eller en cookie-ruta - inte en rubrik."""
    slug = _words(from_url(url))
    if len(slug) < 2: return True
    return bool(_words(claim) & slug)

def from_url(url):
    seg = [s for s in re.split(r"[/?#]", url) if s]
    seg = seg[-1] if seg else ""
    seg = re.sub(r"\.(html?|php|aspx?|ece|cms)$", "", seg, flags=re.I)
    words = [w for w in re.split(r"[-_.]+", seg)
             if w and not w.isdigit() and w.lower() not in STOP and len(w) < 30]
    if not words: return ""
    s = " ".join(words)
    return s[0].upper() + s[1:]

# En sammanfattningsartikel bar flera informationstillstand, inte ett. "5 stories you
# might have missed" ar fem handelser i en ruta och bryter mot grundregeln en observation
# = en ruta. Monstret ar publicerat och rakningsbart, precis som storytakets troskel.
DIGEST = re.compile(
    r"(while you were sleeping|stories you (might|may) have missed|morning briefing"
    r"|evening briefing|news round-?up|roundup|today'?s headlines|what to know"
    r"|five things|5 things|top stories|in pictures|live updates|live blog"
    r"|as it happened|weekly digest|newsletter|up first)", re.I)

def is_digest(claim):
    """Sant om raden ar en sammanfattning av flera nyheter, inte en observation."""
    return bool(DIGEST.search(claim or ""))

def claim_of(page_title, domain, url):
    """Den enda definitionen av klassificerarens input. Anvands bade av
    urvalsfiltret och av inputbygget - annars kan urvalet slappa igenom en rad
    som inputbygget inte kan lasa. Returnerar (claim, claim_source)."""
    title = (page_title or "").strip()
    claim = from_title(title, domain) if title else ""
    slug = from_url(url)
    usable_slug = len([w for w in re.split(r"[^A-Za-z]+", slug) if len(w) > 2]) >= 3
    if claim and usable_slug and not _relates(claim, url):
        claim = ""
    if claim:
        return claim, "LIVE_FETCH"
    if usable_slug:
        return slug, "URL_SLUG"
    if title:
        return html.unescape(title).strip(), "PAGE_TITLE_UNVERIFIED"
    return "", "NONE"

def readable(claim):
    return len([w for w in re.split(r"[^A-Za-z]+", claim) if len(w) > 2]) >= 3

def build(manifest, evidence, state_id):
    rows = list(csv.DictReader(open(manifest, encoding="utf-8")))
    ev = {}
    for line in Path(evidence).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line); ev[r["observation_id"]] = r
    out = []
    for r in rows:
        e = ev.get(r["observation_id"], {})
        t = (e.get("page_title") or "").strip()
        claim = from_title(t, r["representative_domain"]) if t else ""
        src = e.get("title_source") or "LIVE_FETCH"
        slug = from_url(r["representative_url"])
        usable_slug = len([w for w in re.split(r"[^A-Za-z]+", slug) if len(w) > 2]) >= 3
        if claim and usable_slug and not _relates(claim, r["representative_url"]):
            claim = ""          # sidtiteln hor inte till artikeln
        if not claim:
            # en adress utan ord ("article70456163") sager ingenting - da ar
            # sidtiteln, hur generisk den an ar, det basta vi har
            claim, src = (slug, "URL_SLUG") if usable_slug else (html.unescape(t).strip(), "PAGE_TITLE_UNVERIFIED")
        if not claim:
            claim, src = slug, "URL_SLUG"
        out.append({
            "observation_id": r["observation_id"],
            "tile_index": int(r["tile_index"]),
            "observation_timestamp_utc": r["first_mention_utc"],
            "neutral_source_claim": claim,
            "claim_source": src,
            "evidence_basis": e.get("evidence_basis", "NO_EVIDENCE"),
            "action_geo_country": r["action_geo_country"],
            "review_region": r["review_region"],
            "selection_layer": r["selection_layer"],
            "source_tier": r["source_tier"],
            "representative_domain": r["representative_domain"],
        })
    return out

if __name__ == "__main__":
    manifest, evidence, state, outdir = sys.argv[1:5]
    items = build(manifest, evidence, state)
    d = Path(outdir); d.mkdir(parents=True, exist_ok=True)
    from config import canonical_batch_size
    bs = canonical_batch_size()          # ur specen, aldrig hardkodad
    for k in range(0, len(items), bs):
        (d / f"classifier_input_batch_{k//bs+1:02d}.json").write_text(
            json.dumps(items[k:k+bs], ensure_ascii=False, indent=1), encoding="utf-8")
    import collections
    print(len(items), "observations ->", d)
    print(collections.Counter(i["claim_source"] for i in items))
