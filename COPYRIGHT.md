# Copyright and licensing

600 STATES has three layers, and they are deliberately licensed differently.

| Layer | What it is | Terms |
|---|---|---|
| **Instrument** | The code in this repository | MIT — see `LICENSE` |
| **Evidence** | Manifests, hashes, selection reports | CC0 1.0 (public domain dedication) |
| **Artwork** | The rendered States (PNG) and the series | All rights reserved |

## Why they differ

The instrument is MIT because the project's central claim — that nothing in a
finished State is composed, tuned or corrected to look better — is only worth
something if anyone can check it. A verification you are not allowed to run is
not a verification.

The evidence is CC0 for the same reason, one step further. A proof held under
licence is not a proof. Manifests and hashes are released into the public
domain so that reproduction, citation and audit carry no conditions at all.
They are published in a separate repository.

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

Said here, the claim is stronger than it was in seventy-two trailers. A
trailer records which tool was in the room for one commit. This says what the
instrument is: machine-written and human-decided, from the first line to the
last. The project asks to be taken at its word on provenance, and that has to
include its own.
