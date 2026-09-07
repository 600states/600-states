"""Bevisfangst: hamta artikel, hasha ra bytes, spara snapshot.

Ingen modell ar inblandad i detta steg. Ra bytes -> SHA-256.
Domanspärr: endast doman i det frusna kallregistret far hamtas.
"""
import hashlib, json, re, socket, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

UA = "600STATES-archival/1.0 (research archival crawler; contact: archive@600states.com)"
TIMEOUT = 20

def load_registry(path):
    import csv
    with open(path, encoding="utf-8") as fh:
        return {r["domain"].strip().lower() for r in csv.DictReader(fh)}

def _title(html_bytes):
    try:
        head = html_bytes[:200_000].decode("utf-8", errors="replace")
    except Exception:
        return ""
    m = re.search(r"<title[^>]*>(.*?)</title>", head, re.I | re.S)
    if not m:
        return ""
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    return t[:300]

def fetch_one(url, allowed=None):
    """Returnerar bevispost. Ingen modell, ingen tolkning - bara bytes och metadata."""
    rec = {"url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "http_status": None, "content_sha256": None, "bytes": 0, "final_url": None,
           "page_title": "", "error": None}
    if allowed is not None:
        dom = re.sub(r"^www\.", "", (urllib.request.urlparse(url).netloc or "").lower())
        if dom not in allowed:
            rec["error"] = f"DOMAN_EJ_I_REGISTER:{dom}"
            return rec
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read(8_000_000)
            rec["http_status"] = resp.status
            rec["final_url"] = resp.url
            rec["bytes"] = len(body)
            rec["content_sha256"] = hashlib.sha256(body).hexdigest()
            rec["page_title"] = _title(body)
            rec["_body"] = body
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code; rec["error"] = f"HTTP_{e.code}"
    except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
        rec["error"] = f"NET:{type(e).__name__}"
    except Exception as e:
        rec["error"] = f"ERR:{type(e).__name__}"
    return rec

def fetch_many(urls, allowed=None, workers=8, snapshot_dir=None):
    out = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for rec in ex.map(lambda u: fetch_one(u, allowed), urls):
            body = rec.pop("_body", None)
            if body and snapshot_dir:
                d = Path(snapshot_dir); d.mkdir(parents=True, exist_ok=True)
                (d / f"{rec['content_sha256']}.html").write_bytes(body)
                rec["snapshot_path"] = f"{rec['content_sha256']}.html"
            out.append(rec)
    return out
