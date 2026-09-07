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

## Events-data (löst 2026-09-07)

Events-filerna finns nu i `01_RAW_GDELT_2026_001_010` — **GDELT 1.0 dagsfiler**
(`YYYYMMDD.export.CSV.zip`, 58 falt, en fil per dygn), inte GDELT 2.0:s
15-minutersfiler. Fungerar lika bra och ar enklare: 1 fil per dygn i stallet for 96.

Faltindex som anvands: `GLOBALEVENTID` 0, `ActionGeo_CountryCode` 51,
`ActionGeo_FullName` 50, `SOURCEURL` 57.

Verifierat mot #002 (2026-01-02): 73 887 events, 600/600 av manifestets
`representative_event_ids` aterfinns.

### Regel for review_region

Geografin ligger pa de *lankade* eventen, inte pa ett enskilt. Traffsakerhet mot
den frusna `action_geo_country`:

| Regel | Traff |
|---|---|
| forsta event-id | 81,6 % |
| URL-matchad event | 67,7 % |
| **vanligaste bland event-ids (majoritet)** | **97,4 %** |
| nagon av event-ids | 100 % |

v3.0 anvander **majoritetsregeln**: vanligaste `ActionGeo_CountryCode` bland
klustrets lankade events. Deterministisk och reproducerar den historiska
tilldelningen till 97,4 %.

## KVARSTAENDE BLOCKERING — natverk for nya dygn

Pilotdygnen ar losta med lokal data. For **nya** dygn kravs fortfarande utgaende
natverk, som ar blockerat i bada miljoerna:

| Mal | Behovs for | Resultat |
|---|---|---|
| `data.gdeltproject.org` | Mentions + Events for nya dygn | HTTP 403 |
| `web.archive.org` | arkivlank per observation (bevisfangst) | ingen anslutning |

Utan allowlist kan pipelinen aldrig kora automatiskt pa nya dygn.
