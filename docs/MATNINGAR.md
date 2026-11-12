# 600 STATES — pipeline v3.0

Kod ar sanningen. Prosabeskrivningar i checkpoint-dokument ar det inte —
se FYND 001, dar den dokumenterade hashformeln visade sig vara fel.

## Uppdelning kod / data

| | Var | Varfor |
|---|---|---|
| **Kod** (detta repo) | en lokal mapp utanfor molnsynken | git, kort sokvag, ingen molnsynk |
| **Data** | utanfor repot, pekas ut av `STATES_DATA` | stor, binar, andras sallan; git ar dalig pa sadant |

`config.py` ar enda stallet dar sokvagen till datan bor, och den hardkodar
ingen: `STATES_DATA` pekar ut arkivet.

**Lagg aldrig repot i en molnsynkad mapp.** Git skriver manga sma filer snabbt; synken
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
| `CAPTURED_IN_WINDOW` | hamtad i bevisfonstret (nya dygn) - het OBSERVED_AT_CAPTURE till 2026-11-11, se pool_evidence.py |
| `CONTEMPORANEOUS_ARCHIVE` | arkivkopia fran observationsdygnet (manga pilotrader) |
| `RETROSPECTIVE` | hamtad i efterhand, manader senare |

Wayback ar fortfarande inte kritisk vag och far aldrig blockera ett dygn — men
for pilotdagarna ar den mer varde an v0.2 antog.

### Domanspärr

`fetch_evidence.py` slapper bara igenom domaner ur det frusna kallregistret
(75 st), oavsett att plattformens egress ar oppen. Plattformen ar oppen,
programmet ar last.

## Lager 2a — kandidathamtning, matt recall (2026-09-07)

Facit: 34 bekraftade dubblettgrupper i #002 fran den historiska re-auditen, 177 par.
Bada URL:erna finns i kandidatpoolen for samtliga 177.

| Trosklar | Recall | Grupper | Par att bedoma |
|---|---|---|---|
| jac 0,50 / ev 0,25 | 68,9 % | 205 | 734 |
| jac 0,45 / ev 0,20 | 76,3 % | 209 | 862 |
| **jac 0,40 / ev 0,20** | **79,7 %** | 218 | 1004 |
| jac 0,35 / ev 0,15 | 79,7 % | 238 | 1225 |

**Recall planar pa ~80 %.** Lagre trosklar ger fler par men inte fler traffar.

### Diagnos

De sista 20 % ar dubbletter som URL-slugen omojligt kan fanga: olika redaktioner
skriver genuint olika slugar for samma handelse. Det ar exakt samma tak som gav
upphov till ursprungsdefekten (FYND 002) — man kan inte deduplicera information
genom att titta pa adresser.

### Foljd: pipelineordningen andras

Retrieval maste kora pa **artikelrubrik**, inte pa URL-slug. Rubriken finns i
bevisfangsten, som darmed maste ske FORE klustringen.

    tidigare:  kandidater -> klustra -> valj 600 -> bevisfangst
    ratt:      kandidater -> rangordna -> bevisfangst -> klustra pa rubrik
               -> materialitetsbedomning -> valj 600

Kostnad: bevisfangst pa fler an 600 dokument per dygn. Motmedel: rangordna forst
och fanga bevis for en delmangd med marginal (storleksordning 1200 av 2880),
i stallet for hela poolen.

### Event-ID far aldrig sla samman transitivt

Forsta implementationen slog ihop pa delat GDELT-event-ID och producerade tva
jattekluster pa 339 respektive 318 dokument med helt orelaterade nyheter kedjade
samman. GDELT overmergear event (PE-004). Delat event-ID ar nu ett parsignal som
alltid kraver lexikaliskt stod. Storsta gruppen darefter: 19 dokument.

## Klustringsmetod — avgjord genom matning (2026-09-07)

### Mattet var fel forst

