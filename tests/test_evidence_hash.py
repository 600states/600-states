"""Regressionsskydd for FYND 001.

Den dokumenterade formeln i checkpoint v2.7 var fel. Den verkliga kanoniseringen
ar aterskapad empiriskt och lases fast har. Andras den, ska testet falla.
"""
import csv, io, zipfile, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evidence_hash import row_hash
from config import REMEDIATION

PKG = REMEDIATION / "600_STATES_2026_002_010_FROZEN_PRE_EMOTION_PACKAGE_v2.2_SEMANTIC_MATERIALITY_STRICT.zip"
FIELD = "evidence_row_sha256"

def _manifests():
    with zipfile.ZipFile(PKG) as z:
        for n in z.namelist():
            if "MANIFEST_v2.2" in n and n.endswith(".csv"):
                yield n, z.read(n).decode("utf-8")

def test_v22_alla_rader_reproducerar():
    total = ok = 0
    for name, text in _manifests():
        rows = list(csv.DictReader(io.StringIO(text)))
        cols = [c for c in rows[0] if c != FIELD]
        for r in rows:
            total += 1
            if row_hash(r, cols) == r[FIELD].lower():
                ok += 1
    assert total == 5400, f"forvantade 5400 rader, fick {total}"
    assert ok == total, f"{total-ok} rader reproducerade inte"

if __name__ == "__main__":
    test_v22_alla_rader_reproducerar()
    print("OK - 5400/5400 rader reproducerar")
