"""Markeet: en cirkel ur verkets fulla hojd, centrerad i bredd.

Testet vaktar geometrin, inte utseendet: att cirkeln tar hela hojden, att
den ar centrerad i bredd, och att hornen ar genomskinliga. En kvadratisk
ikon som bara ser rund ut i webblasaren ar inte samma sak.
"""
import sys
from pathlib import Path
ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT / "site"))
import pytest
build = pytest.importorskip("build")
Image = pytest.importorskip("PIL.Image")


@pytest.fixture
def verk(tmp_path):
    """Ett falt i verkens proportioner: vanster tredjedel rod, mitten gron,
    hoger tredjedel bla. Da gar det att se VAR cirkeln ar tagen."""
    im = Image.new("RGB", (3087, 2057))
    for x in range(3087):
        f = (255, 0, 0) if x < 515 else ((0, 255, 0) if x < 2572 else (0, 0, 255))
        for y in range(0, 2057, 257):
            im.paste(f, (x, y, x + 1, min(y + 257, 2057)))
    p = tmp_path / "verk.png"
    im.save(p)
    return p


def test_markeet_ar_kvadratiskt(verk):
    assert build.cirkel_ur_verket(verk, 64).size == (64, 64)


def test_hornen_ar_genomskinliga_och_mitten_tackt(verk):
    c = build.cirkel_ur_verket(verk, 64)
    a = c.getchannel("A")
    assert a.getpixel((0, 0)) == 0 and a.getpixel((63, 63)) == 0
    assert a.getpixel((32, 32)) == 255


def test_cirkeln_ar_tagen_ur_mitten_av_verket(verk):
    """Verkets kanter ar roda och bla, mitten gron. Tas cirkeln centrerat ur
    den fulla hojden far den bara den grona mitten."""
    c = build.cirkel_ur_verket(verk, 64).convert("RGB")
    r, g, b = c.getpixel((32, 32))
    assert g > r and g > b
