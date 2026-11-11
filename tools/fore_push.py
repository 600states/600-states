"""Grind fore push: laser HELA objektdatabasen och faller pa det som inte far ut.

Kors fore varje push. Faller den: felkod 1, och varje traff skrivs ut med
monster, objekt, fil eller commit, radnummer och raden.

Fyra saker ar inlarda av ett verkligt fel (2026-11-11, se
docs/HISTORIK_OMSKRIVNING_2026-11-11.md):

1. COMMITOBJEKT lases, inte bara blobbar. Genomsokningen som godkande pushen
   las bara filinnehall. Nio commitmeddelanden bar agarens fornamn i tva
   manader och rapporterades som noll traffar.
2. HELA objektdatabasen lases, med `git cat-file --batch-all-objects --batch`.
   `git rev-list --objects` ser bara det en gren pekar pa; tre
   attributionsrader lag i overgivna objekt fran amends.
3. Attributionen provas pa RADEN, inte pa ordet. Orden Co-Authored-By och
   Claude-Session star med nodvandighet som loptext i AGENTS.md, COPYRIGHT.md
   och kartan over omskrivningen - de tre texter som beskriver forbudet. En
   kontroll som faller pa ordet faller pa sin egen regelbok.
4. Tillatlistan star pa INNEHALL, inte pa filnamn. En post ar (monster, exakt
   traffad text, skal). Ett filnamn vitlistat en gang ar vitlistat aven den dag
   filen innehaller nagot annat.

Ordlistan - namn, organisationer och de kommersiella villkoren - ligger i
dataarkivet och aldrig i repot. En lista over vad som ska doljas ar sjalv ett
lackage om den publiceras, och ett monster som stavar ut det forbjudna faller
pa sig sjalv vid nasta korning. Saknas filen ger grinden felkod 2 och sager vad
som inte provades. Den sager aldrig "rent" utan den.
"""
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import config

ORDLISTA = "fore_push_ordlista.txt"     # i STATES_DATA, aldrig i repot
EGEN_DOMAN = "600states.com"        # projektets egen adress far sta


def monster(ordlista):
    """(namn, regex, radankrad). Radankrad => monstret provas mot hela raden."""
    m = [
        # Raden, inte ordet. Se punkt 3 i modulens docstring.
        ("attribution", re.compile(r"\s*(?:Co-Authored-By|Claude-Session)\s*:", re.I), True),
        ("attribution", re.compile(r"\s*(?:[-*>]\s*)?(?:https?://)?claude\.ai/code\b\s*$", re.I), True),
        # Allt utom projektets egen doman. anthropic.com faller alltsa ocksa.
        ("e-post", re.compile(r"[\w.+-]+@(?!" + EGEN_DOMAN.replace(".", r"\.") + r"\b)[\w-]+(?:\.[\w-]+)+"), False),
        # \b fore enhetsbokstaven, annars traffar monstret varje https:// -lank.
        # Backtick och citattecken hor till texten runt sokvagen, inte till den.
        ("lokal sokvag", re.compile(r"\b[A-Za-z]:[\\/][^\s\"'`<>|?*,)\]]*"
                                    r"|[\\/](?:Users|home)[\\/][^\s\"'`<>|?*,)\]]*"
                                    r"|\bOneDrive\b"), False),
    ]
    # Namnen OCH de kommersiella villkoren star i arkivets ordlista, inte har.
    # Ett monster som stavar ut det forbjudna faller pa sig sjalv vid nasta
    # korning, och en grind som maste redigeras for att slappa igenom en push
    # ar ingen grind. Vad listan tacker star i AGENTS.md, med ord som inte ar
    # orden.
    #
    # Dar star ocksa vad den INTE tacker: leverantorens listpris. "Batch API,
    # 50% of list price" i site/labs.html och src/classify.py ar en uppmatt
    # driftkostnad i FYND 008 och ett publikt listpris, inte vad verket ska
    # kosta. Matt 2026-11-11: ett monster pa ordet for det man betalar ger 139
    # traffar i calibrate.py, classify.py och labs.html, alltsa en tillatlista
    # pa tjugo poster som ingen laser. En lista som ingen laser ar ingen grind.
    kategori = "privat namn"
    for rad in ordlista:
        if rad.startswith("[") and rad.endswith("]"):
            kategori = rad[1:-1].strip()
            continue
        m.append((kategori, re.compile(rad, re.I), False))
    return m


# Tillatlista pa innehall. (monster, exakt text, skal). Texten provas mot den
# traffade strangen OCH mot hela raden, sa att en post kan vara sa smal som
# raden tillater. Samma strang nagon annanstans slapps igenom; en ANNAN strang
# under samma monster faller.
TILLATET = [
    ("kommersiell strategi", "sell",
     "COPYRIGHT.md: licensupplatelsen om vad en kopare INTE far gora med bilderna. "
     "En licens maste kunna saga vad den inte upplater. Posten tacker ordet aven har "
     "i filen, och det ar meningen: samma strang, samma skal."),
    ("lokal sokvag", r"C:\dev\600-states",
     "README.md, docs/MATNINGAR.md och config.py i aldre versioner: namnger ingen "
     "person och ingen organisation, forklarar varfor kod och data ligger isar."),
    ("lokal sokvag", "OneDrive",
     "Samma skal som ovan: ordet star som exempel pa en synkad mapp, inte som nagons sokvag."),
]
TILLATNA = {(p, t) for p, t, _ in TILLATET}


