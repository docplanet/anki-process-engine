---
type: Card Authoring Rule
title: Accuracy — every fact must match its cited source
description: A card may assert only what its cited source supports; added qualifiers, distortions, or ungrounded facts flag for accuracy review.
tags: [anki, card-authoring, accuracy, provenance, review]
resource: anki://rule/accuracy
timestamp: 2026-07-13T00:00:00Z
enforcement: [human-review]
source_defects: [wrong-information]
---

# Rule

A card may assert **only what its cited source supports** — no more. The `Extra` field carries
the provenance (the slide image and/or a verbatim `Source:` line); the card's fact must be
exactly grounded in it. Any of the following is a defect:

- **Added qualifier / embellishment** — the card states more than the source
  ("takes ~2 months" → "takes ~2 months **per cycle**").
- **Distortion** — the card changes the source's meaning.
- **Ungrounded fact** — the source is missing, or too garbled to support the claim
  (a fact derived from an unreadable transcript line is not grounded).
- **Factual error** — the claim is wrong on the subject matter, regardless of source.

# Status — review gate, not mechanical

Accuracy cannot be checked by shape tooling. A card whose fact is not clearly supported by its
cited source is **flagged for accuracy review and does not ship until a human confirms it**
(consistent with the project rule that an open flag must be resolved, never silently carried).
For clinical/board facts, confirmation is a human/expert call.

# Examples

From real flagged cards (`wrong-information`).

| card claim | source | defect |
|-----------|--------|--------|
| "{{oogenesis}} takes {{~2 months per cycle}}" | "…takes ~2 months" | added "per cycle" |
| "In {{pseudostratified epithelium}}, {{not all cells reach the free surface}}" | garbled transcript ("So only one cell where in depth…") | ungrounded — source can't support it |

# Enforcement

## Human-review gate

- Compare each card's fact against the `Source:` in its `Extra`. If the card asserts anything the
  source does not support, set **flagged / blocked** and route to human accuracy review.
- **Provenance is a precondition:** a card with no resolvable source (no slide image and no
  verbatim `Source:` line) cannot be accuracy-checked — treat missing provenance as an automatic
  flag. (See the provenance requirement in the pipeline's fill contract.)

## Judgment (generator instructions)

- assert only what the source states; do not add qualifiers, round differently, or infer beyond it
- if the source is garbled or absent, do not fabricate — flag the gap instead
