"""Storytak — deterministisk ersattning for materialitetsbedomningen.

Ingen modell. Inget omdome. Inget REVIEW_REQUIRED som kan blockera en frysning.

Girigt urval i kronologisk ordning: en kandidat slapps in om den liknar hogst
N-1 redan inslappta rutor. Varje jamforelse gors mot en faktiskt inslappt ruta,
aldrig transitivt — det ar det som gor att kluster inte kedjas ihop till blobbar
(forsta forsoket gav kluster pa 265 orelaterade nyheter).

BESLUT 2026-09-07: N=1, troskel 0,25.

Ett informationstillstand, en ruta. Likhet avgors av ett publicerat matt,
inte av ett tyckande.

Varfor 0,25 och inte 0,20: av de 142 par som slas ihop vid 0,20 men inte vid
0,25 ar ungefar halften felaktiga sammanslagningar. Tva av dem ar fall som
projektets egen re-audit uttryckligen domde DISTINCT (byggnadskollapsen i
South C mot politikerns krav pa byggstopp; bergslejonattacken mot den tidigare
incidenten). Andra slar ihop Pakistans och Sydkoreas Kina-politik, eller tva
orelaterade dodsfall som bara delar orden "family" och "new year day".

Felen ar inte symmetriska. En missad dubblett SYNS - dygnet ser repetitivt ut
och vem som helst kan klicka och se det. En felaktig sammanslagning RADERAR en
verklig handelse utan spar. For ett arkiv ar det andra felet varre.

BAND 0,20-0,25: par i detta intervall tas INTE bort. De loggas i manifestet som
NEAR_DUPLICATE_OBSERVED. Da syns gransfallen offentligt i stallet for att
forsvinna, och mattet blir granskningsbart at bada hallen.
"""

NEAR_DUPLICATE_BAND = (0.20, 0.25)
import re

STOP = set("""a an and are as at be by for from has have in is it its of on or that the to was
with news say says said new after over into more than about against amid ahead his her they
their will would can could""".split())

DEFAULT_N = 1
DEFAULT_THRESHOLD = 0.25

def tokens(text):
    return {w for w in re.split(r"[^a-zA-ZÀ-ÿ0-9]+", (text or "").lower())
            if len(w) > 2 and w not in STOP}

def near_duplicates(rows, text_of, band=NEAR_DUPLICATE_BAND):
    """Par i granslandet. Tas inte bort - loggas som NEAR_DUPLICATE_OBSERVED."""
    lo, hi = band
    toks = [(r, tokens(text_of(r))) for r in rows]
    out = []
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            a, b = toks[i][1], toks[j][1]
            un = a | b
            if not un:
                continue
            jac = len(a & b) / len(un)
            if lo <= jac < hi:
                out.append({"a": toks[i][0], "b": toks[j][0], "jaccard": round(jac, 3)})
    return out


def apply_cap(rows, text_of, time_of, n=DEFAULT_N, threshold=DEFAULT_THRESHOLD):
    """Returnerar (inslappta, bortsorterade) i kronologisk ordning.

    rows      – kandidater
    text_of   – funktion rad -> rubrik eller claim
    time_of   – funktion rad -> sorterbar tidsstampel
    """
    admitted, admitted_tok, rejected = [], [], []
    for r in sorted(rows, key=time_of):
        t = tokens(text_of(r))
        hits = 0
        for at in admitted_tok:
            un = t | at
            if un and len(t & at) / len(un) >= threshold:
                hits += 1
                if hits >= n:
                    break
        if hits >= n:
            rejected.append(r)
        else:
            admitted.append(r); admitted_tok.append(t)
    return admitted, rejected
