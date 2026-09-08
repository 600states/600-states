"""Fargprotokoll v0.4 Golden Master. FRYST.

Detta ar den enda implementationen. Den anvands bade for att rendera och for
att verifiera - en rad vars hex inte kan reproduceras har ar ett fel i
manifestet, inte en anledning att andra formeln.

Ingenting i denna fil far andras for att bilden ska bli snyggare. Se
parameterregistret avsnitt 0.
"""
import colorsys

VOCAB = ["Joy", "Hope", "Relief", "Calm", "Curiosity", "Awe", "Resolve", "Surprise",
         "Uncertainty", "Concern", "Tension", "Fear", "Anger", "Grief", "Disillusion", "Fatigue"]

# ankare: hue, saturation, lightness, range
ANCHORS = {
    "Joy": (45, 0.76, 0.62, 0.16),      "Hope": (145, 0.31, 0.56, 0.15),
    "Relief": (166, 0.30, 0.56, 0.14),  "Calm": (178, 0.34, 0.56, 0.15),
    "Curiosity": (205, 0.52, 0.48, 0.17), "Awe": (244, 0.25, 0.61, 0.13),
    "Resolve": (211, 0.48, 0.34, 0.16), "Surprise": (326, 0.38, 0.65, 0.13),
    "Uncertainty": (226, 0.21, 0.48, 0.15), "Concern": (28, 0.50, 0.55, 0.17),
    "Tension": (23, 0.73, 0.50, 0.18),  "Fear": (9, 0.61, 0.43, 0.18),
    "Anger": (2, 0.61, 0.37, 0.17),     "Grief": (350, 0.40, 0.30, 0.15),
    "Disillusion": (20, 0.17, 0.38, 0.14), "Fatigue": (213, 0.11, 0.45, 0.12),
}
POSITIVE = {"Joy", "Hope", "Relief", "Calm", "Curiosity", "Awe", "Surprise"}

def rgb(primary, secondary, intensity, confidence):
    ph, ps, pl, rng = ANCHORS[primary]
    sh = ANCHORS[secondary][0]
    w = 0.055 + 0.105 * (1 - confidence)
    d = ((sh - ph + 180) % 360) - 180          # kortaste cirkulara hue-vag
    h = (ph + w * d) % 360
    sat = ps * (0.62 + 0.31 * intensity + 0.10 * confidence)
    if primary in ("Awe", "Surprise"): sat *= 0.78
    if primary in ("Uncertainty", "Disillusion", "Fatigue"): sat *= 0.88
    if primary == "Resolve":
        l = pl - (intensity - 0.52) * rng * 0.72 + (confidence - 0.76) * 0.04
    elif primary in POSITIVE:
        l = pl + (intensity - 0.45) * rng * 1.18 + (confidence - 0.76) * 0.055
    else:
        l = pl - (intensity - 0.38) * rng * 1.32 + (confidence - 0.76) * 0.035
    sat = min(max(sat, 0.09), 0.78)
    l = min(max(l, 0.175), 0.79)
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l, sat)
    return (round(r * 255), round(g * 255), round(b * 255))

def hex_of(primary, secondary, intensity, confidence):
    return "#%02X%02X%02X" % rgb(primary, secondary, intensity, confidence)

def hex_of_row(row):
    return hex_of(row["primary_emotion"], row["secondary_emotion"],
                  float(row["intensity"]), float(row["confidence"]))
