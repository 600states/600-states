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

1. **Grid Specification** — the field: 30 × 20, chronological, no exceptions.
   Read `..._ADDENDUM_A_MASTER_PX.md` with it, not after it.
2. **Observation Day Rule** — which UTC day an observation belongs to. Every
   other document assumes a day has already been chosen.
3. **Emotion Classification Protocol** — the sixteen states and the one fixed
   vocabulary they come from.
4. **Emotion Classification Execution Spec** and **Execution Prompt** — how
   the classification is run, and the exact text the model is given. The
   prompt is the one place where the field name `neutral_source_claim`
   appears as an interface.
5. **Colour Protocol, Golden Master** — the anchors and the formula from
   emotion to colour. Its `grid` block is subject to the addendum above.
6. **Source Registry** — which domains a candidate may come from.
7. **PreEmotion Duplicate Materiality Gate** — when two observations are the
   same story, decided before any emotion is read.
8. **Reflection Protocol** — and
9. **Macro State Naming Protocol** — both frozen, neither implemented in code
   yet. They are published as commitments, not as descriptions.
10. **Observation Verification Protocol** — how a finished day is checked.

## Licence

CC0 1.0 Universal. See `LICENSE` in this folder. The code that implements
these documents is MIT and lives in the repository root; the document and its
implementation are different things and carry different terms.
