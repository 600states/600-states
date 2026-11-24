# Den publika sidan

Kallan till 600states.com. En statisk sida: en HTML-fil, ingen byggkedja,
ingen PHP. Sidan visar instrumentet, den ar inte en del av det.

## Vad som ligger har och vad som inte gor det

    index.html             startsidan, inklusive CSS
    labs.html              600 LABS - fynden, matningarna och vad som andrades
    state-2026-315.html    kalibreringsverket 2026/315, egen adress
    field.js               faltet och lasrutan, last av bada faltsidorna
    build.py               bygger en uppladdningsbar mapp

`field.js` ar faltet och lasrutan, och ligger i en egen fil for att TVA sidor
visar samma falt: startsidan och sidan for 2026/315. Koden lag forst inne i
`index.html`, och en kopia av tvahundra rader hade varit samma varde pa tva
stallen - FYND 004:s form i den publika vyn. Sidan ger datan, filen ritar den.
En sida behover bara `#grid`, `#fieldcv` och `#readout` i samma form.

Repot bar sidan, inte dess innehall. `data.js` och renderingarna
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
    labs.html
    state-2026-315.html
    labs/index.html
    data.js
    data_2026_315.js
    field.js
    favicon.ico
    apple-touch-icon.png
    img/state_001.png
    img/state_002.png
    img/state_003.png
    img/state_004.png
    img/state_2026_315.png

Fjorton filer, cirka 860 KB. Ingenting annat.

`state-2026-315.html` ar kalibreringsverket 2026/315 pa en egen adress, och
star med flit inte i menyn: det ar inte ett numrerat State och ska inte sta
som jamlike med serien. Det lankas fran LABS kapitel XVII och fran en mening
i startsidans Proof-avsnitt. Dygnet far inte flyttas in i startsidans falt -
`FIELD_DAY` ar dygn 001 och tre av startsidans tal raknas ur det faltet.

`labs/index.html` ar en omdirigering till `/labs.html` och finns for att
adressen `600states.com/labs` star i atta publika inlagg och gav Apaches
404-sida. Den genereras av bygget, som allt annat: den far inte bli en kopia
av sidan som nagon maste komma ihag att uppdatera. `/labs.html` ar kvar och
ar den kanoniska adressen. Mappen ar avsedd att speglas rakt
upp, sa lagg aldrig nagot i den som inte ska vara publikt lasbart.

Markena genereras ur state_001 vid varje bygge, som allt annat harlett ur
arkivet: en cirkel ur verkets fulla hojd, centrerad i bredd. Darfor ligger de
inte i git.

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

Samma sak galler `data_2026_315.js` och `field.js`.

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
