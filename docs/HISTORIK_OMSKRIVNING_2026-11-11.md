# Omskrivningen av historien, 2026-11-11

Repots commithistorik skrevs om den 11 november 2026. Filinnehallet rordes
inte. Det har dokumentet finns for att varje citat av ett gammalt commit-id
ska ga att sla upp, och for att sommen ska vara dokumenterad i stallet for
dold.

## Varfor

Repot ar publikt, och ett commitmeddelande ar lika publikt som en kallfil.
Regeln i `AGENTS.md` under "This repository is public" foljdes i filinnehall
men inte i meddelanden. Uppmatt over alla 115 commits fore omskrivningen:

| | antal |
|---|---|
| meddelanden som namngav agaren vid fornamn | 9 |
| meddelanden med en `Co-Authored-By`-rad | 72 |
| meddelanden med en `Claude-Session`-lank | 23 |
| meddelanden med arbetsgivare, e-post eller personlig sokvag | 0 |

Tre `Co-Authored-By`-rader lag dessutom i commitobjekt som ingen gren pekade
pa. De gick bort med `gc --prune=now`.

Genomsokningen som skulle ha fangat det har fore en push last bara blobbar och
hoppade over commitobjekt, sa den rapporterade noll. Den lardomen star som
bindande regel i `AGENTS.md`: en genomsokning som inte laser commitobjekt har
inte genomsokt repot.

## Vad som andrades, och vad som inte gjorde det

Bara meddelandetexten. Verifierat pa den omskrivna grenen:

- **115 commits fore, 115 efter.** Ingen commit ihopslagen, ingen borttagen.
- **Alla 115 tradhashar identiska, par for par.** `git diff` mellan gammal och
  ny topp ger noll byte. Inte en byte filinnehall har rort sig.
- **Forfattar-, committer- och datumfalt oforandrade**, rad for rad.
- Efter omskrivningen: noll trailerrader, noll session-lankar och noll
  forekomster av fornamnet i hela objektdatabasen.

Orden `Co-Authored-By` och `Claude-Session` forekommer darefter bara som
loptext i `AGENTS.md`, i `COPYRIGHT.md` och i det har dokumentet, alltsa i de
texter som beskriver regeln. Grinden ska darfor prova RADEN, `^Co-Authored-By:`,
och inte strangen var som helst.

## Citat av commit-id

Citat i FILER pekar om till de nya id:na. De rattades i en vanlig commit
ovanpa omskrivningen, inte i en andra omskrivning:

| fil | gammalt | nytt |
|---|---|---|
| `AGENTS.md` | `f80494a` | `e31ce22` |
| `src/run_state.py` | `b6aeab0` | `8f065a8` |
| `site/build.py` | `9a1f3ba` | `831632f` |
| `site/labs.html` | `f32bd75` | `11f7b66` |

`tests/test_rent_trad.py` lamnades. Strangen `53cf395` dar ar ett argument till
`gate_rent_trad`, alltsa ett provvarde, inte en hanvisning till en commit.

Citat i COMMITMEDDELANDEN star kvar doda, med avsikt. Att ratta dem kraver en
andra omskrivning, och den andrar alla hashar igen. Kartan nedan ar svaret pa
dem i stallet.

## Kartan

Alla 115 commits i rev-list-ordning, aldst forst: gammalt id, nytt id,
amnesrad. Commits efter den 11 november 2026 finns bara i den nya historien
och star inte har.

