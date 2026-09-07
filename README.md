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

## Bevisfangst — matning 2026-09-07 (natverk oppnat)

Stickprov: 120 slumpvis valda av #002:s 600 URL:er.

| Utfall | Antal | Andel |
|---|---|---|
| 200 OK direkt | 95 | 79,2 % |
| HTTP 403 (botspärr) | 20 | 16,7 % |
| timeout / 308 / 406 | 5 | 4,2 % |
| **404 eller 410 (dod lank)** | **0** | **0 %** |

**Noll doda lankar.** Artiklarna finns kvar; misslyckandena ar sajter som
blockerar var hamtare, inte forsvunnet innehall.

Av de 25 misslyckade fanns 23 i Wayback. **Total tackning 118/120 = 98,3 %.**

### Foljd for evidence_basis

Wayback-traffarna ar daterade 2026-01-02/03 — allts fran sjalva
observationsdygnet, inte fran idag. For de raderna ar beviset *samtida*, inte
retrospektivt. v0.2 var for pessimistisk. Tre nivaer galler:

| Varde | Betydelse |
|---|---|
| `OBSERVED_AT_CAPTURE` | hamtad under observationsdygnet (nya dygn) |
| `CONTEMPORANEOUS_ARCHIVE` | arkivkopia fran observationsdygnet (manga pilotrader) |
| `RETROSPECTIVE` | hamtad i efterhand, manader senare |

Wayback ar fortfarande inte kritisk vag och far aldrig blockera ett dygn — men
for pilotdagarna ar den mer varde an v0.2 antog.

### Domanspärr

`fetch_evidence.py` slapper bara igenom domaner ur det frusna kallregistret
(75 st), oavsett att plattformens egress ar oppen. Plattformen ar oppen,
programmet ar last.
