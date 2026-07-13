---
type: Card Authoring Rule
title: No near-duplicate cards
description: Two cards that test the same fact are a duplicate; the deck-level checker surfaces near-duplicate pairs for merge/cut.
tags: [anki, card-authoring, duplicate, dedup, deck-level]
resource: anki://rule/no-duplicate
timestamp: 2026-07-13T00:00:00Z
enforcement: [mechanical, human-review]
source_defects: [wrong-duplicate]
---

# Rule

Two notes that test the **same fact** are a duplicate; keep one. This is a **deck-level** check
(a card is fine in isolation — the defect only exists relative to the rest of the deck), so it
runs after the deck is assembled, not per-card.

Intentional two-sided / split siblings of one note are **not** duplicates — they share an `id`
prefix before `::` and are expected.

# Enforcement

## Mechanical (surface candidates)

The existing detector `classes/ISF/content_check.py` already implements this: it reveals each
card's answer text (strips markup and hints) and reports **near-duplicate pairs** whose revealed
text similarity ≥ a threshold (currently 0.66), skipping same-note siblings. Run it over the deck:

```
classes/ISF/.venv/bin/python classes/ISF/content_check.py <deck-dir> --json
```

It also flags **over-carded subjects** (one `<b>` subject appearing in ≥ 3 cards) — a redundancy
signal adjacent to duplication.

## Human-review gate

The detector never edits or rejects — it produces a worklist. Each near-duplicate pair is routed
to human review to **merge, cut, or keep-both-with-reason** before ship; an unresolved pair blocks
ship (consistent with the project rule that an open flag must be resolved).

# Related

- [card-structure](/rules/card-structure.md) — two-sided siblings of one note are not duplicates.
- [yield](/rules/yield.md) — over-carding a subject is also a yield question.