Recall mattes forst **per par**. Det ar fel matt: facitgrupperna ar transitiva
(en grupp pa 11 ger 55 par, men klustringen behover bara en sammanhangande kedja).
Ratt matt ar **hur manga grupper som halls ihop**.

Med ratt matt, pa 34 bekraftade dubblettgrupper i #002:

| Metod | Troskel | Grupper helt fangade | Extra par att bedoma |
|---|---|---|---|
| Lexikalisk pa rubrik | 0,20 | **30/34 (88,2 %)** | **275** |
| Lexikalisk pa rubrik | 0,25 | 28/34 (82,4 %) | 154 |
| Embeddings (MiniLM) | 0,45 | 31/34 (91,2 %) | 873 |
| Embeddings (MiniLM) | 0,50 | 31/34 (91,2 %) | 619 |

### Beslut: lexikalisk pa rubrik, Jaccard 0,20. Inga embeddings.

Embeddings vinner tre procentenheter — en enda grupp av 34 — till tre ganger
bedomningskostnaden, och kraver torch plus en nedladdad modell vars beteende
andras mellan versioner. I ett instrument som ska kunna koras om identiskt om tio
ar ar det fel avvagning. Determinism vager tyngre an tre procentenheter.

### Nasta forbattring ar inte metoden, det ar tackningen

Grupperna som fallerar innehaller rader dar rubriken saknas och slugen anvands som
reserv. Rubriktackning i testet: 494 av 600. Battre hamtning (andra headers, omforsok,
Wayback-reserv for rubrik) ar billigare an embeddings och traffar samma problem.

## Generalrepetition 2026/315 — hela kedjan skarpt under v3.3 (2026-11-12)

Forsta korningen av hela kedjan raflode -> bild under v3.3. Dygnet ar inte ett
seriedygn; serien startar 2026/335. Syftet var att de nitton kolumnerna,
`evidence_basis`, `evidence_retrieved_at` och `gate_evidence_time` skulle ga
hela vagen en gang innan de provas pa ett seriedygn.

Ingen grind stoppade kedjan. Revisionen reproducerar 600/600 hex ur
protokollet.

| Steg | Grind | Utfall |
|---|---|---|
| acquire | kompletthet | 96/96 slots, `COMPLETE` |
| candidates | dygn, mention_rows, register | 3 786 kandidater, 0 utanfor registret |
| pool | rubriktackning | 3 599/3 786 = 95,1 % (golv 60 %) |
| select | 600, regionkvoter, cap | 600, alla regioner >= 30, max 10 per publicist |
| select | `gate_evidence_time` | 0 rader utan tidsstampel, 0 utan niva |
| input | lasbar text | 600 rader, 0 sammanfattningar |
| emotion | ID-mangd, vokabular, spridning | 600 in = 600 ut, 48 unika intensity |
| color | manifestet orort sedan frysningen | sha256 stammer |

Bevisnivaer: 565 `RETROSPECTIVE`, 35 `NO_EVIDENCE`, 0 `CAPTURED_IN_WINDOW`.
Hamtningen skedde 2026-11-12 20:46-20:53 UTC, knappt arton timmar efter att
bevisfonstret stangde 03:00 UTC. Fordelningen ar den vantade for en
efterhandskorning och ar inte ett fel — men den betyder ocksa att
`CAPTURED_IN_WINDOW` annu aldrig har producerats skarpt. Den nivan ar oprovad
tills ett dygn kors i fonstret.

De 35 `NO_EVIDENCE` bar URL men ingen hashad sida: 23 utan svar, 11 med HTTP
403, 1 med 404. Deras klassificeringstext kommer ur URL-slugen. Grinden
slapper dem med ratta — nivan star i vokabularet — men det ar sa botten ser ut
pa ett retrospektivt dygn.

