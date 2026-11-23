"""Kor sviten bada vagarna och skriver rapportraden ur utfallet.

    python tools/matt.py

INGEN SIFFRA SKRIVS FOR HAND. Raden som skrivs ut klistras in i rapporten
som den ar.

Skalet star i AGENTS.md: ett tal som skrivs ur minnet ar uppraknat, och
projektets regel ar att uppmatt slar uppraknat. Felet uppstod tva ganger pa
tva dygn, bada gangerna for att rapporten skrevs i samma anrop som sviten
kordes - alltsa innan utfallet fanns. Ordningsfoljden garanterade felet.
Det har verktyget tar bort mojligheten i stallet for att varna for den.

Samma form som sajtens testtal, som stod skrivet som 42 nar det var 16, och
som sedan 0ac74ec raknas vid bygget.

Felkoden fran pytest lases direkt ur processen, aldrig genom ett ror.
Se FYND 017: ett ror ger rorets felkod, och grinden kan da inte saga nej.
"""
import re, subprocess, sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
UTAN = "/tmp/finns-inte-ett-arkiv"


def kor(miljo):
    """(felkod, {utfall: antal}, pytests egen sista rad)."""
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                       cwd=ROT, env=miljo, capture_output=True, text=True)
    sista = [x for x in r.stdout.splitlines() if x.strip()][-1]
    tal = {k: int(v) for v, k in re.findall(
        r"(\d+) (passed|failed|skipped|xfailed|xpassed|error)", sista)}
    return r.returncode, tal, sista


def rad(namn, n):
    delar = [f"{n.get('passed', 0)} grona"]
    for nyckel, ord_ in (("failed", "fallna"), ("skipped", "overhoppade"),
                         ("xfailed", "xfail"), ("xpassed", "xpass")):
        if n.get(nyckel):
            delar.append(f"{n[nyckel]} {ord_}")
    return f"{namn}: " + ", ".join(delar)


def main():
    import os
    med_kod, med, med_rad = kor(dict(os.environ))
    utan_kod, utan, utan_rad = kor({**os.environ, "STATES_DATA": UTAN})

    print("\n--- pytest, oredigerat ---")
    print("  med arkiv :", med_rad, f"(felkod {med_kod})")
    print("  utan arkiv:", utan_rad, f"(felkod {utan_kod})")

    if med_kod or utan_kod:
        print("\nSVITEN AR INTE GRON. Ingen rapportrad skrivs.")
        return 1

    print("\n--- rapportrad, klistras in som den ar ---")
    print(rad("Med arkiv", med) + ". " + rad("Utan arkiv", utan) + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
