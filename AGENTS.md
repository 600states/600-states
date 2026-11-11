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

## The classifier's locked parameters

Model id, prompt sha256, spec sha256, batch size — and **thinking is off**.
`src/classify.py` sends `thinking={"type": "disabled"}` and writes
`thinking_disabled: true` into the run record for every day, next to the model
id and the hashes. A State classified with thinking is not the same instrument
as one classified without, so the record has to say which.

The reason is not cost. The model's thinking is never returned: the blocks come
back empty by design. A reasoning step whose content cannot be read is a step
without derivation, in an instrument whose whole claim is that every step can
be audited.

Measured 2026-11-05, the failure that found this: Opus 5 thinks adaptively by
default, those tokens count against `max_tokens`, and the first call returned
`stop_reason=max_tokens` with 16000 output tokens and **zero characters** of
text. The answer was not cut off. It never started. Raising `max_tokens` would
not have fixed that — the ceiling is a separate question, settled below.

## The classifier's output ceiling and output format

`max_tokens` is 32000, and that number is measured. With thinking off, 16000
output tokens produced 41-42 complete rows out of 60 on all three attempts
(2026-11-05, batch 01): **387 output tokens per row**. Sixty rows need 23 250.
A ceiling has to be a measured quantity, not a round number — re-measure it if
the row format ever changes.

`OUTPUT_RULE` also asks for compact JSON: no indentation, no line breaks
between objects. The truncated response came back indented — 1 134 lines for
41 objects — and whitespace is billed as output tokens. This is formatting,
not content: the frozen protocol specifies what each row must contain, never
how it is laid out, so the rule lives in `src/classify.py` and not in the
frozen prompt whose sha256 the gate checks.

**Do not touch the compact-JSON rule until the rate is measured.** One attempt
in three on 2026-11-05 came back as broken JSON in the middle of an otherwise
complete response — the model stuttered and wrote half a field twice
(`"primary_emotion":"Joy":0.00},"primary_emotion":"Joy"`). The compact format
may be what provokes it. If that rate holds it means roughly ten re-runs a day
and about $5 extra, which is worth knowing but not worth guessing about. The
run record counts it per batch as `parse_failures`, and per run under `totals`
so a run where every attempt failed still leaves the number. Collect it over
several days first.

Anthropic's own documentation warns that Opus 5 with thinking off sometimes
leaks internal XML tags into the visible output. `parse()` is strict and
`validate()` checks every row, so such a response fails rather than being
saved — and the raw response is written to
`classifier_passes/FAILED_*.txt`. If it happens, it is a measurement: record
it, do not make the parser more forgiving.

## The two things `parse()` settles before `validate()` sees a row

Both were measured on batch 01 of 2026/308 on 2026-11-05, and both are decided
in `src/classify.py` before validation — never by softening validation.

**An empty-named score key is struck out and counted.** One row in 60 came back
with a seventeenth score key whose name was the empty string —
`"Fatigue":0.28,"":0` — with all sixteen real keys correct. That is an emission
artefact of compact JSON, not a protocol violation. **Only the exact empty
string is removed.** Every other extra key still fails validation: a misspelt
emotion such as `Joie` is a different thing entirely and must never slip
through. The count goes into the run record per batch as `emission_artifacts`.
The defect is not hidden; it is counted.

**`primary_emotion` and `secondary_emotion` are derived from `scores`.** The
spec says `primary_must_rank_first` and `secondary_must_rank_second`, so it
already defines these fields as derived — computing them is the strictest
reading of that rule, not a relaxation of it. The model's own labels are kept
as `stated_primary` and `stated_secondary`, and the model is still required to
deliver them: we stop requiring that they agree, not that they exist.

Ties go to the lowest index in the frozen `EMOTION_STATES` order, the same
arbitration `vocab.arbitrate()` uses for consensus — `derive()` sorts by
`(-score, ORDER[emotion])`. The derivation must stay a pure function of the
values and never of the key order in the model's JSON, or the field is not
reproducible.

