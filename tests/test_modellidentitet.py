"""Grinden mot modellidentiteten.

Skrivet av den andra parten an den som skrev grinden i 0986fcb, enligt
AGENTS.md.

VAD SOM AR I FARA. Exekveringsspecen anger classifier_model "GPT-5.6 Sol".
Instrumentet kor claude-opus-5. Specen ar fryst och rattas inte, sa den
styrande identiteten bor i config.STYRANDE_MODELL - och det enda som haller
isar de tva ar att koden INTE laser specens falt. Den uppenbara "rattelsen"
later grinden jamfora mot specen. Da slapper den igenom fel modell och stoppar
varje riktig korning: grinden faller at fel hall och ser ut att fungera.

Darfor star tyngdpunkten i det har testet pa jamforelsevardet, inte pa att
grinden kan saga nej. test_jamforelsevardet_ar_config_och_inget_annat och
test_specens_falt_ar_inte_jamforelsevardet ar vakterna; de ovriga beskriver
beteendet runt dem.

VAD SOM MATS UR KALLKODEN OCH INTE UR EN KORNING. Tva pastaenden gar inte att
kora hit utan att bygga en hel korning: att grinden ligger fore forsta
API-anropet, och att korjournalens post bar bada modellnamnen. Posten byggs
efter API-nyckelkontrollen och ingen korning har gjorts med den nya koden, sa
det finns ingen journal att lasa. Bada provas darfor pa run():s egen kalltext,
och ordningen provas DESSUTOM genom att korningen faktiskt stoppas innan den
nar steget efter grinden. Det star utskrivet i varje sadant test.
"""
import importlib, inspect, os, sys
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT / "src"))
sys.path.insert(0, str(ROT))
import classify
import config
import gates
from conftest import kraver_arkiv

ANNAN = "MODELL-SOM-INTE-AR-DEN-STYRANDE"


# =========================================================================
# 1. Grinden faller vid avvikelse och slapper igenom den styrande
# =========================================================================

def test_den_styrande_modellen_slapps_igenom():
    styrande = config.styrande_modell()
    assert classify.gate_modellidentitet(styrande) == styrande


def test_en_avvikande_modell_faller():
    with pytest.raises(gates.GateFailure) as e:
        classify.gate_modellidentitet(ANNAN)
    # Felet ska namna BADA: en grind som bara sager "fel modell" tvingar den
    # som last stoppet att ga till koden for att se vad den vantade sig.
    assert ANNAN in str(e.value)
    assert config.styrande_modell() in str(e.value)


# =========================================================================
# 2. DET VIKTIGASTE: jamforelsen sker mot config, aldrig mot specens falt
# =========================================================================

def test_jamforelsevardet_ar_config_och_inget_annat(monkeypatch):
    """Vrid pa config och se grinden folja med.

    Det har ar provet pa VAR vardet kommer ifran, och det kraver inget arkiv.
    Byter nagon ut jamforelsen mot specens falt - eller mot en literal -
    slapper raden nedan inte langre igenom MODELL-X, och den riktiga modellen
    slutar falla.
    """
    monkeypatch.setattr(classify, "styrande_modell", lambda: "MODELL-X")
    assert classify.gate_modellidentitet("MODELL-X") == "MODELL-X"
    with pytest.raises(gates.GateFailure):
        classify.gate_modellidentitet(config.STYRANDE_MODELL)


def test_den_styrande_identiteten_overlever_att_specen_ar_borta(monkeypatch, tmp_path):
    """styrande_modell() far inte rora specfilen alls."""
    monkeypatch.setattr(config, "SPEC_FILE", tmp_path / "finns-inte.json")
    assert config.styrande_modell() == config.STYRANDE_MODELL
    # Negativ kontroll pa stand-in:en sjalv: den som DOCK laser specen faller.
    # Utan den raden hade testet ovan kunnat passera for att utbytet inte bet.
    with pytest.raises(OSError):
        config.specens_modellfalt()


@kraver_arkiv
def test_specens_falt_ar_inte_jamforelsevardet():
    """REGRESSIONSVAKTEN. Specens eget falt ska FALLA som modell.

    Den som "rattar" config till att lasa specen far den har raden gron i
    stallet for rod - alltsa testet rott. Det ar hela poangen med det.
    """
    falt = config.specens_modellfalt()
    assert falt, ("specen bar inget classifier_model-falt; da provar det har "
                  "testet ingenting och vakten ar borta")
    assert falt != config.styrande_modell(), (
        "specens falt och den styrande modellen ar lika. Specen ar fryst och "
        "skulle inte kunna andras: kontrollera arkivet mot den publicerade "
        "hashen innan du ror det har testet")
    with pytest.raises(gates.GateFailure):
        classify.gate_modellidentitet(falt)


