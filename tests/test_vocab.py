"""Vokabularet finns pa tre stallen. De far aldrig glida isar."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vocab import EMOTION_STATES, ORDER, arbitrate
from color_protocol import VOCAB, ANCHORS
from config import FROZEN

def test_samma_som_fargprotokollet():
    assert EMOTION_STATES == VOCAB
    assert set(EMOTION_STATES) == set(ANCHORS)

def test_samma_som_fryst_protokoll():
    p = FROZEN / "600_STATES_Emotion_Classification_Protocol_v1.0_FROZEN.json"
    assert json.loads(p.read_text(encoding="utf-8"))["emotion_states"] == EMOTION_STATES

def test_ordningen_ar_skiljedomare():
    """Verifierad mot alla fyra 1/3-fall i STATE_001."""
    assert arbitrate(["Concern", "Anger", "Resolve"])[0] == "Resolve"
    assert arbitrate(["Calm", "Resolve", "Hope"])[0] == "Hope"
    assert arbitrate(["Concern", "Grief", "Uncertainty"])[0] == "Uncertainty"
    assert arbitrate(["Resolve", "Hope", "Curiosity"])[0] == "Hope"

def test_majoritet_slar_ordning():
    assert arbitrate(["Grief", "Grief", "Joy"]) == ("Grief", 2)

def test_index_ar_stabilt():
    assert ORDER["Joy"] == 0 and ORDER["Fatigue"] == 15
