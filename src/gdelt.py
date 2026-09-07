"""Laddare for GDELT 2.0 Mentions - nastlade zip-arkiv, ett dygn per yttre zip."""
import zipfile, io, csv, sys
from collections import defaultdict

COLS = ["GlobalEventID","EventTimeDate","MentionTimeDate","MentionType","MentionSourceName",
        "MentionIdentifier","SentenceID","Actor1CharOffset","Actor2CharOffset","ActionCharOffset",
        "InRawText","Confidence","MentionDocLen","MentionDocTone","MentionDocTranslationInfo","Extras"]

def iter_mentions(outer_zip_path):
    """Ger en dict per mention-rad. Hanterar nastlad zip-i-zip."""
    with zipfile.ZipFile(outer_zip_path) as outer:
        for inner_name in sorted(outer.namelist()):
            if not inner_name.lower().endswith(".zip"):
                continue
            data = outer.read(inner_name)
            with zipfile.ZipFile(io.BytesIO(data)) as inner:
                for csv_name in inner.namelist():
                    raw = inner.read(csv_name).decode("utf-8", errors="replace")
                    for line in raw.split("\n"):
                        if not line.strip():
                            continue
                        parts = line.split("\t")
                        if len(parts) < 6:
                            continue
                        yield dict(zip(COLS, parts))

def load_day(outer_zip_path):
    """Returnerar (rader, url_index) dar url_index: url -> lista av rader."""
    rows = []
    by_url = defaultdict(list)
    for m in iter_mentions(outer_zip_path):
        rows.append(m)
        by_url[m["MentionIdentifier"]].append(m)
    return rows, by_url

if __name__ == "__main__":
    rows, by_url = load_day(sys.argv[1])
    print(f"mentions: {len(rows):,}   unika URL:er: {len(by_url):,}")
    print("exempelrad:", {k: rows[0][k] for k in ("GlobalEventID","MentionTimeDate","MentionSourceName","MentionIdentifier")})
