"""Kopierar de frysta protokollen till protocols/ och skriver deras hashar.

    python tools/publicera_protokoll.py

KONSTANTERNA AR INSTRUMENTET. Den som klonar repot for att granska ska halla
samma dokument som korningen holls till, utan att be om arkivet. Darfor ligger
de i repot - men de BOR i arkivet: config.FROZEN ar kallan, protocols/ ar en
kopia, och koden laser aldrig kopian. En kopia som far vara kalla for nagon
blir en andra sanning, och da granskar varlden ett dokument som instrumentet
inte kor.

MANIFESTET BAR INGEN TIDSSTAMPEL, med flit. Utan den ar filen en ren funktion
av dokumenten: kor verktyget tva ganger och du far samma bytes, sa ett rent
trad betyder att hasharna stammer med filerna. Nar de hashades star i git, och
git ar vittnet har.

TVA FORMAT UR SAMMA GENOMGANG. Textfilen gar att prova med sha256sum -c,
JSON-filen bar storlekarna. De skrivs i samma anrop och kan inte glida isar.
"""
import hashlib, json, shutil, sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))
import config

UT = ROT / "protocols"
MANIFEST = "MANIFEST_SHA256__600_STATES_PROTOCOLS_v1.0"

# De tolv frysta konstanterna. Inte bibliotekets zip, inte pilotens manifest,
# inte de superseded HISTORICAL-filerna: en zip ar en andra kopia av det som
# redan ligger har, och ett pilotmanifest ar bevis, inte en konstant.
PROTOKOLL = (
    "600_STATES_Observation_Day_Rule_v1.0_FROZEN.json",
    "600_STATES_Color_Protocol_v0.4_GOLDEN_MASTER_FROZEN.json",
    "600_STATES_Emotion_Classification_Protocol_v1.0_FROZEN.json",
    "600_STATES_Emotion_Classification_Execution_Spec_v2.1_FROZEN.json",
    "600_STATES_Emotion_Classification_Execution_Prompt_v2.1_FROZEN.txt",
    "600_STATES_Grid_Specification_v1.0_FROZEN_EXPORT.json",
    "600_STATES_Grid_Specification_v1.0_ADDENDUM_A_MASTER_PX.md",
    "600_STATES_Macro_State_Naming_Protocol_v1.0_FROZEN.json",
    "600_STATES_Reflection_Protocol_v1.0_FROZEN.json",
    "600_STATES_PreEmotion_Duplicate_Materiality_Gate_v1.0_FROZEN.md",
    "600_STATES_Observation_Verification_Protocol_v0.1.json",
    "600_STATES_Source_Registry_v2.0_FROZEN.csv",
)


def main():
    config.require_data()                     # sager ifran om arkivet saknas
    kalla = config.FROZEN                     # 00_CANONICAL_PROJECT_DOCS/01_FROZEN_PROTOCOL_LIBRARY_v1.0
    UT.mkdir(exist_ok=True)
    poster = []
    for namn in PROTOKOLL:
        src = kalla / namn
        if not src.exists():
            raise SystemExit("saknas i arkivet: " + namn)
        shutil.copyfile(src, UT / namn)          # bytes, inte rader
        b = src.read_bytes()
        poster.append({"path": namn, "size_bytes": len(b),
                       "sha256_file_bytes": hashlib.sha256(b).hexdigest()})
        print("  %-62s %6d B" % (namn, len(b)))

    poster.sort(key=lambda p: p["path"])
    (UT / (MANIFEST + ".json")).write_text(json.dumps(
        {"project": "600 STATES", "library": "protocols", "version": "v1.0",
         "file_count": len(poster), "entries": poster},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    (UT / (MANIFEST + ".txt")).write_text(
        "".join("%s  %s\n" % (p["sha256_file_bytes"], p["path"]) for p in poster),
        encoding="utf-8", newline="\n")
    print("\n%d dokument, hashar i %s.{json,txt}" % (len(poster), MANIFEST))


if __name__ == "__main__":
    main()
