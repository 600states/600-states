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
| `stampel.Dockerfile` | Samma form, egen lasfil. Stamplingens miljo - se nedan |
| `requirements-stampel.txt` | Stamplingens nio paket pa exakt version |
| `compose.yml` | Tre roller: `uppdatera`, `kedja` och `stampel` |
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

## Stampling - egen image, tva steg i olika korningar

Stamplingen kor inte i kedjans image. Nio Bitcoin- och git-bibliotek hor inte
hemma i det instrument som laser nyheter, och en stampel intygar ett fardigt
manifest - den tillverkar det inte. Samma princip som haller urval och farg
atskilda.

| Nar | Kommando | Nat |
|---|---|---|
| Direkt efter frysningen | `docker compose run --rm stampel python src/stamp.py stampla` | ja, fyra kalendrar |
| I nasta dygns korning B | `docker compose run --rm stampel python src/stamp.py forankra` | ja |

`forankra` utan dygn tar alla dygn som har en stampel men ingen forankring,
aldst forst. Lyckas den inte lamnas `.ots` orord och forsoket tas om nasta
dygn; stampeln gors aldrig om.

Forankringen ligger ett dygn senare for att sex bekraftelser tar langre tid an
forsta blocket, och en korning ska aldrig vanta pa en extern kedja. Uppmatt
2026-11-24: forsta blocket efter ca 57 minuter, alla fyra kalendrar inom ca
5,5 timmar; en `upgrade` atta minuter efter forsta blocket lyckades inte.

Ingen nyckel och ingen planbok. Det enda som lamnar maskinen ar manifestets
SHA-256.

**Grinden sitter pa publiceringen, inte pa frysningen.** Ett fryst manifest
vars `.ots` annu inte forankrats publiceras inte, men det produceras: ett
natavbrott 00:06 kostar en fordrojning, aldrig ett verk. Grinden kors av
`run_color.py --stage site`, laser arkivets tidsstampelpost och ror inget nat.

## Lagring

Data flyttar till varden forst nar lagringspoolen har dataskydd. RAID ar inte
backup - kopia utanfor varden ar obligatorisk (1.13).

### Kvoter - regel, beslutad 2026-11-18

**Ingen ny delad mapp skapas utan kvot, satt vid skapandet och inte efterat.**

En kvot pa kedjans mapp begransar kedjan; den reserverar ingenting at den.
Det som hindrar att nagot annat fyller volymen och svalter bevisfangsten ar
kvoter pa allt annat, plus ett larm. Volymen delas inte upp; separationen
gors med delade mappar och kvoter.

| Vad | Varde |
|---|---|
| Kvot, kedjans mapp | 200 GB (serien behover 20-50 GB over 600 dygn) |
| Kvot, varje annan delad mapp | satt vid skapandet; Container Managers mapp 500 GB |
| Larm, anvand volym | 85 % |

Larmet sager till i efterhand. Kedjans forkontroll ska dessutom vagra starta
ett dygn om det lediga utrymmet understiger en troskel, sa att ett dygn aldrig
borjar skrivas och tar slut halvvags.

### Kontroller - regel, beslutad 2026-11-18

**En kontroll ska koras pa den vag som faktiskt kommer att anvandas, inte pa
en angransande.**

Ett test pa filsystemet ar inget bevis om atkomsten sker over SMB, och ett
test i File Station ar inget bevis om hotet kommer over SMB. Gar vagen inte
att testa darifran ar kontrollen inte gjord, och det ska skrivas ut i
rapporten.
