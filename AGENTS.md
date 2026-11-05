# Working rules for this repository

Read this before proposing or writing any code here.

600 STATES produces one artwork per UTC day from 600 news observations. The
rules below are not tidiness preferences. Most of them exist because breaking
them silently destroys the project's only real asset: that a finished State can
be shown to be a consequence of the method rather than of taste.

## Never propose changing

- **Colour protocol v0.4** (`src/color_protocol.py`). Constants, weights,
  thresholds and clamps are frozen. No simplification, no vectorisation that
  changes floating-point results, no "readability refactor".
- **The ranking rule** for primary/secondary: stable sort with the index in
  `vocab.EMOTION_STATES` as tiebreak. That order is semantic and frozen.
- **Observation Day Rule v1.0** — UTC day, INFORMATION_DAY.
- **SHA256 hashing** of manifests, selections and snapshots.
- **Validation thresholds** (0.90, 0.95, 0.25, 25, 15 and others). They are
  evidence with measurements behind them, not magic numbers to clean up.

## The architecture rule that must not be optimised away

Selection is frozen **before** emotion classification, and the colour model is
unreachable until the 600-observation manifest is frozen.

In practice: `run_state.py` (selection, classification input) and
`run_color.py` (colour, render) are separate programs. They do not import each
other. `consensus.py` does not import the colour protocol — it writes an
emotion manifest with no `hex` column and freezes it with a SHA256 sidecar,
which `run_color.py` verifies before colour is applied.

Never merge them, even when it would mean fewer lines. **The separation is the
function.** `tests/test_separation.py` imports each program in its own
interpreter and fails if either side reaches the other.

## The day is always a parameter

Every step takes the observation day as an argument (`YYYYMMDD`, UTC). No code
may read the system clock in computation logic. A daily run and a run of an
older day must take exactly the same path, or the days are not comparable.

Never write a separate backfill script.

`src/statepaths.py` derives the day's identity and every filename. Do not build
a `state_id` string anywhere else — the format drifted from `2026/001` to
`2026-001` once already, and because `state_id` feeds the `observation_id`
hash, every identifier in that generation changed.

## Runs must be idempotent

The same day run twice gives an identical result and does not duplicate or
overwrite frozen artefacts. An interruption must not leave a half-written
manifest: all manifest writes go through `src/atomic.py`.

## Determinism outranks performance

If a proposal could change output bit-for-bit, do not put it forward.
Embeddings lost to lexical clustering for this reason, and were rejected.

## An ugly day is a valid result

Output that looks bad is not a bug to fix. Nothing may be made prettier by
hand, no tile substituted, no composition rebalanced. If a State looks dull or
muddy, that is what the day's news flow produced under a method that was fixed
before the day began — and it is the strongest evidence the method is real.

Never propose a change whose justification is that the image would look better.

## The chain of traceability may never be shortened

news item -> observation -> emotion -> colour

Every link must stay walkable in the manifests: the URL behind a tile, the
evidence capture behind the URL, the three classifier passes behind the
consensus, the frozen formula behind the hex. Do not collapse a step, cache
away an intermediate, or drop a column because nothing reads it yet.

## This repository is public

Never commit, in code, comments, documentation, test fixtures or commit
messages:

- personal names or private email addresses
- an employer's or a client's name
- local filesystem paths of any kind

This applies to history as much as to the current tree — a deleted file still
carries its content in the object database. The path to the data archive comes
from `STATES_DATA` and is never hardcoded; see `config.py`.

Before any push, scan the whole object database, not just the latest version,
and search spelling variants rather than only the obvious words.

## Where documentation and code disagree, code wins — and say so

One open divergence and two resolved. Do not "fix" the code to match the documents:

- **`Uncertainty` lightness branch.** The frozen formula list does not state
  which emotion belongs to which branch, and an earlier handover stated it
  incorrectly. Every rendered State treats `Uncertainty` as negative, and
  `color_protocol.py` does the same. Verified against 3 600 known tiles.
- ~~**Master dimensions.**~~ Resolved 2026-11-05: the master is 3087x2057.
  The frozen spec gave cell 100, separator 3, no external border and master
  3000x2000, which cannot all hold (30x100 + 29x3 = 3087). The derived value
  was corrected, the three constitutive values stand. `render.py` already does
  this; nothing was re-rendered. See the Grid Specification Addendum A. Do not
  "fix" render.py to 3000x2000.
- ~~**Two different `v2.2`.**~~ Resolved 2026-11-05. The Execution Spec exists
  only as v2.1, `600_STATES_Emotion_Classification_Execution_Spec_v2.1_FROZEN.json`.
  A reference to "Execution Spec v2.2" is an error; it came from the parameter
  registry, since corrected, and `src/consensus.py` said it until f80494a.
  `FROZEN_PRE_EMOTION_PACKAGE_v2.2` is a different artefact and that version is
  right. **Never search and replace on `v2.2`**: it would corrupt
  `docs/MATNINGAR.md`, `tests/test_candidates.py` and `tests/test_evidence_hash.py`.
  Read what the version belongs to before touching it.

If you find another, report it. Do not resolve it in a commit.

## May be reviewed and cut hard

I/O, paths, CLI arguments, logging, error messages. Duplicated code between
steps. Dependencies — is `pandas` or `sklearn` justified, or does stdlib do it?
Dead code and unused imports.

## Style

Code comments and commit messages are in Swedish, written without diacritics
(`foljer`, not `följer`) to match the existing codebase. Commit messages state
what changed and why, with the measurement or finding that motivated it.

A comment explains why a rule exists, not what the line does.

## Tests

Dependencies live in a virtual environment inside the repository, with locked
versions in `requirements.txt`. The daily run goes on for years on one machine,
and a global install can be changed by any other installation without anyone
noticing.

    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
    .venv\Scripts\python -m pytest -q

57 tests with the data archive present. Without it, 47 pass and 10 skip: a
clone without the archive must skip, never crash, because the README promises
an outside reader it can.

`requirements.txt` is a lock file, and that was verified rather than assumed on
2026-11-05: a second environment built from it in an empty venv froze to an
identical list, 23 packages, no differences, and ran 57 and 47/10. Installing
it against an environment that already satisfies it proves only that the
conditions hold, not that a restoration reproduces the instrument. Whoever
restores this in a year has the file and nothing else. A rule that cannot stop a run is not a rule: gates
live in `src/gates.py` and raise.
