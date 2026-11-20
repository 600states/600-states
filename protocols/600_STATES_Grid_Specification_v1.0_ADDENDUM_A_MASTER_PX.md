# 600 STATES — Grid Specification v1.0, ADDENDUM A

**Status:** FRYST TILLÄGG
**Datum:** 2026-11-05
**Gäller:** `600_STATES_Grid_Specification_v1.0_FROZEN_EXPORT.json` och gridblocket i `600_STATES_Color_Protocol_v0.4_GOLDEN_MASTER_FROZEN.json`
**Ändrar fryst metodik:** NEJ — rättar ett härlett värde som aldrig kunde vara sant

## Vad som rättas

Grid Specification v1.0 anger fyra värden som inte kan gälla samtidigt:

```
native_cell_px         [100, 100]
internal_separator_px  3
external_border        false
master_px              [3000, 2000]
```

Räkningen:

```
bredd  = 30 × 100 + 29 × 3 = 3000 + 87 = 3087
höjd   = 20 × 100 + 19 × 3 = 2000 + 57 = 2057
```

Det är inte en tolkningsfråga. `master_px` är felaktigt härlett.

Felet upptäcktes 2026-11-05 vid jämförelse av två renderare som löst motsägelsen på var sitt håll: pilotserien Version A producerade 3000×2000 med en sista ruta på 100 px och övriga på 97, medan `render.py` producerar 3087×2057 med likformiga rutor. Ingen av dem följde specen, eftersom specen inte gick att följa.

## Avgörande

**Masterns mått är 3087 × 2057 px.**

De tre konstituerande värdena står oförändrade: ruta 100 × 100 px, separator 3 px mellan rutor, ingen yttre ram.

## Varför det härledda värdet ger vika

Rutstorlek, separatorbredd och frånvaron av yttre ram bestämmer hur verket ser ut. Måttet är en konsekvens av dem. När en specifikation motsäger sig själv ska det härledda värdet rättas, inte de värden det härleds ur.

Två alternativ som bevarar 3000 × 2000 prövades och avvisades:

**Rand i kant.** Ruta 97 px med 3 px rand efter varje ruta inklusive den sista ger 30 × 100 = 3000 exakt och likformiga rutor. Avvisat: färgen når över- och vänsterkant men inte höger- och underkant. Det är en yttre ram på två sidor, vilket `external_border: false` utesluter.

**Breddad mittseparator.** Ruta 97 px med de två mittersta separatorerna på 6 px i stället för 3:

```
bredd = 15 × 97 + 14 × 3 + 6 + 14 × 3 + 15 × 97 = 3000
höjd  = 10 × 97 +  9 × 3 + 6 +  9 × 3 + 10 × 97 = 2000
```

Går ihop exakt och är symmetriskt. Avvisat ändå: ett 6 px kors genom bildens mitt är ett kompositionselement som inte kommer från dagens data, placerat på den mest framträdande ytan i formatet. Projektets grundregel är att ingenting i den färdiga bilden komponeras. En betraktare läser ett centrerat kors som en avsiktlig uppdelning i fyra fält, och motiveringen "det följer av aritmetiken" bär inte för något så synligt.

Båda alternativen lägger alltså in något i verket som inte är en observation. 3087 × 2057 lägger inte in någonting.

## Formatet

3087 / 2057 = 1,500729. Avvikelsen från 3:2 är 0,049 %. Vid export till 1620 px bredd blir höjden 1079,5 px i stället för 1080 — en halv pixel. Avvikelsen saknar praktisk betydelse och motiverar inte en ändring i verket.

Låsningen att rutnätet är 3:2 och aldrig får beskäras står kvar oförändrad.

## Konsekvenser

- Ingen kod ändras. `render.py` producerar redan 3087 × 2057.
- Inget verk renderas om.
- Pilotseriens Version A, 3000 × 2000 med ojämna rutor, följer varken detta tillägg eller den ursprungliga specen. Den förblir historisk och ska inte användas som referens för geometri.
- `canonical_sha256` i de två frysta JSON-filerna är orörd. Detta tillägg kompletterar dem, det skriver inte om dem.
