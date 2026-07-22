---
type: Knowledge Bundle Index
title: ISF card authoring
description: Governing principle, the style guide, and the three judgment rules.
tags: [anki, card-authoring, isf]
timestamp: 2026-07-18T00:00:00Z
---

# ISF card authoring

## Governing principle

Card creation is a **faithful rendering of the source into card shape — a robust copy/paste, not a
rewrite.** Take the facts as the source states them and restructure them into cloze cards.

**Add nothing.** No outside knowledge, no synthesized framing, no coined terminology, no
editorializing. If a fact, term, or qualifier is not in the source, it does not go on the card.

# The seven files

| File | What it is |
|---|---|
| **[process.md](process.md)** | **How to build a deck** — the steps. Start here. |
| **[style.md](style.md)** | **The card style** — five lines, plus the reference corpus that settles every other shape question |
| [rules/yield.md](rules/yield.md) | Is this fact worth a card? What did the teacher stress? |
| [rules/accuracy.md](rules/accuracy.md) | Is it true, is it in the source, did you invent anything? |
| [rules/no-duplicate.md](rules/no-duplicate.md) | Does this card already exist? |
| [rules/card-structure.md](rules/card-structure.md) | **What to cloze** — every testable role blanked, ≤3, split beyond, no self-answering |
| **[review-checklist.md](review-checklist.md)** | **The per-card review** — the bar, and what counts as a finding |

**Shape is settled by looking at the reference cards, not by reading rules.** See
[style.md](style.md). Nine prose files that described shape were deleted — they drifted from the
real decks and contradicted them.

Pull the reference corpus with `build_deck corpus` → `classes/ISF/reference/style_corpus.jsonl`.

The driver is `classes/ISF/build_deck.py`. It automates only the deterministic steps —
**authoring and review are agent work; no script writes cards.**
