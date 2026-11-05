"""De sexton emotionstillstanden. Klassificeringens vokabular, inte fargens.

Ordningen ar semantisk och fryst i Emotion Classification Protocol v1.0 FROZEN
(faltet emotion_states). Den anvands som skiljedomare nar tre pass inte ger
nagon majoritet: lagsta index vinner. Kasta aldrig om listan.

Den ligger i en egen fil for att klassificeringen ska kunna anvanda den utan
att importera fargprotokollet. Urval och klassificering far inte na fargen -
separationen AR funktionen. test_vocab vaktar att listan ar identisk med den
i color_protocol och med det frysta protokollet.
"""
EMOTION_STATES = ["Joy", "Hope", "Relief", "Calm", "Curiosity", "Awe", "Resolve", "Surprise",
                  "Uncertainty", "Concern", "Tension", "Fear", "Anger", "Grief", "Disillusion", "Fatigue"]

ORDER = {e: i for i, e in enumerate(EMOTION_STATES)}

def arbitrate(values):
    """Majoritet; vid lika lagsta index i den frysta ordningen. (vinnare, antal)"""
    from collections import Counter
    c = Counter(values)
    top = max(c.values())
    return sorted([v for v, n in c.items() if n == top], key=lambda v: ORDER[v])[0], top