Why it was needed: the model names as `secondary_emotion` what it judges to be
the event's second character, not the arithmetic runner-up. Four measured
cases, none of them ties — Hope 0.36 while Tension had 0.38; Surprise 0.52
while Tension had 0.58; Surprise 0.50 while Tension had 0.54; Hope 0.46 while
Concern had 0.50. At two rows in 60 per attempt, nearly every batch failed
all three attempts and no day could finish.

`diagnostics()` reports `stated_primary_differs` and `stated_secondary_differs`
per batch, so the calibration battery gets the number without an extra call. A
model whose narrative and whose numbers drift apart often is measurably worse,
whatever it costs. Replaying the three saved responses of 2026/308 through the
new code: primary diverged **0** times, secondary 3 and 1.

`src/consensus.py` is untouched. It reads `primary_emotion` and
`secondary_emotion` from the pass files and now always gets derived values.

## The run record grows; it is never overwritten

A day's thirty calls are taken in several rounds — `--budget` is the normal
mode for a resumable run — so the record is read, this round's calls are
appended and `totals` is recomputed over all of them. Each call carries a
`run` stamp (UTC, one per round) so it is visible which calls belong together.
The write goes through `src/atomic.py` like every other manifest write.

It is written on **every** exit from `run()`: the budget ceiling, a gate
failure, an interruption, a normal finish. The `finally` around the batch loop
is what guarantees that, and it is not decoration: the budget exit used to
return before the write, so on most runs the token accounting for a call that
had already been paid for existed nowhere. The record is the manifest's
provenance claim; it may not describe one round out of three.

**And it says what it does not cover.** On every write, the pass files on disk
are compared with the calls in the record and the ones with no call are listed
under `unrecorded`, with an `unrecorded_note` saying why they cannot be
accounted for. A record that is silent about its gaps is a silent untruth —
the rule has stood since FYND 001. The gap appears whenever a batch was
classified without its call reaching the record, which an interruption can
cause again at any time; it is not a one-off for 2026/308. The list is
recomputed from disk at every write and never inherited from an earlier
record, so an empty list is a statement too: the check ran.

Before the first call, `las_journal()` checks `model`, `prompt_sha256` and
`spec_sha256` against the existing record and stops the run if any of them
differs — a different instrument half way through a day means the day cannot
become a work. The gate runs before the calls, not at the write: discovering
the swap at the write means the money is already spent.

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

## The manifest version names a shape: write `V`, read `frozen()`

`v3.2` has 17 columns in the pre-emotion manifest, `v3.3` has 19. Two shapes
under one version name is what made "Execution Spec v2.2" useless as a
reference, so the columns and the version move together.

2026/308 is frozen as v3.2 and stays that way. So production steps
(`run_state`, `consensus`, `run_color`, `render`) write `statepaths.V` and
nothing else — what happens to be on disk must never decide the shape that is
written — while the steps that read a finished day (`audit_state`,
`build_site`, `build_battery`) go through `statepaths.frozen()`, which takes
the day's own file. Audit of 2026/308 passes unchanged under v3.3 code.

`frozen()` says so when it substitutes, naming the file asked for and the file
read, and the audit report prints the version of each file it actually read.
A silent substitution is FINDING 011's shape again: the record does not say
which form it read.

Two versions of the same file in one day stop the read. The first version took
`sorted(...)[-1]` and carried on. A day has one shape; if its directory holds
two, someone re-ran half the chain, and which one counts is not the code's
decision. `site/build.py` is the exception and keeps globbing: the pilot days
carry v3.0 and v3.1 on purpose, because they were re-rendered.

A day that was produced under an older version cannot be half re-run: colour
and render would write `V` beside its older manifests. Produce it whole, or
leave it alone.

## Two `basis()`, and only one of them is the series

`capture_state.basis()` belongs to the pilot path. It can return three levels
and `CAPTURED_IN_WINDOW` is not among them, because that path fetches long
after the day it describes. It is still called by `repair_evidence.py`. Leave
it alone; do not "complete" it.

`pool_evidence.basis(candidate, day)` is the v3.0 path and the only producer of
`CAPTURED_IN_WINDOW`. Three lines in it are decisions, not implementation:

