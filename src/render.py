"""Renderar ett State ur emotionsmanifestet. Deterministiskt.

Bilden ar en konsekvens av manifestet, aldrig tvartom. Ingen parameter har far
justeras for att bilden ska bli snyggare - se parameterregistret avsnitt 0.
Grid Specification v1.0: 30x20, celler 100x100, separator 3 px #0B0E12.
"""
import csv, sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA
from color_protocol import hex_of_row

COLS, ROWS, CELL, SEP = 30, 20, 100, 3
SEP_RGB = (0x0B, 0x0E, 0x12)

def render_state(state, version="v3.1"):
    d = DATA / "08_V3_STATES" / f"STATE_{state}"
    src = d / f"600_STATES_2026_{state}_EMOTION_COLOR_MANIFEST_{version}_CONSENSUS.csv"
    rows = sorted(csv.DictReader(open(src, encoding="utf-8")), key=lambda r: int(r["tile_index"]))
    if len(rows) != COLS * ROWS:
        raise SystemExit(f"manifestet har {len(rows)} rader, vantade {COLS*ROWS}")

    w = COLS * CELL + (COLS - 1) * SEP
    h = ROWS * CELL + (ROWS - 1) * SEP
    img = Image.new("RGB", (w, h), SEP_RGB)
    dr = ImageDraw.Draw(img)
    for r in rows:
        i = int(r["tile_index"]) - 1
        cx, cy = i % COLS, i // COLS
        x, y = cx * (CELL + SEP), cy * (CELL + SEP)
        hx = hex_of_row(r)
        if hx.upper() != str(r["hex"]).upper():
            raise SystemExit(f"ruta {r['tile_index']}: manifestet sager {r['hex']}, protokollet {hx}")
        dr.rectangle([x, y, x + CELL - 1, y + CELL - 1],
                     fill=tuple(int(hx[k:k+2], 16) for k in (1, 3, 5)))
    out = d / f"600_STATES_2026_{state}_{version}_CONSENSUS.png"
    img.save(out, "PNG", optimize=True)
    return out

if __name__ == "__main__":
    print(render_state(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "v3.1"))
