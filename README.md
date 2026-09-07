# 600 STATES — pipeline v3.0

Kod ar sanningen. Prosabeskrivningar i checkpoint-dokument ar det inte —
se FYND 001, dar den dokumenterade hashformeln visade sig vara fel.

## Uppdelning kod / data

| | Var | Varfor |
|---|---|---|
| **Kod** (detta repo) | `C:\dev\600-states` | git, kort sokvag, ingen molnsynk |
| **Data** | OneDrive, `600 STATES` | stor, binar, andras sallan; git ar dalig pa sadant |

`config.py` ar enda stallet dar sokvagen till datan bor. Satt `STATES_DATA`
for att peka nagon annanstans.

**Lagg aldrig repot i OneDrive.** Git skriver manga sma filer snabbt; synken
lagger tillbaka aldre versioner och skapar konfliktkopior. Projektet har redan
tre `(1)`-filer och fyra misslyckade kopieringar av den orsaken.

## Kor

    python tests/test_evidence_hash.py                  # regressionsskydd, FYND 001
    python src/join_check.py <manifest.csv> <raw.zip>   # finns valda rader i raflodet?

## Verifierat 2026-09-07

| Kontroll | Resultat |
|---|---|
| `evidence_row_sha256`, v2.2 #002–#010 | 5 400 / 5 400 |
| `evidence_row_sha256`, v2.3 #002–#010 | 0 / 5 400 — FYND 001 |
| `evidence_row_sha256`, v1.4 #001 | 0 / 600 — tredje okant schema |
| URL aterfinns i raflodet, #001–#010 | 6 000 / 6 000 |
| Tidsstampel matchar raflodet | 6 000 / 6 000 |

Referensgeneration: **v2.2**. v2.3 anvands inte som sanning.

## Kanonisering, `evidence_row_sha256` (v2.2)

    SHA256( "|".join(alla kolumner utom evidence_row_sha256, i CSV-kolumnordning) )

## Nasta steg

Urvalsmotorn. Malet ar INTE att reproducera v2.2:s exakta 600 rader — det vore
att aterimplementera odokumenterade heuristiker (`priority_score`, `signature_v2`).
Malet ar ett giltigt 600-radersurval som uppfyller samtliga frysta villkor,
byggt fran raflodet.
