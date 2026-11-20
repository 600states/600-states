"""Grindar for sviten sjalv: att pinningen inte blir en attrapp som provas.

Skrivet av den andra parten an den som byggde riggningen i aae056d, enligt
AGENTS.md.

conftest pinnar tva arkivlasningar sa att 31 tester om helt andra pastaenden
gar att kora utan dataarkivet. Det ar ratt. Men ett pinnat varde ar ett varde
som ljuger pa kommando, och den som lagger till ett test om just det vardet far
ett gront svar fran attrappen i stallet for fran specen.

Risken namngavs i rapporten for aae056d. En risk i en rapport stoppar ingen
korning. Harr ar den en grind.

Testerna laser svitens egen kallkod. De provar inte vad koden gor - de provar
att riggningen inte kan bli osann utan att nagot faller.
"""
import ast
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT / "tests"))

DENNA = Path(__file__).name
PINNADE = ("spec_precision", "PROMPT_FILE")


def svitens_moduler():
    return [p for p in sorted((ROT / "tests").glob("*.py")) if p.name != DENNA]


def _trad(p):
    return ast.parse(p.read_text(encoding="utf-8"))


def _namn_som_importeras(trad):
    ut = set()
    for nod in ast.walk(trad):
        if isinstance(nod, ast.ImportFrom):
            ut.update(a.name for a in nod.names)
    return ut


def _setattr_mal(trad):
    """Varje monkeypatch.setattr(X, "namn", ...) i modulen -> namnen."""
    ut = []
    for nod in ast.walk(trad):
        if (isinstance(nod, ast.Call) and isinstance(nod.func, ast.Attribute)
                and nod.func.attr == "setattr" and len(nod.args) >= 2
                and isinstance(nod.args[1], ast.Constant)
                and isinstance(nod.args[1].value, str)):
            ut.append((nod.args[1].value, nod.lineno))
    return ut


def _anropar(trad, attribut):
    """Anrop pa formen <nagot>.<attribut>() i modulen."""
    return [nod.lineno for nod in ast.walk(trad)
            if isinstance(nod, ast.Call) and isinstance(nod.func, ast.Attribute)
            and nod.func.attr == attribut]


def test_pinningen_sker_bara_genom_conftest():
    """EN DEFINITION, ETT STALLE - tillampat pa riggningen.

    Pinnar en modul spec_precision eller PROMPT_FILE pa egen hand finns vardet
    pa tva stallen, och det andra blir fel den dag specen andras. conftest har
    hjalparna; ingen annan modul far satta dem sjalv.
    """
    brott = []
    for p in svitens_moduler():
        if p.name == "conftest.py":
            continue
        for namn, rad in _setattr_mal(_trad(p)):
            if namn in PINNADE:
                brott.append(f"{p.name}:{rad} satter {namn} sjalv")
    assert brott == [], (
        "pinningen ska ga genom conftest.pinna_specens_decimalkrav / "
        f"pinna_prompten, men: {brott}")


def test_ingen_modul_bade_pinnar_och_provar_decimalkravet():
    """DEN HAR AR POANGEN.

    En modul som pinnar spec_precision far inte ocksa frassa om dess varde -
    da provar den sin egen attrapp och svarar gront oavsett vad specen sager.
    Den som vill prova decimalkravet gor det i en modul som inte pinnar, eller
    laser den frysta filen direkt.

    test_batchsize.py gor ratt i dag: den anropar spec_precision() och pinnar
    inte. test_classify.py:s test_pinnade_decimalkravet_ar_specens gor ratt pa
    andra sattet: den laser filen forbi den pinnade funktionen.
    """
    brott = []
    for p in svitens_moduler():
        trad = _trad(p)
        pinnar = "pinna_specens_decimalkrav" in _namn_som_importeras(trad)
        anrop = _anropar(trad, "spec_precision")
        if pinnar and anrop:
            brott.append(f"{p.name}: pinnar och anropar spec_precision pa rad "
                         + ", ".join(str(r) for r in anrop))
    assert brott == [], (
        "en modul som pinnar decimalkravet far inte ocksa prova det - "
        f"den provar da sin egen attrapp: {brott}")


def test_decimalkravet_star_som_tal_pa_ett_stalle():
    """Talet ska finnas som conftest.SPEC_PRECISION och ingen annanstans.

    Provar namnet, inte siffran: en modul som skriver 2 i en helt annan mening
    ar inte ett brott, men en som skriver sitt eget decimalkrav ar det.
    """
    conftest = ROT / "tests" / "conftest.py"
    trad = _trad(conftest)
    tilldelningar = [n for n in ast.walk(trad)
                     if isinstance(n, ast.Assign)
                     and any(isinstance(m, ast.Name) and m.id == "SPEC_PRECISION"
                             for m in n.targets)]
    assert len(tilldelningar) == 1, (
        f"SPEC_PRECISION ska tilldelas en gang i conftest, fick {len(tilldelningar)}")

    for p in svitens_moduler():
        if p.name == "conftest.py":
            continue
        for nod in ast.walk(_trad(p)):
            assert not (isinstance(nod, ast.Assign)
                        and any(isinstance(m, ast.Name) and m.id == "SPEC_PRECISION"
                                for m in nod.targets)), \
                f"{p.name}:{nod.lineno} satter ett eget SPEC_PRECISION"


def test_bandet_mellan_attrappen_och_specen_finns_kvar():
    """Pinningen ar bara forsvarlig sa lange nagot knyter den till den frysta
    filen. Forsvinner det testet star sviten och provar ett tal den hittat pa.

    Testet far hoppas over utan arkivet - det ar da det inte gar att kora - men
    det far inte tas bort.
    """
    kalla = (ROT / "tests" / "test_classify.py").read_text(encoding="utf-8")
    assert "def test_pinnade_decimalkravet_ar_specens" in kalla, (
        "testet som knyter conftest.SPEC_PRECISION till den frysta specen "
        "saknas - utan det ar pinningen ett tal utan tackning")
    assert "kraver_arkiv" in kalla