def test_den_styrande_modellen_star_i_tankandetabellen():
    """DELVAKT PA VILKET vardet ar, utan arkivet. Inte en hel vakt.

    Vakterna ovan provar VAR vardet kommer ifran. Den arkivfria av dem byter ut
    styrande_modell och ser darfor inte en andrad literal: muteras
    STYRANDE_MODELL till "GPT-5.6 Sol" ger det 1 rott prov MED arkivet och noll
    utan - vakten for vardet ligger bland de overhoppade, och en extern
    granskare kor sviten utan arkiv. Uppmatt 2026-11-24 pa 5f80624.

    TANKANDE ar en lista over modeller instrumentet kan kora, och den finns i
    repot. Specens falt star inte i den och faller har. Men raden ar BARA en
    delvakt: "claude-sonnet-5-5" star i tabellen och slipper igenom. Last som
    hel vakt ar den samre an ingen - det arkivkravande provet ar fortfarande
    det som sager vilket vardet ska vara.

    Ingen andra deklaration av modellnamnet laggs till for att gora den hel.
    Tva definitioner av samma varde ar FYND 004, och ett varde pa tva stallen
    ar precis det grinden finns for.
    """
    assert config.styrande_modell() in classify.TANKANDE, (
        "den styrande modellen %r star inte i TANKANDE. Antingen har literalen "
        "i config andrats till nagot instrumentet inte kor, eller sa har "
        "modellen fallit ur tabellen - i bada fallen klassificerar en korning "
        "med en modell ingen skrivit in" % config.styrande_modell())


# =========================================================================
# 3. --avvikande-modell noterar och slapper igenom - bara vid avvikelse
# =========================================================================

def test_avvikande_modell_pa_begaran_noteras_och_slapps(capsys):
    assert classify.gate_modellidentitet(ANNAN, tillat_avvikelse=True) == \
        config.styrande_modell()
    ut = capsys.readouterr().out
    assert "NOTERA avvikande modell pa begaran" in ut
    assert ANNAN in ut, "noteringen maste namna vilken modell som kordes"


def test_flaggan_noterar_ingenting_nar_modellen_stammer(capsys):
    """Flaggan far inte stanga av grinden, bara slappa igenom en avvikelse.

    En flagga som hoppar over provningen aven nar det inte finns nagon
    avvikelse ar en flagga som tystar grinden, och da sager korjournalen
    "avvikelse pa begaran" om en korning som inte avvek.
    """
    classify.gate_modellidentitet(config.styrande_modell(), tillat_avvikelse=True)
    ut = capsys.readouterr().out
    assert "NOTERA" not in ut
    assert "  OK   " in ut and "modellen ar den styrande" in ut, "grinden kordes inte"


# =========================================================================
# 4. model=None provar ingenting OCH sager det
# =========================================================================

def test_utan_modell_provas_ingenting_och_grinden_sager_det(capsys):
    """Utskriften ar pastaendet. En grind som tiger nar den inte provade
    lamnar ett tomrum som ser ut som ett godkannande."""
    assert classify.gate_modellidentitet() == config.styrande_modell()
    ut = capsys.readouterr().out
    assert "MODELLIDENTITETEN PROVADES INTE" in ut
    assert config.styrande_modell() in ut, (
        "raden maste saga vilken modell som ar den styrande, annars vet den "
        "som laser loggen inte vad som inte provades")
    assert "  OK   " not in ut and "  STOPP" not in ut, (
        "grinden skrev en grindrad fast den inte provade nagot")


# =========================================================================
# 5. Grinden ligger fore forsta API-anropet i run()
# =========================================================================

def test_grinden_star_fore_klienten_i_run():
    """Kalltextmatning, inget anrop. Ordningen i run() ar pastaendet."""
    src = inspect.getsource(classify.run)
    fore = src[:src.index("gate_instrument(")]
    assert src.index("gate_instrument(") < src.index("anthropic.Anthropic(")
    assert "anthropic" not in fore and "client" not in fore, (
        "nagot som ror API-klienten star fore instrumentgrinden i run()")


