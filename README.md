# 600 STATES

One artwork per UTC day. 600 tiles, 600 news observations, one irreversible
visual state.

> The artwork is the Proof of State. The manifest is the Proof of Work.

This repository is the **instrument**: the code that selects the 600
observations, prepares them for classification, and turns the classified
result into colour. It is not the artwork and it does not contain the data.

## Why the code is public

600 STATES claims that nothing in a finished State is composed, tuned or
corrected to look better. An ugly day is a valid result, not a bug.

That claim cannot be demonstrated after the fact. Commit dates can be set to
anything; only a push is witnessed. So the instrument is published **before**
the series begins, and every frozen constant in it is a commitment made before
the data existed.

Anyone can check the colour model against a published manifest and get the
same 600 colours. If they do not match, the manifest is wrong — not the
formula.

## Status

**Not yet in operation.** Sharp start is planned for 1 December 2026
(`2026/335`). What exists and what does not:

| | |
|---|---|
| Colour protocol v0.4, frozen | complete, reproduces 3 600 / 3 600 known tiles |
| Consensus over three classifier passes | complete, reproduces the frozen pilot manifest field for field |
| Selection engine, story cap, quotas | complete |
| Gates between every stage | complete |
| Acquisition of new days from GDELT | **not built** |
| Calling the classifier | **not built** — passes are produced outside the chain today |
| Public view | **not built** |

States `001`–`010` under the pilot naming are **validation artefacts from an
earlier generation**, not canonical works. They were used to test the
instrument and they surfaced real method defects, which are documented in
`docs/MATNINGAR.md`.

## Architecture

Three rules shape the code. None of them is tidiness.

**Selection and colour are separate programs.** `run_state.py` selects and
prepares; `run_color.py` colours and renders. Neither imports the other.
Observation Day Rule v1.0 states that the colour model is inaccessible until
the 600-observation manifest is frozen — a chain that *can* reach colour at any
point cannot show that it did not. `tests/test_separation.py` imports each
program in its own interpreter and fails if either pulls in the other side.

**The day is always a parameter.** No code reads the system clock in
computation logic. A daily run and a run of an older day take exactly the same
path, or the days are not comparable. There is no separate backfill script and
there never will be.

**Determinism outranks performance.** Embeddings lost to lexical clustering on
headlines by three percentage points and were rejected: a model whose behaviour
drifts between versions cannot be re-run identically in ten years. Every
threshold in the code has a measurement behind it, recorded in
`docs/MATNINGAR.md`.

## Layout

    src/
      statepaths.py    the day's identity and every filename, in one place
      candidates.py    GDELT -> candidate pool (no materiality decisions)
      ranking.py       mention volume as the funnelling signal
      story_cap.py     one information state, one tile
      select_day.py    quota engine -> exactly 600 frozen observations
      consensus.py     three classifier passes -> one emotion manifest
      color_protocol.py  v0.4 GOLDEN MASTER, frozen
      render.py        manifest -> PNG
      gates.py         a rule that cannot stop a run is not a rule
      run_state.py     selection side
      run_color.py     colour side
    tests/             42 tests
    docs/MATNINGAR.md  the measurement log behind every decision (Swedish)

## Verifying a State

    pip install pytest pillow
    python3 -m pytest -q

The two tests that matter most to an outside reader:

- `test_color_protocol.py` — the colour model must reproduce a frozen manifest
  exactly. If a constant in `color_protocol.py` is touched, it fails.
- `test_consensus.py` — consensus is rebuilt from the three raw classifier
  passes and compared field by field against the frozen manifest.

Both need the data archive, which is not in this repository. Point
`STATES_DATA` at it.

## Frozen protocols

The instrument is governed by documents that are frozen and hashed:
Observation Day Rule v1.0, Colour Protocol v0.4 GOLDEN MASTER, Emotion
Classification Protocol v1.0, Grid Specification v1.0. The code reads the
colour anchors from the protocol file rather than restating them.

A known discrepancy: the protocol's formula list does not state which emotion
belongs to which lightness branch. That mapping exists only in code, and an
earlier handover document stated it incorrectly for `Uncertainty`. Every
rendered State follows the code. The documentation is being corrected to match
the instrument, not the other way round.

## Licensing

Code MIT, evidence CC0, artwork all rights reserved. See `COPYRIGHT.md`.

## Contact

archive@600states.com
