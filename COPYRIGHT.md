# Copyright and licensing

600 STATES has four layers, and they are deliberately licensed differently.

| Layer | What it is | Terms |
|---|---|---|
| **Instrument** | The code in this repository | MIT — see `LICENSE` |
| **Protocols** | The frozen constants in `protocols/` | CC0 1.0 — see `protocols/LICENSE` |
| **Evidence** | Manifests, hashes, selection reports | CC0 1.0 (public domain dedication) |
| **Artwork** | The rendered States (PNG) and the series | All rights reserved |

## Why they differ

The instrument is MIT because the project's central claim — that nothing in a
finished State is composed, tuned or corrected to look better — is only worth
something if anyone can check it. A verification you are not allowed to run is
not a verification.

The protocols are CC0 because they are what the instrument is held to. The day
rule, the colour protocol, the classification protocol and the grid
specification decide what a State is before a line of code runs, and a constant
nobody can read is a constant you have to take on trust. The twelve documents
in `protocols/` are copies: the instrument reads them from the archive, and the
copy exists so that whoever clones this repository holds the same constants the
run was held to. Their SHA-256 hashes are published beside them.

The colour protocol is CC0 here like the other three. `src/color_protocol.py`,
the code that implements it, stays MIT with the rest of the instrument: the
document and its implementation are different things and carry different terms.

The evidence is CC0 for the same reason as the protocols, one step further:
manifests and hashes carry no conditions at all on reproduction, citation or
audit. None of it is published yet, so the terms are the only part that exists.
A proof nobody can read is not yet a proof either, whatever its licence.

The artwork is not free. The images are the work. Reproducing them from a
manifest and the instrument is trivially possible and that is by design — it is
what makes the method auditable — but doing so does not transfer any right to
display, distribute or sell the resulting images.

## Attribution

Rights are held by Myolc AB. The project publishes under the name 600 STATES.

## A note on how this code was written

The instrument is built with AI assistance. That is stated here, and on
600 LABS, and it is not recorded per commit.

It was recorded per commit until 2026-11-11, in `Co-Authored-By` trailers and
session links. The history was rewritten that day to remove them, together
with the owner's first name, from the commit messages: this repository is
public, which makes a commit message as public as a source file, and names
and session links had no business being in one. No file content changed in
that rewrite — all 115 tree hashes are unchanged — and
`docs/HISTORIK_OMSKRIVNING_2026-11-11.md` maps every old commit id to its new
one and records what was verified.

A trailer records which tool was in the room for one commit. This says what
the instrument is: machine-written and human-decided, from the first line to
the last. It is a statement, not a record — the per-commit records were removed
on 11 November 2026, and the history before that rewrite is not publicly
verifiable. The project asks to be taken at its word on provenance, and that
has to include its own. This is the one place where it asks for exactly that.
