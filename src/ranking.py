"""Rangordning av kandidater — avgor vilka som far bevisfangst.

Detta ar INTE urvalet. Det ar en trattning fran hela dygnets kandidatpool till en
delmangd med marginal, sa att bevisfangst och rubrikbaserad klustring blir
overkomliga. Sjalva urvalet av 600 sker efter materialitetsbedomningen.

Signalen ar GDELT:s omnamnandevolym. Uppmatt pa #002 (600 valda mot 2280 ovalda):

    mention_rows     valda median 10,0   ovalda median 3,0
    antal event_ids  valda median 10,0   ovalda median 3,0
    cluster_domains  valda median  1,0   ovalda median 1,0   (svag)
    source_tier      ingen atskillnad (samma A/B-kvot i bada grupper)

Omnamnandevolym ar alltsa den enda starkt separerande signalen. Ingen estetik,
ingen emotion, ingen farg — enligt frozen protokoll.
"""

CAPTURE_N = 1500

def rank(cands):
    """Fallande omnamnandevolym, deterministiskt tiebreak pa tid och URL."""
    return sorted(cands, key=lambda c: (-c["mention_rows"], c["first_mention_utc"], c["url"]))

def capture_set(cands, n=CAPTURE_N):
    """Delmangd som far bevisfangst.

    Uppmatt overlapp med det historiska urvalet for #002:
        topp  600 -> 58,5 %
        topp 1200 -> 90,7 %
        topp 1500 -> 94,8 %
        topp 1800 -> 96,5 %

    1500 valt: nastan hela det utrymme en mogen urvalsmotor skulle vilja ha,
    till ungefar halva hamtningskostnaden mot hela poolen (2880 for #002).

    Overlappet ar en rimlighetskontroll, inte ett mal. v3.0 ska inte reproducera
    det historiska urvalet (se FYND 002) — men en rangordning som INTE innehaller
    det gamla urvalet vore ett tecken pa att signalen ar fel.
    """
    return rank(cands)[:n]