Klassificeringen kordes `--en-i-taget`: 1 800 begaran, 36 passfiler, 600
observationer i alla tre pass. Ett parse-fel (`JSONDecodeError`, extra data
efter det avslutade objektet) pa 1 800 begaran; rondmekaniken begarde om den
enda observationen och den gick igenom. En emissionsartefakt. Noll nollfyllda
rader, noll rader med tva eller farre egna poang, noll fall dar modellens eget
`observation_id` avvek fran begarans. `stated_primary_differs` 0,
`stated_secondary_differs` 7. Batchens fordrojning: 4,0 minuter for 1 800
begaran, 1,4 minuter for den enskilda omkorningen.

### P1 = P2 — tva matningar som inte stammer overens

De tre passen behovs for att median kraver tre varden. Argumentet vilar pa hur
ofta de tva forsta passen ar lika: ar de lika sallan, ger ett hoppat tredje
pass fel resultat i nastan varje ruta.

Talet ar nu matt tva ganger, under olika betingelser, och de stammer inte
overens:

| Matning | n | Leveransform | intensity p1 = p2 | confidence p1 = p2 |
|---|---|---|---|---|
| tidigare | 610 observationer | batch om femtio | **15,6 %** | **13,0 %** |
| 2026/315, 2026-11-12 | 600 observationer | en observation per begaran | **35,3 %** | **28,2 %** |

**Bada talen galler, inget av dem ersatter det andra.** De ar matta under
olika leveransformer, och `--en-i-taget` ar en matvag, inte en beslutad
leveransform (se FYND 009). Vilket tal som beskriver instrumentet beror darfor
pa ett beslut som annu inte ar fattat.

Den nya siffran har **en matning** bakom sig. Enligt regeln fran 2026-11-10
bar den darfor inget omdome och ingen multipel, och ingenting i den ska
beskrivas som en forbattring eller en forsamring. Vad den ger ar ett skal att
mata om.

Riktningen pekar at samma hall for bada talen, och at det hall som gor
argumentet for tre pass starkare, inte svagare. Det ar en observation om tva
tal, inte en slutsats om instrumentet.

Orsaken ar inte undersokt. En oprovad gissning, nedtecknad enbart for att den
som mater nasta gang ska veta vad som redan ar tankt och inte visat: att en
observation som bedoms ensam, utan fyrtionio andra i samma svar, klustrar
hardare pa runda varden. Ingen matning stoder det. Det ska inte citeras som
forklaring forran nagon har matt det.

Nasta matning bor ta bada formerna pa samma dygn, annars matar den bada
sakerna pa en gang igen.

### Sjalvoverensstammelse over de tre passen, 2026/315

Spridningen mellan passen ar den storhet hela konsensusargumentet vilar pa:
majoritet pa tillstanden kraver att passen varken ar identiska eller
oberoende av varandra. Detta ar det forsta skarpa v3.3-dygnet, matt pa
**n = 600** observationer som samtliga finns i alla tre passen.

| Matt | 3/3 lika | 2/3 | 1/3 |
|---|---|---|---|
| `primary_emotion` | 526 (87,7 %) | 73 (12,2 %) | 1 (0,2 %) |
| `secondary_emotion` | 413 (68,8 %) | 174 (29,0 %) | 13 (2,2 %) |

Parvis lika `primary_emotion`:

| Par | Lika | Andel |
|---|---|---|
| pass 1 mot pass 2 | 549/600 | 91,5 % |
| pass 1 mot pass 3 | 550/600 | 91,7 % |
| pass 2 mot pass 3 | 552/600 | 92,0 % |

Talen ar rakade direkt ur passfilerna fore frysningen och stammer med
`consensus.py`:s egen `primary_agreement`-fordelning i det frysta manifestet
(526 / 73 / 1).

En matning, ett dygn. Enligt regeln fran 2026-11-10 bar den inget omdome och
ingen multipel, och den ska inte jamforas med en agreement-siffra matt mot
referensen — det ar en annan storhet, och att blanda ihop dem ar precis det
fel som publicerades och fick dras tillbaka.

### Kostnad — utfallet, och tva formler for samma storhet

Dygnet kostade **$9,32** mot estimerade **$8,11**, 15,0 procent over per
begaran ($0,005179 mot $0,004505).

