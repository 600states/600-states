"""Storytak — deterministisk ersattning for materialitetsbedomningen.

Ingen modell. Inget omdome. Inget REVIEW_REQUIRED som kan blockera en frysning.

Girigt urval i kronologisk ordning: en kandidat slapps in om den liknar hogst
N-1 redan inslappta rutor. Varje jamforelse gors mot en faktiskt inslappt ruta,
aldrig transitivt — det ar det som gor att kluster inte kedjas ihop till blobbar
(forsta forsoket gav kluster pa 265 orelaterade nyheter).

Uppmatt pa #002-#010 (5400 rader), troskel 0,30:

    N=1   915 rutor bortsorterade (16,9 %)
    N=2   408 (7,6 %)
    N=3   242 (4,5 %)
    N=5    99 (1,8 %)

Re-auditens manuella semantiska bedomning gav 663. Den manskliga standarden
ligger alltsa mellan N=1 och N=2 vid denna troskel.
"""
import re

STOP = set("""a an and are as at be by for from has have in is it its of on or that the to was
with news say says said new after over into more than about against amid ahead his her they
their will would can could""".split())

DEFAULT_N = 3
DEFAULT_THRESHOLD = 0.30

def tokens(text):
    return {w for w in re.split(r"[^a-zA-ZÀ-ÿ0-9]+", (text or "").lower())
            if len(w) > 2 and w not in STOP}

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
