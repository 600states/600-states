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

STDERR KASTAS INTE BORT. Uppmatt 2026-11-27: verktyget kordes med en tolk
utan pytest. Pytest skrev ingenting pa stdout, felet lag i stderr, stderr
slangdes, och kvar blev en sparfoljd om listindex fran verktyget sjalvt. Ett
matverktyg som inte kan saga varfor det misslyckades ar ingen matning.

TVA UTFALL SOM INTE FAR SE LIKADANA UT. "Proven foll" ar ett resultat och
ger felkod 1. "Pytest kunde inte koras" ar inget resultat alls och ger
felkod 2 - ingen matning gjordes, och den som laser ska inte kunna lasa det
som en rod svit. Verktygets egen felkod ar fortfarande en annan sak an
provens: pytests egen kod skrivs ut per korning, oredigerad.
"""
import re, subprocess, sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
UTAN = "/tmp/finns-inte-ett-arkiv"


KOMMANDO = ["-m", "pytest", "-q"]


def kor(miljo):
    """En korning: {kod, tal, sista, stderr, last}.

    TOM UTSKRIFT AR ETT RESULTAT. Raden fanns forut som rader[-1] pa en lista
    som kunde vara tom, och da dog verktyget med ett IndexError i stallet for
    att saga vad pytest gjorde. Nu blir tom stdout en tom sista rad, och
    last=False sager att det inte gar att lasa en matning ur korningen.

    last ar sant nar pytests egen rad bar minst ett tal. En korning utan tal
    - ingen modul, ingen svit, en tolk utan pytest - ar inte ett provresultat
    och far inte raknas som ett.
    """
    r = subprocess.run([sys.executable] + KOMMANDO,
                       cwd=ROT, env=miljo, capture_output=True, text=True)
    rader = [x for x in r.stdout.splitlines() if x.strip()]
    sista = rader[-1] if rader else ""
    tal = {k: int(v) for v, k in re.findall(
        r"(\d+) (passed|failed|skipped|xfailed|xpassed|error)", sista)}
    return {"kod": r.returncode, "tal": tal, "sista": sista,
            "stderr": r.stderr.rstrip(), "last": bool(tal)}


def rad(namn, n):
    delar = [f"{n.get('passed', 0)} grona"]
    for nyckel, ord_ in (("failed", "fallna"), ("skipped", "overhoppade"),
                         ("xfailed", "xfail"), ("xpassed", "xpass")):
        if n.get(nyckel):
            delar.append(f"{n[nyckel]} {ord_}")
    return f"{namn}: " + ", ".join(delar)


def skriv(namn, k):
    """En korning, oredigerad. Stderr skrivs ut sa fort nagot gick fel."""
    print(f"  {namn}:", k["sista"] or "INGEN RAD ATT LASA (pytest skrev"
          " ingenting pa stdout)", f"(felkod {k['kod']})")
    if k["stderr"] and (k["kod"] or not k["last"]):
        for r in k["stderr"].splitlines():
            print("      stderr:", r)


def main():
    import os
    med = kor(dict(os.environ))
    utan = kor({**os.environ, "STATES_DATA": UTAN})

    print("\n--- pytest, oredigerat ---")
    print("  tolk      :", sys.executable)
    print("  kommando  :", " ".join(KOMMANDO))
    skriv("med arkiv ", med)
    skriv("utan arkiv", utan)

    # ORDNINGEN AR AVSIKTLIG. Gick pytest inte att kora alls finns ingen svit
    # att doma, och da ska beskedet inte se ut som en rod svit.
    if not (med["last"] and utan["last"]):
        print("\nPYTEST KUNDE INTE KORAS. Ingen matning gjordes - det har ar"
              " inte ett provresultat. Kontrollera tolken ovan.")
        return 2

    if med["kod"] or utan["kod"]:
        print("\nSVITEN AR INTE GRON. Ingen rapportrad skrivs.")
        return 1

    print("\n--- rapportrad, klistras in som den ar ---")
    print(rad("Med arkiv", med["tal"]) + ". " + rad("Utan arkiv", utan["tal"]) + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