| Post | Tokens | Kostnad |
|---|---|---|
| output | 603 330 | $7,54 |
| cachelasning | 4 339 188 | $1,08 |
| input, ocachad | 274 965 | $0,69 |
| cacheskrivning | 2 412 | $0,01 |
| **summa** | | **$9,32** |

Priser: `claude-opus-5` $5 / $25 per MTok, cachelasning 0,1x input,
cacheskrivning 1,25x input, allt till Batch API:s halva listpris.

**Modellen skrev mindre an vantat, inte mer.** 603 330 output-tokens pa 1 800
begaran ar 335 per begaran, mot de 387 per rad som star matta 2026-11-05. Per
begaran gick det at 2 411 cachade tokens, 153 ocachad input och 335 output.

Estimatet $8,11 ar batteriets `kostnad_usd_per_verk` fran 2026-11-10: 150
begaran under samma leveransform, uppraknat linjart med 12. Fragan ar vart de
15 procenten tog vagen, och svaret ligger i att **`tools/calibrate.py` bar tva
formler for samma storhet**.

| Formel | Var | Raknar cachelasning |
|---|---|---|
| `kostnad_usd_batteriet`, `kostnad_usd_per_verk` | den skrivna posten | **nej** |
| torrkorningens overslag | `--dry-run`-grenen | ja, 0,1x input |

Den skrivna posten summerar `input_tokens * pris_in + output_tokens * pris_ut`
och ingenting mer. `classify.usage_fields()` returnerar hela usage, cachefalten
inkluderade, sa uppgiften fanns — den gick bara inte in i summan.

Raknat pa samma grund som batteriet, alltsa utan cachelasning, kostade dygnet
$8,23, vilket ar $0,004572 per begaran mot batteriets $0,004505:

| Jamforelse | Per begaran | Avvikelse |
|---|---|---|
| dygnet mot batteriet, allt medraknat | $0,005179 mot $0,004505 | +15,0 % |
| dygnet mot batteriet, batteriets egen formel | $0,004572 mot $0,004505 | **+1,5 %** |

**Stickprovet skalade.** 150 begaran forutsade 1 800 till inom 1,5 procent.
Av gapet pa $1,21 ar $1,09 den cachelasning som den skrivna formeln aldrig
raknade, och $0,12 ar verklig drift mellan stickprov och dygn.

Samma fils torrkorningsformel, som har cachelasningen med, ger $9,27 for 1 800
begaran mot utfallets $9,32 — 0,6 procents fel. Instrumentet kunde alltsa
forutsaga dygnet. Det var den av dess tva siffror som skrevs till filen som
inte kunde det.

Detta ar formen fran FYND 004 igen: ett varde som beskriver en resurs raknas
pa tva stallen och de tva definitionerna glider isar. Det ar rapporterat, inte
atgardat — se "Kod vinner over dokumentation" i `AGENTS.md`.

Siffrorna har ett dygn bakom sig och bar darfor inget omdome om vad serien
kommer att kosta. De sager vad ett dygn kostade under `--en-i-taget`
2026-11-12.

### Forkontroll fore daglig korning — tva fynd ur miljon

Bada hor till forkontrollen fore den dagliga korningen, inte till kedjan, och
hanteras som egen uppgift.

- **`python3` finns inte pa korningsmaskinen.** Kommandot faller pa Windows
  app-alias innan Python startar. Kedjan kors genom den lasta venv:en, vilket
  ar vad AGENTS.md foreskriver, men dokumentationens kommandon gar inte att
  kora som de star.
- **`ANTHROPIC_API_KEY` finns som anvandarvariabel men inte i processmiljon.**
  Klassificeringen avslutas da med felkod 4 efter att samtliga grindar
  passerat: inget kostar nagot, men ingenting blir gjort heller.

Bada ar ofarliga for en manniska vid tangentbordet och stoppar ett
schemalagt jobb helt. Schemalaggningen byggs annu inte, men forkontrollen
maste finnas innan den gor det.
