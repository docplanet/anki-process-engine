---
type: Knowledge Bundle Index
title: ISF card authoring
description: Governing principle, the style guide, and the three judgment rules.
tags: [anki, card-authoring, isf]
timestamp: 2026-07-18T00:00:00Z
---

# ISF card authoring

## What a card is FOR

**A card exists to make the student produce a key term or phrase from memory, inside a complete
thought.** That is what reinforces recall — not reading a fact again, not recognising it, but
having to say it.

So the question that decides every cloze is: **what must the student produce for this card to be
doing its job?** That word is the blank. Everything else on the card is there to make the sentence
a complete, natural thought that the blank sits inside.

This is the *purpose*; the principle below is a *constraint on how to serve it*. When the two seem
to pull apart, the purpose is what the card is for.

> **Why this is stated first.** It used to be missing entirely, and its absence was not harmless.
> Asked whether to cloze `<b>Parathyroid hormone</b>` in *"PTH acts on bone to raise blood calcium"*,
> a reviewer answered: *"it serves as the general FRAME (which hormone are we talking about), not a
> term being tested for recall."* It wrote down the exact recall question and classified it as
> context — because nothing told it that making the student produce that word was the point. With
> no purpose to reason from, "is this a term the student must recall?" is a question with no answer
> that can be wrong.

## Governing principle

Card creation is a **faithful rendering of the source into card shape — a robust copy/paste, not a
rewrite.** Take the facts as the source states them and restructure them into cloze cards.

**Add nothing.** No outside knowledge, no synthesized framing, no coined terminology, no
editorializing. If a fact, term, or qualifier is not in the source, it does not go on the card.

Fidelity governs *what may go on a card*. It never decides *which word gets blanked* — that is
settled by the purpose above.

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

**Shape is settled by MEASURING the reference cards, not by reading rules.** See
[style.md](style.md). Nine prose files that described shape were deleted — they drifted from the
real decks and contradicted them.

`classes/ISF/style_check.py` is where that measurement lives. It runs its predicates over the corpus
on **every call** and tiers each by its measured rate:

| tier | meaning |
|---|---|
| **BLOCKING** | the corpus violates it **zero** times — a real invariant, and it gates |
| **UNUSUAL** | the corpus violates it rarely (≤5%) — advisory, reported with the rate |
| *(silent)* | the corpus violates it often — not a rule, never reported |

**To change a style rule, change the corpus** — then `build_deck corpus` to re-pull. Do not write a
rule into prose or a prompt; that is how *"always cloze the subject"*, *"always have hints"*,
`strict_shape`'s templates and *"never force-cloze it"* all shipped as defects.
`style_check.py --derive` prints the current table.

What measurement cannot settle, it returns as **questions** rather than guesses — is this `<b>` span
a term to recall or the scope; does the hint read like English in its gap. Those stay with the
reviewer.

The driver is `classes/ISF/build_deck.py`. It automates only the deterministic steps —
**authoring and review are agent work; no script writes cards.**
