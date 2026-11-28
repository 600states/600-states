"""Atomiska skrivningar. Ett avbrutet dygn far aldrig lamna ett halvt manifest.

Alla manifestskrivningar gar genom denna fil. Monstret ar skriv-till-granne +
byt: en temporarfil i samma katalog, flush + fsync, sedan os.replace som ar
atomiskt pa samma filsystem. Antingen finns den gamla filen eller den nya,
aldrig en halv.

Kravet star i projektreglerna: "Ett avbrott mitt i far inte lamna halvskrivna
manifest." Direkt open(path, "w") uppfyller inte det.
"""
import os, tempfile
from contextlib import contextmanager
from pathlib import Path

def _replace(tmp, path):
    with open(tmp, "rb+") as fh:
        fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)

@contextmanager
def atomic_write(path, encoding="utf-8", newline=""):
    """Textfil. Anvands som open(): with atomic_write(p) as fh: fh.write(...)"""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
    os.close(fd)
    try:
        with open(tmp, "w", encoding=encoding, newline=newline) as fh:
            yield fh
            fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise

def write_text(path, text, encoding="utf-8"):
    with atomic_write(path, encoding=encoding, newline="") as fh:
        fh.write(text)
    return Path(path)

def skriv_sha_sidecar(path, digest):
    """Hashens sidecar bredvid filen, i EN form: digest, tva blanksteg,
    filnamn, radslut.

    Formen stod pa tre stallen - consensus.py for emotionsmanifestet,
    run_color.py for fargmanifestet och for verket - och tre strangar som
    maste vara lika ar FYND 004 i skrivform. En granskare som kan prova den
    ena sidecaren ska kunna prova den andra utan att lara sig ett andra
    format. A45.

    DEN BOR HAR och inte i statepaths bredvid sha_sidecar(): skrivningen ar
    en skrivning, och statepaths bygger sokvagar utan att rora disken. Den
    lokala importen haller den riktningen - statepaths vet ingenting om
    atomic, och ska inte behova veta det.

    Digesten raknas av anroparen. Steget som fryser filen har redan talet,
    och en andra hashning har vore samma varde raknat pa tva stallen.
    """
    import statepaths as sp
    with atomic_write(sp.sha_sidecar(path)) as fh:
        fh.write(f"{digest}  {path.name}\n")
    return sp.sha_sidecar(path)


def write_bytes(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix="." + path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path
