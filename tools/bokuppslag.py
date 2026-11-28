"""Sidor ur boken, renderade till PNG.

    python tools/bokuppslag.py <bok.pdf> <ut-katalog> <prefix> <sida> [sida ...]

BILDERNA AR GENERERADE, INTE TAGNA. Boken ar genererad ur det frysta
manifestet; bilderna AV boken maste vara det ocksa, annars gar de inte att
gora om nar boken andras. Ett handgrepp i en bildvisare lamnar ingen
kodvag, och den dag generatorn rattas vet ingen vilka sidor som behover
goras nytt.

PYPDFIUM2, INTE PyMuPDF. PyMuPDF ar AGPL och det har repot ar publikt: ett
verktyg i tools/ som smittar licensen ar ett eget problem. pypdfium2 ar
Apache-2.0/BSD och binder ingenting.

BREDDEN AR UNGEFAR DUBBEL VISNINGSBREDD. Sidan ar 210 x 150 mm liggande,
alltsa 595 x 425 punkter. Skalan raknas ur den begarda bredden i pixlar, sa
samma sida ger samma bild oavsett vilken maskin som ritade den.

Verktyget laser en PDF och skriver PNG. Det ror aldrig arkivet, och det
bygger aldrig boken - boken byggs av tools/bygg_bok.py, och vilken PDF som
renderas ar anroparens val och syns i kommandoraden.
"""
import sys
from pathlib import Path

SIDBREDD_PUNKTER = 595.2755905511812      # 210 mm


def rendera(pdf, ut, prefix, sidor, bredd=1600):
    """Skriver en PNG per sida. Returnerar de skrivna filerna.

    Sidnumren ar bokens egna, alltsa 1-baserade: sidan 319 heter p319 i
    filnamnet och inte p318. En lasare som ser bilden ska kunna sla upp
    samma sida i PDF:en utan att rakna om.
    """
    import pypdfium2 as pdfium
    pdf = Path(pdf)
    ut = Path(ut)
    ut.mkdir(parents=True, exist_ok=True)
    dok = pdfium.PdfDocument(str(pdf))
    if not sidor:
        raise SystemExit("ange minst ett sidnummer")
    skrivna = []
    for n in sidor:
        if not 1 <= n <= len(dok):
            raise SystemExit(f"sidan {n} finns inte: boken har {len(dok)} sidor")
        sida = dok[n - 1]
        skala = bredd / sida.get_size()[0]
        bild = sida.render(scale=skala).to_pil()
        fil = ut / f"{prefix}_p{n:03d}.png"
        bild.save(fil)
        skrivna.append(fil)
        print(f"  {fil.name:<32} {bild.width}x{bild.height} px  "
              f"{fil.stat().st_size:>9,} byte  (sida {n} av {len(dok)})")
    return skrivna


def main(argv):
    if len(argv) < 5:
        raise SystemExit(__doc__)
    rendera(argv[1], argv[2], argv[3], [int(x) for x in argv[4:]])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
