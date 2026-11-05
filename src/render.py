"""Renderar ett State ur fargmanifestet. Deterministiskt.

Bilden ar en konsekvens av manifestet, aldrig tvartom. Ingen parameter har far
justeras for att bilden ska bli snyggare - se parameterregistret avsnitt 0.
Grid Specification v1.0: 30x20, celler 100x100, separator 3 px #0B0E12.

Ligger pa fargsidan av kedjan. Importeras av run_color.py, aldrig av
urvals- eller klassificeringsprogrammet.
"""
import csv, sys
from pathlib import Path
from PIL import Image, ImageDraw
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import statepaths as sp
from atomic import write_bytes
from config import DATA
from color_protocol import hex_of_row

COLS, ROWS, CELL, SEP = 30, 20, 100, 3
SEP_RGB = (0x0B, 0x0E, 0x12)

def render_state(day, data=DATA):
    src = sp.color_manifest(data, day)
    rows = sorted(csv.DictReader(open(src, encoding="utf-8")), key=lambda r: int(r["tile_index"]))
    if len(rows) != COLS * ROWS:
        raise SystemExit(f"manifestet har {len(rows)} rader, vantade {COLS*ROWS}")

    img = Image.new("RGB", (COLS * CELL + (COLS - 1) * SEP,
                            ROWS * CELL + (ROWS - 1) * SEP), SEP_RGB)
    dr = ImageDraw.Draw(img)
    for r in rows:
        i = int(r["tile_index"]) - 1
        x, y = (i % COLS) * (CELL + SEP), (i // COLS) * (CELL + SEP)
        hx = hex_of_row(r)
        if hx.upper() != str(r["hex"]).upper():
            raise SystemExit(f"ruta {r['tile_index']}: manifestet sager {r['hex']}, protokollet {hx}")
        dr.rectangle([x, y, x + CELL - 1, y + CELL - 1],
                     fill=tuple(int(hx[k:k+2], 16) for k in (1, 3, 5)))

    import io
    buf = io.BytesIO(); img.save(buf, "PNG", optimize=True)
    return write_bytes(sp.png(data, day), buf.getvalue())

if __name__ == "__main__":
    print(render_state(sys.argv[1]))
