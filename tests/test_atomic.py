"""Ett avbrutet dygn far aldrig lamna ett halvt manifest."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from atomic import atomic_write, write_text, write_bytes

def test_avbrott_lamnar_gamla_filen_orord():
    d = Path(tempfile.mkdtemp()); p = d / "manifest.csv"
    write_text(p, "gammalt")
    try:
        with atomic_write(p) as fh:
            fh.write("halvt")
            raise RuntimeError("avbrott")
    except RuntimeError:
        pass
    assert p.read_text(encoding="utf-8") == "gammalt"

def test_avbrott_lamnar_inget_skrap():
    d = Path(tempfile.mkdtemp()); p = d / "manifest.csv"
    try:
        with atomic_write(p) as fh:
            fh.write("halvt"); raise RuntimeError("avbrott")
    except RuntimeError:
        pass
    assert list(d.iterdir()) == []

def test_skrivning_gar_igenom():
    d = Path(tempfile.mkdtemp())
    assert write_text(d / "a.txt", "hej").read_text(encoding="utf-8") == "hej"
    assert write_bytes(d / "b.bin", b"\x00\x01").read_bytes() == b"\x00\x01"
