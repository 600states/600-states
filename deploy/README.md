# deploy/ - bevisfangstens korningsmiljo

Parameterregistret 1.13 bestammer: bevisfangsten (`acquire` -> `candidates` ->
`pool` -> `select` -> `input`) ar kedjans enda tidskritiska steg och kors pa en
alltid pasatt vard, i en container med last Python-version - inte vardens
systempython. Klassificering, farg och rendering kors var som helst.

Den har katalogen beskriver miljon. Den beskriver inte tiden:

> Schemalaggaren far aldrig veta nar nagot ska koras. Den knackar pa; programmet
> laser `KORNING_START_UTC` sjalvt och avgor i UTC vilket dygn som saknas.

`TZ=UTC` i containern ar balte och hangslen, inte mekanismen.

Containern ar instrumentets referensmiljo. Se AGENTS.md, "Reference
environment".

## Filer

| Fil | Vad |
|---|---|
| `Dockerfile` | Python last med digest, lasfilen installerad med `--no-deps` och `pip check`, icke-root, ingen standardkorning |
| `compose.yml` | Tva roller pa samma image: `uppdatera` och `kedja` |
| `.env.exempel` | Variabelnamnen. Kopieras till `.env` pa varden. `.env` committas aldrig |

Imagen innehaller inte koden. Repot monteras. Imagen beskriver miljon; klonen
beskriver koden.

## Tva roller, tva monteringar

| Roll | Repot | Datan | Nyckel | Gor |
|---|---|---|---|---|
| `uppdatera` | skrivbart | - | - | `git pull --ff-only`, sedan slut |
| `kedja` | **skrivskyddat** | skrivbar | ur `.env` | kor ett steg i kedjan |

Den som kor matningen kan inte andra instrumentet som utfor den. Varken en bugg
eller en komprometterad korning kan skriva i koden; allt resultat gar till
`/srv/data`. Uppdateringen ar ett eget kortlivat steg som kors fore kedjan.

`uppdatera` ligger i en compose-profil och startar aldrig nar projektet startas.
`kedja` startad utan kommando skriver att den saknar standardkorning och stannar
med felkod 64. Det ar avsiktligt: en image som kor nagot sjalv nar den startar
ar en image som kan kora ett dygn av misstag.

## Egen anvandare, inte administrator

Kedjans tyngsta steg hamtar och parsar tusentals sidor fran frammande domaner.
Den arbetsbelastningen far minsta mojliga behorighet. Containern kor som en egen
anvandare pa varden: ingen hemkatalog, ingen inloggning, ingen annan delning,
las- och skrivratt enbart pa kedjans mapp. Dess uid och gid ges i `.env`.

Pa en Synology racker det inte att containern ager katalogerna. Delade mappar
styrs av Synology-ACL, och en uid som inte finns i DSM nekas trots agarskap.
Atkomsten ges darfor till en riktig DSM-anvandare via delningens behorigheter -
aldrig genom att ge containern administratorsgruppen.

## Inga vardsokvagar i repot

Repot ar publikt. Inga monteringspunkter, delningsnamn, volymnamn, vardnamn
eller uid:n star i nagon committad fil - de star i `.env` pa varden, av samma
skal som `config.py` anger for `STATES_DATA`. Grinden `tools/fore_push.py`
fangar Windows- och hemkatalogssokvagar men inte NAS-volymer; de maste hallas
ute for hand.

## Satta upp pa en Synology med Container Manager

1. **Tid.** Kontrollpanelen -> Nationella installningar: synkronisera mot en
   NTP-server (1.13: obligatoriskt; klockan ar en bevisparameter). Systemets
   tidszon ror du inte.
2. **Mapp.** Skapa en delad mapp for andamalet med tva underkataloger: en for
   repoklonen och en som blir dataarkivet. Valj namn som inte sager nagot om
   agaren. Datachecksumma pa.
3. **Anvandare.** Skapa en DSM-anvandare for kedjan. Behorighet: las och skriv
   pa mappen ovan, ingen atkomst till andra delningar, inga program. Ingen
   hemkatalog. Notera dess uid och gid.
4. **Klon.** Klona `https://github.com/600states/600-states.git` till
   klonkatalogen - fran GitHub, inte fran en arbetsdator, sa att varden ar
   oberoende av den. DSM har ingen git; anvand SSH eller en engangscontainer
   med en git-image. Lat klonkatalogen och datakatalogen agas av anvandaren
   fran steg 3 - git vagrar arbeta i ett repo som en annan uid ager. Tva saker
   som Synology-ACL:en ger, bada uppmatta 2026-11-13:
   - En klon gjord som root kan lamna `.git/config` med lage 000, utanfor ACL:en.
     Da kan ingen annan an root lasa repot. Leta efter filer med lage 000 och
     ge dem 644.
   - ACL:en visar varje fil som 777, och git ser da varje fil som andrad - och
     `git pull` vagrar. Kor som anvandaren fran steg 3:
     `git config core.fileMode false` i klonen.
5. **.env.** Kopiera `deploy/.env.exempel` till `deploy/.env` i klonen och fyll
   i. Sokvagarna far vara relativa till `deploy/`.
6. **Projekt.** Container Manager -> Projekt -> Skapa. Satt sokvagen till
   klonens `deploy/`-katalog och anvand den befintliga `compose.yml` (Container
   Manager hittar den och fragar - svara ja). Bygget hamtar basimagen via
   digest och installerar lasfilen. Projektet startar och stannar direkt med
   felkod 64 - det ar ratt.
7. **Roktest.** Kor testsviten i kedjans roll:

       docker compose run --rm kedja python -m pytest -q -p no:cacheprovider

   Container Manager har ingen `run`; utan SSH kors kommandot i en separat
   engangscontainer pa samma image, med samma anvandare och samma monteringar.
   Utan dataarkiv faller eller hoppas de tester over som laser frysta protokoll
   ur arkivet. Allt annat ska vara gront.

## Kora

Varje steg kors med ett explicit kommando, aldrig genom att starta projektet:

    docker compose run --rm uppdatera
    docker compose run --rm kedja python -m <steg> ...

Schemalaggningen ar inte uppsatt. Nar den gors ska uppgiften bara anropa
kommandon med jamna mellanrum; tiden ager programmet.

## Lagring

Data flyttar till varden forst nar lagringspoolen har dataskydd. RAID ar inte
backup - kopia utanfor varden ar obligatorisk (1.13).