- **The window has two sides**: after the observation's own `first_mention_utc`,
  and at most `FONSTER_TIMMAR` after the observation day closed at 24:00 UTC.
  The upper bound is a margin for a run that starts at `KORNING_START_UTC`, not
  a target. The lower bound is deliberate: a page fetched before the story
  existed does not carry the story, however early we were. The level that
  misses either side is `RETROSPECTIVE`.
- **Both numbers live in exactly one place**, the two constants at the top of
  `pool_evidence.py`, never inside `basis()` and never repeated in a scheduler.
  The batch size showed what two copies of one number cost: 60 in the code, 50
  in the spec, for months.
- **The evidence is the hashed page, not the attempt.** `fetch_one` stamps
  `retrieved_at_utc` even when the fetch fails, so a row without
  `content_sha256` is `NO_EVIDENCE` however promptly we tried.

The level was called `OBSERVED_AT_CAPTURE` while the boundary was the fetch's
own calendar day. That boundary was wrong - a fetch at 00:30 the next day is
methodologically identical to one at 23:50 - and the name went with it.

`gate_evidence_time` stops the freeze when a row carries no timestamp or no
level, and it runs on the rows in memory, before the manifest is written. The
field existed in the working file and was dropped at the freeze for three days
before anyone looked; see FINDING 011.

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

## Nobody checks their own work — binding from 2026-11-10

Whoever writes a thing does not write the check for it.

This is not an opinion about who codes better. A test written by the author of
the code inherits the author's assumptions, and the test then asks precisely
the question the author already believed the answer to. The failure is
structural and applies to every agent and every person working here.

It is written down because it happened, on 2026-11-10, in this repository.
Five tests were written for `tools/bygg_referens.py` by the same author as the
program. Every one of them asserted on the *source text* rather than on
behaviour:

    assert "if NY.exists():" in inspect.getsource(bygg_referens.main)

Replace `sys.exit(...)` with `print(...)` and the gate stops protecting
anything while that assertion still passes. One of the five asserted that a
sentence existed in a docstring — a test whose only way to fail is for someone
to edit a comment. An independent reviewer found all five in one reading.

It is the same shape as FINDING 001-004, and as the source-registry gate that
compared a filename with itself, and as `audit_state.py` returning a hardcoded
`True`. The difference is that this time the gate was the test suite.

**The rule, in both directions:**

| Who writes it | Who writes the test, the gate, and the review |
|---|---|
| Claude (this session) | Claude Code |
| Claude Code | Claude (this session) |

Applies to: code, gates, tests, anything that changes a frozen artefact, and
any number that will be published.

**The reviewer does not get the author's tests.** Only what must hold. Handing
over the existing test file turns an independent question into an edit of the
author's assumptions, which is the thing being guarded against.

**Procedure.** The author writes the implementation, then writes a brief for
the other agent stating what must hold and what must not be assumed, and tells
the operator explicitly that it goes to the other agent. The operator carries
it; the two agents do not talk directly. Disagreements go to the operator only
when they are real disagreements.

## No figure is published on one measurement — binding from 2026-11-10

A number that has been measured once does not go on the public site, into the
message bank, or into any document presented as evidence. Measure again,
independently, and publish the pair or the range.

Also written down because it happened the same day. A self-agreement figure of
0.86 was measured once, published, and described as "five times the noise
floor" — where the noise floor itself came from two measurements. The next run
of the same configuration gave 0.82. The claim was wrong by the time it was
read, and the error was public for a day on a page whose entire claim is that
its numbers can be trusted.

Two consequences, both binding:

- **A measure with one measurement behind it carries no multiple.** At n = 50
  the standard error is ±0.059. The figure has been in `tools/calibrate.py`
  since the battery was built.
- **Name the measure, not just the number.** The error that caused the above
  was conflating agreement *between the three passes* with agreement *against
  the reference*. Both are "tiles in fifty that differ". They are not the same
  quantity and must never be written as if they were.

Neither gate nor reviewer caught that one. The next measurement did, which is
the only mechanism that could have — and is the reason this rule is about
measuring twice rather than about reading more carefully.

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
