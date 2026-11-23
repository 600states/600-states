# 600 STATES — frozen protocols

Read this before implementing anything from the files in this folder. One of
them states a value that is wrong, and the correction is a separate document.

## Known correction: the master is 3087 × 2057 px, not 3000 × 2000

`600_STATES_Grid_Specification_v1.0_FROZEN_EXPORT.json` gives
`master_px: [3000, 2000]`. **That value is incorrectly derived.** The three
values it follows from are the ones that hold:

    cell 100 × 100 px, separator 3 px between cells, no outer border

    width  = 30 x 100 + 29 x 3 = 3087
    height = 20 x 100 + 19 x 3 = 2057

The master measures **3087 × 2057 px**. This is settled in
`600_STATES_Grid_Specification_v1.0_ADDENDUM_A_MASTER_PX.md`, which governs
both the grid specification and the `grid` block of
`600_STATES_Color_Protocol_v0.4_GOLDEN_MASTER_FROZEN.json`.

The frozen files are **not** rewritten and their `canonical_sha256` is
untouched. The addendum completes them; it does not replace them. An
implementer takes the addendum as the authority for the measurement, and the
frozen files as the authority for everything else.

## What this folder is

The frozen constants the instrument is held to, published before the series
begins, so that the rules can be checked against the works rather than the
other way round. Twelve documents, each with its SHA-256 in
`MANIFEST_SHA256__600_STATES_PROTOCOLS_v1.0.txt`. The manifest is the complete
list of them, and every entry in it has a file here. This README is a reader's
guide, not a protocol: it is not in the manifest and carries no hash.

A frozen document is not revised. Where one turns out to be wrong, a separate
addendum states what holds instead, and the original keeps its hash. This
folder currently carries one such addendum, named above.

## Reading order

Each line is a document in this folder; the order is the order the instrument
applies them.

1. **Grid Specification** — `600_STATES_Grid_Specification_v1.0_FROZEN_EXPORT.json`
   the field: 30 × 20, chronological, no exceptions. Read
   `600_STATES_Grid_Specification_v1.0_ADDENDUM_A_MASTER_PX.md` with it, not
   after it.
2. **Observation Day Rule** — `600_STATES_Observation_Day_Rule_v1.0_FROZEN.json`
   which UTC day an observation belongs to. Every other document assumes a day
   has already been chosen.
3. **Emotion Classification Protocol** — `600_STATES_Emotion_Classification_Protocol_v1.0_FROZEN.json`
   the sixteen states and the one fixed vocabulary they come from.
4. **Emotion Classification Execution Spec** — `600_STATES_Emotion_Classification_Execution_Spec_v2.1_FROZEN.json`
   how the classification is run.
5. **Emotion Classification Execution Prompt** — `600_STATES_Emotion_Classification_Execution_Prompt_v2.1_FROZEN.txt`
   the exact text the model is given. It is the one place in this folder where
   the field name `neutral_source_claim` appears as an interface.
6. **Colour Protocol, Golden Master** — `600_STATES_Color_Protocol_v0.4_GOLDEN_MASTER_FROZEN.json`
   the anchors and the formula from emotion to colour. Its `grid` block is
   subject to the addendum above.
7. **Source Registry** — `600_STATES_Source_Registry_v2.0_FROZEN.csv`
   which domains a candidate may come from.
8. **PreEmotion Duplicate Materiality Gate** — `600_STATES_PreEmotion_Duplicate_Materiality_Gate_v1.0_FROZEN.md`
   when two observations are the same story, decided before any emotion is
   read.
9. **Reflection Protocol** — `600_STATES_Reflection_Protocol_v1.0_FROZEN.json`
   frozen, with no implementation in the code.
10. **Macro State Naming Protocol** — `600_STATES_Macro_State_Naming_Protocol_v1.0_FROZEN.json`
    the same. Both are published as commitments, not as descriptions.
11. **Observation Verification Protocol** — `600_STATES_Observation_Verification_Protocol_v0.1.json`
    how a finished day is checked.

## Licence

CC0 1.0 Universal. See `LICENSE` in this folder. The code that implements
these documents is MIT and lives in the repository root; the document and its
implementation are different things and carry different terms.
