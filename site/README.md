# Den publika sidan

Kallan till 600states.com. En statisk sida: en HTML-fil, ingen byggkedja,
ingen PHP. Sidan visar instrumentet, den ar inte en del av det.

## Vad som ligger har och vad som inte gor det

    index.html   hela sidan, inklusive CSS och JS
    build.py     bygger en uppladdningsbar mapp

Repot bar sidan, inte dess innehall. `data.js` och de fyra renderingarna
genereras vid varje bygge ur dataarkivet, och ligger medvetet inte i git:

- **Bevisen.** `data.js` ar 600 observationer med kall-URL, tidsstampel och
  tolkning. Bevis publiceras CC0 i bevisrepot, inte i instrumentrepot.
  Se `COPYRIGHT.md`.
- **Verken.** De fyra PNG-filerna ar renderade States. De ar inte
  MIT-licensierade och hor inte hemma i ett repo som ar det.

Darfor star det kvar i `README.md` att detta repo inte innehaller datan.

## Bygga och rulla ut

    python site/build.py

`STATES_DATA` maste peka pa dataarkivet, precis som for resten av koden.
Bygget hamnar i `site/dist/`, och det ar darifran filerna laddas upp.
Mappen ligger i repot men utanfor git: det som ska till servern far inte
kunna bytas ut av en filsynk mellan bygge och uppladdning, och bevis och
verk hor anda inte hemma i historiken.

En annan malmapp gar att ange: `python site/build.py <malmapp>`.

`site/dist/` blir exakt det som ska ligga i `public_html`:

    index.html
    data.js
    img/state_001.png
    img/state_002.png
    img/state_003.png
    img/state_004.png

Sex filer, cirka 416 KB. Ingenting annat. Mappen ar avsedd att speglas rakt
upp, sa lagg aldrig nagot i den som inte ska vara publikt lasbart.

### .htaccess ligger bara pa servern

Den finns i webbroten men inte i bygget. Ladda upp genom att skriva over,
och anvand aldrig en synk som raderar filer som saknas lokalt - da ryker
den. Efter utrullning ska `/.htaccess` svara 403. Svarar den 404 ar den
borta.

## Byggstampel

`index.html` bar `<meta name="build" content="dev">`. Bygget skriver in kort
commit-hash i stallet, med `-dirty` om tradet hade oincheckade andringar.
Da gar det att lasa pa den utrullade adressen vilken version som ligger ute
i stallet for att gissa.

## Tva saker som biter vid utrullning

**Versaler.** Servern ar Unix, Windows ar det inte. Mappen ska heta `img` med
gemener och filerna `state_001.png`. Fel versal ger fyra trasiga bilder bara
pa servern.

**Cachen.** Loopias korttidscache behandlar `index.html` och `data.js` var for
sig, sa en besokare kan fa ny sida med gammal data. Andras datan, hoj
versionen i taggen samtidigt:

    <script src="data.js"></script>  ->  <script src="data.js?v=2"></script>

## Faltet ar en canvas

Rutnatet ritades forst som 600 DOM-element med CSS-gap. Det gick inte: en
separator pa en CSS-pixel blir mindre an en enhetspixel vid dpr under 1 och
avrundas bort pa enskilda kolumner, och Chromium lagrar layout i 1/64 pixel
sa felet ackumuleras over 30 kolumner. Matningen visade 20 av 29 lodrata
granser borta vid dpr 0.9.

Canvasen ritas i enhetspixlar, dar alla koordinater ar heltal. Matt pa malade
pixlar ar nu noll granser borta vid dpr 0.9, 1, 1.25, 1.5 och 2.

Faltet observeras med `device-pixel-content-box`, inte bara storleken i
CSS-pixlar: en andrad pixelkvot som lamnar CSS-storleken orord ger annars en
inaktuell canvas, och da hamnar varje linje pa en bruten pixel igen.

Tangentbord och skarmlasare kor genom 600 dolda knappar som driver samma
urval som musen. Canvasen ar `aria-hidden`.