def objekt(repo):
    """Strommar varje objekt i databasen. En process, inte en per objekt."""
    p = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch-all-objects", "--batch"],
                         stdout=subprocess.PIPE)
    try:
        while True:
            rad = p.stdout.readline()
            if not rad:
                break
            delar = rad.split()
            if len(delar) < 3:
                continue
            sha, typ, storlek = delar[0].decode(), delar[1].decode(), int(delar[2])
            data = p.stdout.read(storlek)
            p.stdout.read(1)
            yield sha, typ, data
    finally:
        p.stdout.close()
        p.wait()


def tradnamn(data):
    """Filnamnen i ett tradobjekt. De ar lika publika som innehallet."""
    i = 0
    while i < len(data):
        nul = data.find(b"\0", i)
        if nul < 0:
            return
        post = data[i:nul].split(b" ", 1)
        if len(post) == 2:
            yield post[1].decode("utf-8", "replace"), data[nul + 1:nul + 21].hex()
        i = nul + 21


def prova(text, mon):
    for n, rad in enumerate(text.splitlines(), 1):
        for namn, rx, radankrad in mon:
            if radankrad:
                if rx.match(rad):
                    yield namn, rad.strip(), n, rad
            else:
                for m in rx.finditer(rad):
                    yield namn, m.group(0), n, rad


def amnesrad(text):
    """Amnesraden ur commitobjektet sjalvt: forsta raden efter huvudet.

    Lases ur objektet vi redan har, aldrig med ett nytt git-anrop. Ett anrop per
    traff gor en korning pa sekunder till en korning pa en kvart.
    """
    delar = text.split("\n\n", 1)
    return delar[1].splitlines()[0] if len(delar) > 1 and delar[1].strip() else ""


def main(repo):
    # En traff kan ligga i vilket tecken som helst, och terminalen pa Windows ar
    # cp1252. Utan detta dor utskriften mitt i en rapport om en lacka.
    sys.stdout.reconfigure(errors="backslashreplace")
    t0 = time.time()
    fil = config.data_root() / ORDLISTA
    ordlista, ordfel = [], None
    if fil.exists():
        ordlista = [r.strip() for r in fil.read_text(encoding="utf-8").splitlines()
                    if r.strip() and not r.lstrip().startswith("#")]
    else:
        ordfel = ("Ordlistan saknas: " + str(fil) + "\n"
                  "  Namn, organisationer och kommersiella villkor PROVADES INTE.\n"
                  "  Satt STATES_DATA, eller lagg filen pa plats. Ett monster per rad.")
    mon = monster(ordlista)

    fall, tillatna, namn_av_sha, binara, antal, anvanda = [], 0, {}, 0, 0, {}
    for sha, typ, data in objekt(repo):
        antal += 1
        if typ == "tree":
            namn = list(tradnamn(data))
            for filnamn, barn in namn:
                namn_av_sha.setdefault(barn, filnamn)
            text = "\n".join(n for n, _ in namn)
        elif b"\0" in data:
            binara += 1                     # binar blob: inga rader att prova
            continue
        else:
            text = data.decode("utf-8", "replace")
        var = "commit: " + amnesrad(text) if typ == "commit" else ""
        for monsternamn, traffad, radnr, rad in prova(text, mon):
            nyckel = ((monsternamn, traffad) if (monsternamn, traffad) in TILLATNA
                      else (monsternamn, rad.strip()) if (monsternamn, rad.strip()) in TILLATNA
                      else None)
            if nyckel:
                tillatna += 1
                anvanda[nyckel] = anvanda.get(nyckel, 0) + 1
                continue
            fall.append((monsternamn, sha, typ, radnr, traffad, rad.strip(), var))
    sekunder = time.time() - t0

    for monsternamn, sha, typ, radnr, traffad, rad, var in fall:
        var = var or namn_av_sha.get(sha, "")
        print("FALL  {:<20} {} {}  rad {}".format(monsternamn, typ, sha[:10], radnr))
        if var:
            print("      " + var[:120])
        print("      traffade: " + traffad[:120])
        print("      raden:    " + rad[:200])
        print()

    print("{} objekt lasta pa {:.1f} s ({} binara blobbar utan rader att prova)"
          .format(antal, sekunder, binara))
    # En oanvand post ar en post vars skal inte langre galler. Den ska bort, inte
    # ligga kvar och vitlista en strang som ingen minns varfor den stod dar.
    print("{} traffar tillatna av tillatlistans {} poster:".format(tillatna, len(TILLATET)))
    for p, t, skal in TILLATET:
        print("      {:>4} x  {} | {}\n            {}".format(
            anvanda.get((p, t), 0), p, t, skal))
    if ordfel:
        print("\n" + ordfel)
    if fall:
        print("\nGRINDEN FALLER: {} traffar. Ingen push.".format(len(fall)))
        return 1
    if ordfel:
        return 2
    print("Inga traffar. Rent.")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent))
