# 600 STATES — Pre-Emotion Duplicate / Materiality Gate v1.0 FROZEN

Status: FROZEN QA LAYER

Purpose: operationalize the existing rule that duplicate reporting of the same material information state must collapse before emotion classification. This layer does not change the Observation Day Rule, 300/240/60 selection structure, regional floors, emotion vocabulary, or Color Protocol v0.4.

## Gate

1. Run same-day candidate retrieval after the provisional 600 are assembled and before selection freeze.
2. Retrieval may use exact normalized claim matching, title/signature matching, semantic similarity, URL-family variants, and event/provenance overlap.
3. Similarity is never sufficient by itself to delete an observation.
4. Every flagged pair/group receives a materiality adjudication:
   - DISTINCT: the later/parallel observation contains a materially new information state that can be stated explicitly and is supported by evidence.
   - DUPLICATE: no materially new information state can be stated; publisher repetition, spelling/format changes, URL suffixes, or equivalent paraphrases do not qualify.
   - REVIEW_REQUIRED: available evidence is insufficient to decide; the observation cannot be frozen until resolved.
5. For a DISTINCT decision, record one concise `material_novelty_statement` describing what new information is present compared with the earlier/parallel observation.
6. For a DUPLICATE decision, keep one representative observation and replace the redundant slot from the same eligible review stream while preserving all frozen selection constraints.
7. Re-run duplicate/materiality QA after replacements. Selection may freeze only when no unresolved HIGH/MEDIUM duplicate-risk pair remains.
8. Cross-day similarity is an audit signal only. A later UTC day may legitimately contain a materially new information state about the same underlying event.

## Non-negotiable safeguards

- No emotion, RGB/HEX, image, macro-state, reflection, or aesthetic feedback may enter duplicate/materiality adjudication.
- Do not reject a later observation merely because the underlying event is the same.
- Do not admit a repeated observation merely because the publisher, URL, headline, or timestamp differs.
- Numeric changes may be material (for example, a substantively updated casualty count) but are not automatically material; the novelty must be explicit and evidenced.
- If material novelty cannot be verified, it cannot become a separate tile.