@kraver_arkiv
def test_korningen_stoppas_av_grinden_fore_steget_efter_den(monkeypatch):
    """Korningen avbryts INNAN den nar nasta steg - utan att nagot anropas.

    batches() ar forsta raden efter grinden, och allt som kostar pengar ligger
    efter batches(). Nar den raden aldrig kors ar pengarna inte utlagda.
    gate_dygnet_ar_oppet kopplas bort: den handlar om dygnet, inte om modellen,
    och skulle annars stoppa korningen fore det som provas har.
    """
    monkeypatch.setattr(classify, "gate_dygnet_ar_oppet", lambda day: None)

    def for_langt(*a, **k):
        raise AssertionError("korningen gick forbi grinden")

    monkeypatch.setattr(classify, "batches", for_langt)
    with pytest.raises(gates.GateFailure) as e:
        classify.run("20261201", model=ANNAN)
    assert "modellen ar den styrande" in str(e.value)


# =========================================================================
# 6. main() kopplar flaggan hela vagen fran argv
# =========================================================================

def _ur_argv(monkeypatch, argv):
    """Kor main() med argv och lamna tillbaka argumenten run() fick, vid namn.

    Bindningen gors mot den RIKTIGA signaturen, sa att en omflyttad
    parameterordning inte kan ge testet ratt av misstag.
    """
    riktig = classify.run
    sett = {}

    def fanga(*a, **k):
        sett["bundna"] = inspect.signature(riktig).bind(*a, **k).arguments
        return 0

    monkeypatch.setattr(classify, "run", fanga)
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as e:
        classify.main()
    assert e.value.code == 0
    return sett["bundna"]


def test_main_kopplar_avvikande_modell_fran_argv(monkeypatch):
    bundna = _ur_argv(monkeypatch,
                      ["classify.py", "20261201", "--dry-run", "--avvikande-modell"])
    assert bundna["tillat_avvikande_modell"] is True


def test_main_utan_flaggan_slapper_ingen_avvikelse(monkeypatch):
    bundna = _ur_argv(monkeypatch, ["classify.py", "20261201", "--dry-run"])
    assert bundna["tillat_avvikande_modell"] is False


# =========================================================================
# 7. DEFAULT_MODEL ar styrande_modell() nar STATES_MODEL ar osatt
# =========================================================================

def _ladda_om_med(varde):
    if varde is None:
        os.environ.pop("STATES_MODEL", None)
    else:
        os.environ["STATES_MODEL"] = varde
    return importlib.reload(classify)


def test_default_model_kommer_ur_den_styrande_identiteten(monkeypatch):
    """Inte ur en literal med samma text.

    config.STYRANDE_MODELL vrids till ett varde ingen literal kan rakar vara
    lika med. Star det ett fast strangvarde i classify.py gar den har raden
    sonder - samma varde pa tva stallen ar FYND 004:s form.
    """
    fore = os.environ.get("STATES_MODEL")
    monkeypatch.setattr(config, "STYRANDE_MODELL", "MODELL-X")
    try:
        assert _ladda_om_med(None).DEFAULT_MODEL == "MODELL-X"
        # Att provet kan se en skillnad: miljovariabeln tar over nar den finns.
        assert _ladda_om_med("MODELL-UR-MILJON").DEFAULT_MODEL == "MODELL-UR-MILJON"
    finally:
        monkeypatch.undo()
        _ladda_om_med(fore)
    assert classify.DEFAULT_MODEL == config.styrande_modell(), (
        "modulen lamnades i ett annat skick an den hittades i")


# =========================================================================
# 8. Korjournalens post bar bade den styrande och specens falt
# =========================================================================

def test_korjournalen_bar_bada_modellnamnen():
    """KALLTEXTMATNING, inte en korning.

    Posten byggs efter API-nyckelkontrollen i run() och ingen korning har
    gjorts med den nya koden, sa det finns ingen journalfil att lasa. Det som
    gar att prova harifran ar att bada falten star i posten OCH att de hamtas
    ur funktionerna i stallet for att skrivas som text: en literal hade varit
    samma varde pa tva stallen igen.
    """
    src = inspect.getsource(classify.run)
    assert '"styrande_modell": styrande_modell()' in src
    assert '"spec_classifier_model": specens_modellfalt()' in src


@kraver_arkiv
def test_specens_falt_ger_journalen_ett_varde():
    """Posten ovan vore tom om faltet inte fanns. Det gor det."""
    assert config.specens_modellfalt().strip()