```
1718891a5a6a63f3fc87fdcde6bd85cf468dc6b2  9f64e4576da0794e813442096ffcbf8ef802a88e  Initial: GDELT-laddare, aterskapad evidence-hash, join-kontroll
cd14bfd1313a0a715747d98b4fcf616233b3c7b8  8cd7df4b20e1518575cbb3c2d3f0a11c8cb55e90  Verifiera att git fungerar efter stadning
48e54d52fbcc1d469487688643b168938480ab0b  fff8226ed2c33bddf4845c6de9518fc06e38d8a3  Dokumentera natverksblockering for forvarvslagret
b546507882b5171e6aab461d53d7baa767259be8  76e2293fc393c9390d466b9b0b338b35be63479a  Nedladdningsskript for GDELT Events (kors utanfor sandladan)
b224e6520371d08b5b6ab99ef623e76298366216  0231daa16ddf56b502ccb8b868a3d94091cbee11  Events-data pa plats: GDELT 1.0 dagsfiler, geografi aterskapad
cbccf382c9ac0f41ca94c7681f568eecdd4cb63a  0f3a971fcac1b57c576a7c37de4a61aed794b1ac  Bevisfangst: hamtare med domansparr + lankrotsmatning
764a61cf0d1c9b45be160de96520cce8cb470127  4fbaf8ba8ad234cf59f94f419bf6006727980ab9  Bevisfangst kord skarpt for State #001 (600/600)
5ab79c656b6a5f7d6abc241e4b93a15d2017bd7d  bbdd0b6e6b9f63321abb6d2dca0552be525d1117  Lager 1: kandidatbyggare med geografi och regionkarta
617f703e59e48ed6d9cfc83403cf4d8f07e85e74  3415a62ce1d2bf6529a365ccee1d4201a5ff4e77  Lager 2a: kandidathamtning med matt recall
465b0f88c6b3939f13de6b3ff776e7dd00fbb460  6d3bd0f84659e8672da859e23a50d4dd22d8a1f7  Rangordning: omnamnandevolym som trattningssignal
14d13785eaef09571f80e65f7024b5cba8fd758d  926c2cdc05aea27229d687b6684210a6a0167a9d  Klustringsmetod avgjord: lexikalisk pa rubrik, inga embeddings
008c09b7bb9213c2722cd91f8c269a1555fa3d87  4fb089274edd19514114f72eb0bd83783d41f1e9  Storytak: deterministiskt girigt tak ersatter materialitetsbedomning
e33da8f936ca656e363908ce3d04e61692ac7808  3a968e459ec7608044f8d594e0d1b3aebfc7ded1  BESLUT: N=1, troskel 0,25, gransband 0,20-0,25 loggas
d4afe6ab5af0d1c393cbf6a851f504c962a3765c  a56d8b8ae4756e7a29b2f171867d349965690907  Kvotmotor klar: #001 frusen med 600 rader under v3.0
b4c108889e7cb29ad5837dd1c4b4b431f677b1c2  2ff6bd19e2c69896f16064aa9448d73115707dc8  Bevisfangst: ratt kallregister, subdomangrind, reparationspass
f49468e798619891085843929fad4fdc5fc58c36  8629e28b4bebb9442a0f10b925bcf42b1cf69dcd  Klassificerarens input blir kod: build_classifier_input.py
100174aaf9e6d9c1af8d46e6c6223e5f1275f1a8  b4654049b5e827720208a64efade1fb5f40ab78d  En runner med grindar: kedjan kan stoppa sig sjalv
53d45cae35b51a89517f53b9b24e62485e5122cd  6c21822afd71c7dec3707ba6b4c5707519f519a3  Konsensus blir kod, och hela kedjan har kort skarpt for 2026/001
ae1c40ca4755c100a823b14e33125d2a03f89026  b375514411eca34eacf89e646b89fec4e3f4326e  Sammanfattningsartiklar ar inte en observation
0598f2678b92512263617319b123ca0de6392df2  a06fefaf8b62580e6ed3e13be0f4e9e54262ba0e  Grind: ingen sammanfattningsartikel far na klassificeraren
19387eacfa1b6f04667c5e6d31de8663b453eae8  28fc20b7da2e2d78f3de7c29e94ba0bebf38ecfa  Revisionsskript: audit_state.py
ae60504116db38b326d0ff555607291b478f7116  1409fda7c57dcb12ab98d3eee6ae8a42005d0f05  Sajtens datafil byggs av kedjan: build_site.py
7fde5d297c65e9ddd95f0d46cfeb85342c51c52c  cde2eacc660e6695a34caadeef825eb3ab680e8e  Kallregistret har EN definition: config.REGISTRY_FILE
fc11eb7bf0fdf3755f8f77c7f9c3c59d0f2bbef5  b3a279561279516c3a7fdf040353537d1caa4241  Grundplattor: statepaths, atomic, och tester for besluten
d8459f008dad4df909d270f0987bc38472b3536a  e6e2795d0953961d1ef0de50cb125f39c736b1a3  Urval och farg ar tva program. Separationen ar funktionen.
e9eea7a8c3d847daa6c6d5c271acad1e16b24616  81b737f175a59c2c9b0576e865380b05b71344fd  Licens och publik README
aa36993b1028eaf441f5b8c17935d977640db33c  5cf72bc9e67b1b8f14fa7e1e2d6710f64149dc8a  Inga personliga sokvagar eller adresser i koden
9acf127e82a284b40ce7a6991d2106a2a234c051  56bbd76df31d81abc0eed77f048113c267762d2e  Testerna hoppas over utan dataarkiv i stallet for att krascha
37e7d30391cc816e6c605e5aafd59e35559669da  3295f5f5a3cf5e0549503bb10b13e9604835cdaa  Inga lokala sokvagar i dokumentationen
77b3d94f1ec6a013b0a83852d120965334c26819  6713c1e0e8f7a7e4707a04dc509621d4baf5eb0c  AGENTS.md: reglerna star i repot, inte bara i nagons minne
b5a667d467743ce6ea3bf4f099183eedaee3549f  20ec9369f0fef532f08e3b7b48bc8dfdf1774e88  Tva regler som saknades: ful output och spar barheten
57b6ee62ad94d91f62d4dcd1d0e8a85123421b33  85d39d69b47c9cf0d86a6e443a982953fcb1cc40  Masterns matt avgjort: 3087x2057
e17ebebd9e1e3bda74bc72ce1fab60efbd986794  e5aa3e8b176dd30059b75a7d12de86435127c414  Forvarvssteget: ett dygns raflode hamtas och fryses som snapshot
bb51df5d157734499193c9f612a8e3d66fd9a141  e2f8d5a232d2a430984f5ad989a734c306fddf35  Klassificeringssteget: kedjan anropar API:et sjalv
650f88dba0e2b2fecfe076316be91c323d199e44  8f19d06821612efe345469c9a1cf7e23dd12599d  Sidan in i repot: kallan i git, innehallet ur arkivet
a55f16a422cb634d60cedebac49a7f39ec767887  6229f41379bd5e0caa3fbcc4a9bd2f7e846cce15  Granskningsverktygets skarmbilder ignoreras
b8190b412b0f99c2b39555e964e06d906adabc48  08148c12e155b323ba03feeffe766faedbee1ec3  Radslut normaliseras: .gitattributes
67d345ba24afc3e5ef916ee9583f30048259bcee  ad0a0f33440af971dfda18c10d1dfcae16a0e322  Bygget hamnar i site/dist, inte i en synkad mapp
5dd6cee6053c8a2acc7163fa198ab377fc6ae125  ac5160e1a3a5b06df15072b5b3ea82ea7d272d99  Beroenden i venv med lasta versioner
17dd3b5ee6fcefc82179df4cf0d5464d08160919  dd001da890b7545817c93463ae8ac479c988d147  requirements.txt ar provad som lasfil, inte antagen
f80494a9184a58110bdd60f3432d017a38359d95  e31ce225189fcb287180a3536a79a42d19d44bc9  Ratt specversion i consensus.py
b026202de2d29cbd19d8d06a0ba81603a20a49fa  bdb795ac3e4c02806ab78459e823ef80dfaf6c29  Tva olika v2.2 star nu bland de kanda divergenserna
96282c118599622717369119ffdf8fbd114c38ae  857d66377054ea2c7c4c64ca304cab9c6784aea2  Misslyckade anrop lamnar nu spar
fc90b80a0c778126cbef359ea697412f6b1bcd1b  b7a53c7059a20a8d9e47736c2dbc11c53eb83858  Taenkandet avstangt - en instrumentparameter, inte en instaellning
25dc69a02f28ff82cfa3efb4869cb57b3a2a2c48  8ae3b88b5637548f3dbaa0cfc691a8c60e3698f4  Taket ar en matt storhet: 32000 output-tokens
acdbe88992bb2c2701e0fb9cc6885e3374f33ac5  b0c93365082a1e69a6dfceefbb2770325baf3bfd  Stroemmat anrop, och omforsok bara for fel som skickades
e7b4373719ae2dea67eadb5a69a54e4c468c6df8  f84a5c8548682e6d538019483c87be23207e00dc  Valideringsmiss lamnar nu lika mycket spar som ett undantag
d85b7fc72b9fb8ac6d34db275a7e06a8b905658a  bc7885b204032354cc8043c0eff7eae82b751f59  Tomnamnad nyckel stryks, primary och secondary harleds
f71ca589d775850d403812f1a6574cdadefe398b  486f26a3a1275d9833620bab3c0e9de1cc8f00f6  Parsningsfel raknas per batch och per korning
dba392171144476e59ef76c5504cc48acbe0c792  59973891b79ceffcd78f0e147085a427fe4652d8  Korjournalen skrivs pa varje utgang, och vaxer i stallet for att skrivas over
3d674a97adfcf8f949544fc1b59ef6f75566d9b8  f2fac4052a122fce5d183030f6b3a6d540cea44d  Journalen sager vad den inte tacker
445b2b3818c30ee24d029d1a97152273bb5c9d5a  80670033f8db69a28eef80995969bfe80b2da5fa  Batchstorleken lases ur specen, och modellen far inte hitta pa rader
5ebe6fbdaf86fef388493b02ce9c33ee15c8770b  5fb0c92a845738150c1d2e3d930e45dfbadacc7a  Overskott kastas och raknas, underskott faller
9261520e62fd711e00901ff416c069ef120a2a39  8e325b1a5eaf455fa4c440a3558723ddc518b7f6  Fyra krav utan efterkontroll, hittade i en oberoende granskning
ef5c65bf20a5c8983110fd044ec1dd3c616f384e  0ea636eb9ab98436aecffcc8ba790e4aad990c83  Stympade observation_id aterstalls genom uteslutning, aldrig gissning
cb9a4939913ec49a36d9b7469553cad9d874eda9  84e7677a6c7ce4f0a7fe574eb3f3558ad314cd3e  Kalibreringsbatteriet: samma sextio observationer, for alltid
2f21684bfeb0517946f10fe61fc35f272750def8  cff6a288dab8314ff84ee2326caf3e4ab6366e04  Taenkandet ar per modell, och ett 400 kors aldrig om
71607cd51afade3abc21ffb6999d4e63be9f6484  064125ff72250e1450b3acffb127f1d6bd329b40  Grinden harleds ur specen, inte ur ett observerat snitt
7afa5fcbc5d24010d77b1978361e57dc72afc32c  8d221d7f2bae2893aa27a9b3beb38aa85359b4f5  kalibrering: MAD over passen, slut pa overskrivningen, rattad docstring
4ad7fa45ac31ebc7fb74a59c013536b0189538ac  de9db59dcedaf80c904d93f0c4a4240fe8872d0a  klassificerare: effort skrivs ut, opus-5-5 utesluten med skal
a620302f0abe290a14052a3e7d2205f516194fe4  de19f5f39c51823166c6dace0db1c9f5baefd3e7  grind: kvantiseringsforbudet provas, haiku faller pa det
62d011aa8327034d3d262ea4a2fc61ec789a91ce  0fa921055d22b4f334d2b9b8b89c3e55542100b5  grind: en dag, en korning, ett utfall
7e0dc43294e1935775588f3e5d6f254158ef011e  464d231f39ea54db04a3c29f4935c8ec1509e3ab  site: 600 LABS som egen undersida
f32bd75977ec896910ec512db1aa8ce6f6d8df9e  11f7b6697bdd089a8bf8cbc56be277dffc9272eb  labs: harfina linjer bort, mobiltoppen och vansterkanten som pa startsidan
d584493e3d2c47a9bd765756c256180aa4d1b737  6d6f68f78e8362b55e27ddedef7c413f4499b792  labs: tyst undantag for cramped-padding, med matningen som skal
d403e16a485a831980b06be532759eb863262a93  81b1bcad4b2907c18dfc0709b49676f2bcdeec46  labs: kriteriet for de atta kvarstaende traffarna, dar det lases
cc74c44fa4ba96edbe0a9c34505615c39fbd34d4  57a0c836d4746ec1fc5dc15f051d835b88d1be5d  bygge: sidorna skrivs med LF, inte med byggmaskinens radslut
bba818619bb7f35162c363a8d7bbfce834e29014  ccf803718483e398a445ef8c6b802205b761630f  site: verket i labs hero, och menyn klistrad pa bada sidorna
663f8dc1ab93b4ed78e8ee88e73ada71aecdf0bd  f75f219fa36530a4faef8af79dd5550510df1d20  labs: elva blir tio, for listan har tio poster
632a6498ffca3fc7565f91660aba8c251376d7f5  f65ae07e9d9e811283ba0c0585c9b2850acb482e  labs: verket bakom rubriken, och siffran i hjalten grindas
e1eb881214d0908e37f818c85fa6f980d9d86efc  54aaff8fb171443dac108837c3ac6874e5953acd  labs: verket beskars inte - contain i stallet for cover
f180e1ad9e8dc4597f3f2249e0035a011ce1e7ef  0547bff6063fa177f43d77af5ad65e3fe46ee0b6  site: logotypen lankar hem, och ett marke ur verket
f3899a7a7583df6e11118ed81cb3875ae4612ab0  13a23ea539e7361ad647c515e176d0456b368433  labs: skalet till att det vita faltet spanner IX och X
f46291a45754c7402960dae47a1744494b9a4abb  0bb01ec277dc8ac811791e0b95b7a7d95fa78cee  site: mobilmeny pa bada sidorna, och inga viewport-enheter i hjalten
d44e504bfc06e6eb9d88e4b6351e7c5f8da44905  812baf7ef0d8ec49831e1fa1300e75304b948187  site: hjaltebilden matas ur verket, inte ur rutan
5f2743cde951949e32bc9d2a752febddcbb72699  22a67bd5c902d36e7b6f4e6336bd49afa68d87f4  site: verket far inte vila pa att ett skript gar igenom
917bc3f206da5e3ce216dbf073c0d8c84b477744  5a22fbaee2f9bfa2d48ea3b97398c96ebf2e9677  site: tva animationer pa samma ruta, och den ena slackte verket
43d2c47bbdcb148920afcc644156e8676bb3a26f  22e05c3720bd985b89ec04cbb5b96b4ae92c5a9b  labs: frysningen fixerar verket, den skapar det inte
7555d313a09aef659e2f69bbe49fee4d3fa1d7f6  b7558b6e13ca6ae3bedc29ecda56046a8cc890f9  labs: kapitel XI, miljon som dolde felet - och testet som last fast ett tal
b429cf18e8d885dc5f949fc58161b7a1d43762d1  c1532a9859bce07f4c7b7df2f46175e5440c6562  labs: kapitel XI tillbaka ut, det horde inte hemma pa sidan
9a1f3ba98e1a1d4df9155330bc032cf72c3cece6  831632f13e26bc068342b42da605159d4da63738  labs: tog bort en overbliven </div> fran aterstallningen
53cf395f154a1dc6ea592de15184ff33889c4625  99496a9f4c771f1fc3f6258204a09e4e64eb6b19  labs: lank till instrumentet, nu nar det ar offentligt
0bb2c67648606b26dd2617187665b16bc26cf0db  743fa55702cbae90c7b406519fc49b9d86d735e9  build: vagra bygga dist ur ett smutsigt trad
d88a9e931aee620247402510ce586029a6e58321  fc84f8f42c9d3e2121c31e24e13bd037f6a9837f  kalibrering: temperaturen blir matbar, och journalen kan inte ljuga om den
9bea929458f06c1d36a83b6174b69d6e374cdeb1  73be277b9f46fd96d6369669251ec8484ec60eb1  temperaturen finns inte, och en matning raderade en annan
2f11332193772bea2a72d7835cb760fd7d04ac5b  d519bfe74a68692792eee6d58cc9daeea7f49628  labs: kapitel XI, parametern som inte fanns
f33549800285dbb04fb63ff33b7f998346054267  a489a7517a57dbe184d29598b1aab4c9ebc5ea7a  labs: kapitel XI:s tabell foljer sidans mobilform
2a2ccd4de26fe4f24ee38332ca707b5895f4ef83  c2a5883441b702ec032a73bfec28fd909ec96bc7  labs: talparen i kapitel XI bryter inte mitt i sig sjalva
4b0c60467332c3fec968b6ce17200060d49da0c3  8718df9d3f358975ea6a279e255c846994c7826c  leverans: Batch API, som beslutet sade sedan 2026-11-06
f4713df8d3a6edd7c9fc11092b8433e00c12ed38  6c006fee08f7c45ba9ec1e2ec31a97ac027ee32e  matvag: en observation per begaran, for att mata FYND 009
b2005ab37db3fea21a4a6c481f80ae2e2d675d94  446f62fa687d086c6f5d6f6e4f9e66e8115749fe  ett slappt jobb ar inte ett haveri
2e339fbca4065b6cf0b9eb90173edee0fb58812b  0d07e6f8ecda65a0583703b8918e22997df08b17  indata lases en gang, inte en gang per svar
d80c19df2a4d331adca0462338ab00542060f2d2  1a12d70cdb74fb930d6e17b33483fba555292a91  kalibrering: batteriet kan koras med en observation per begaran
a9b6af6bf60f1f8b56b587dbd83772c145b9045d  caf10abee927f6eb4108457ff25958d356c159db  labs: kapitel XII och XIII
507ba7977fa0a967849054f8429e9dc9b175c52f  964e721799df551b3d1289dac1ae68d6c3ad5b18  labs: brusgolvstabellen i kapitel XIII foljer sidans mobilform
96555a1c72d6171c1edba70b28c327adb9bcfe56  028a4f3940213c8adf0416b0a12dc9afba02f697  labs: talkolumner far vanstermarginal
edf65526db842829b9653b5a2b284bc093100cef  4ecf871193e08a4cb2ae96cd5a0b17f0a4239470  referens: bygg en ny under den beslutade formen
39596a4e3f711dcca9945ae6c2dbf2eab1e42198  d980b1741c8b281414d4c359bed62973f838a477  labs: rattelse i kapitel XIII — tva matt som inte var samma matt
23347cc0bb2a05a36bd09822a98b5e1b7de0125a  643757d47dc3a88ade07e2cd5870f3e9e616d2d0  referens: testerna provar beteende, och tva tysta luckor stangda
357172f6a31445a48751f54ffc19cdcf487b49f1  c6df4866dcf0b224ac2cec71c3826ef9f0352852  AGENTS.md: ingen granskar sitt eget arbete, och ingen siffra pa en matning
f30a36db27d391f5301c717d2e4cb5e7ac7f2c3c  bc4ba114d70164dfe5d8fdba3a8fcfe445bcdcef  test: tackningsgrinden ska ga fore anropen — faller med flit
b6aeab0777794a4770ae4bae9dee4d5d5b486e36  8f065a896ed71e4876bae2ee811e0ba7685ad79d  kalibrering: tackningsgrinden flyttad fore anropen
91a11e21b746a8568723f78a4f66de85ab60c141  1150757e452319bdb4ae8210a6e49488cb30b8d8  labs: kapitel XIV — tidsstampeln som dog vid frysningen
8eb3a206530eb620638291a0bec5601922193c14  fe0f3958afc2b4253f5a5d9eff3f1ebf39a7e81f  bevis: tidsstampeln foljer med in i frysningen, och grinden gar fore
1994cb8a349d3a8671451503b7df227b8d6cb3d8  615092808dfc070c880cc9747ec033ec83e65ed2  test: bevistiden ska overleva frysningen — acceptanstest for FYND 011
0fee6c6bfaf8fc7289de6b2b5738bdf1d93f266a  b63e8cf3ae0e636ad08b7262163c6bb8b56613e3  labs: kapitel XIV — matningen, noll OBSERVED_AT_CAPTURE pa tre dygn
d7ead28e4d2a8b270e61dd3234c8b22a060c904d  45759567b28b4d4ad08782eec15494d267350741  manifest: v3.3, for formen andrades — skrivning far V, lasning far dygnets fil
8d04ccd9254bbb67edf72f1b4597ebab11892c4e  e747cdc77e7c14daf2a8bac68d53e123cbe3c347  statepaths: frozen() sager vilken form den laste, och stannar vid tva
fe701de229a225d84f16dac2f4eed621f990a42a  fe68e91c698f523c6d8ff2c526ff0f25a1f4dbab  test: lasvagen ska saga vilken form den laste — acceptanstest
effd5dec560538611dbedb56f7c73b1ea4cedcdf  7c7233818893c54d00bbfe3b0fd7e7830fc3b264  bevisnivan: ett fonster med tva sidor, och bada talen pa ett stalle
cce25fbab9032bc31755d822843e11c0a54dcd0c  0b6bd5b8364f87ea6c5902d5d3f128bada29acea  test: fonstret har tva sidor — acceptanstesterna foljer nya gransen
bf23368cf9788ba78ad9f83336f3d11d672848ae  6f1a1682396d3a406e051ce4d78d00613382b00e  labs: kapitel XIV — rattelse, fonstret har tva sidor
8d515724e78a4628ceae3612ce403ef6424b2ca4  838b8a6e716aaef7bed9ca1d61f85b30cd4b2230  grind: ogiltiga rader, inte forsok — ett omforsok som lakte ar inget haveri
8c684a15355d4943c3bdb8022f574d3e8cca9841  26bf5196ff0fc8632e28e407188a2949330053f1  test: grinden ska rakna ogiltiga rader, inte forsok — acceptanstest FYND 012
d5914ddb9bdf057cd5767f208a9430d59c5ef1c9  a83c5f70ed267411785926521255de1f854f11b2  labs: kapitel XV — grinden som raknade forsok
```
