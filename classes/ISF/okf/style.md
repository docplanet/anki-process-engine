---
type: Style Guide
title: Card style
description: The whole card style, as stated by the deck owner. Shape questions are answered by the reference corpus, not by prose.
tags: [anki, card-authoring, style]
timestamp: 2026-07-18T00:00:00Z
---

# The style

1. **`<b>` bold, `<u>` underline, `<i>` italics.** Bold = the subject. Underline = the facet
   (the aspect being asked about). Italics = the answer/value.
2. **Usually clozed, not always.** A styled span is normally inside `{{c1::…}}`, but a visible
   bold subject or a visible underlined facet is fine and common.
3. **Lists:** a clozed header, a visible `<u>` facet, then ONE NUMBERED LINE PER ITEM. The
   numbers sit **outside** the braces and are **not** italicised — they are scaffolding, not
   answers. Every item shares one cloze number, so the whole list is one card view. See `ref-05`.
4. **Every cloze gets a hint. No exceptions.** Stated directly by the deck owner.

   > The reference deck keeps this perfectly — **73 of 73 clozes hinted** — so it is also a
   > BLOCKING rule in `style_check`. It was briefly softened to "hint the ones that need it — not
   > every cloze", on the evidence that the *old* hand-built reference was 22% hintless. The author
   > read that as permission and returned a 124-card deck that was **65% hintless**. That old deck
   > is no longer the reference, for exactly this reason.
5. **Hints read like English** — substituted into the blank, the sentence reads naturally.

That is the whole style guide.

# Everything else about shape comes from the corpus

**Do not answer a shape question from prose. Read the cards.**

**`classes/ISF/reference_cards.jsonl`** is the reference — **six hand-built cards, one per shape,
tracked in git.** Not pulled from a deck: an authority has to be right before it is large, and the
deck it used to be pulled from carried its own defects (an un-clozed subject, a hint that was not a
complete thought, a card with two `<b>` spans). The six are:

| | shape |
|---|---|
| `ref-01` | two clozes — subject + answer |
| `ref-02` | two clozes + a **visible** facet |
| `ref-03` | three clozes — an either/or choice wears `<u>`, the value wears `<i>` |
| `ref-04` | one cloze — the subject is the **frame**, so it stays visible |
| `ref-05` | list — numbers **outside** the braces, one item per line, all sharing `c2` |
| `ref-06` | image — the picture is one cloze, the term the other |

`ref-04` and `ref-06` are the two that must not be dropped. Without `ref-04` the author clozes every
subject it sees; without `ref-06` it has no model for a recognition card.

**To change the style, edit `classes/ISF/reference_cards.py` and regenerate.** The rules recompute
from whatever those cards do — `style_check.py --derive` prints the table.

Measured on the six, for orientation only (not as limits to enforce):

| | |
|---|---|
| clozes per card | 1 → 2 cards, 2 → 3, 3 → 1 |
| hints | **every cloze**, mean ~2.5 words |
| hint form | all end in `?` — question-form hints are house style |
| shapes with a `<u>` facet | 4 of 6 |
| commas in hints | 0 |

**A previous version of this rulebook was calibrated to a different deck (AnKing Neurogenetics)
and concluded that hints should be bare noun phrases without question marks. That is wrong for
these decks.** It also required the subject to be clozed and flagged visible bold subjects as
defects; the reference corpus does that constantly. Both rules were prose inventions that the
owner's actual cards contradict. This is why shape is settled by examples.

# Do not add a rule to this file

Style rules have shipped as defects five times because someone reasoned about them instead of
measuring them: *"always cloze the `<b>` subject"*; `strict_shape`'s T1–T5 templates (measured from
the deprecated AnKing deck); *"never force-cloze it"* (four hormone cards shipped with the hormone
visible); and — the other direction — *"hint only the clozes that need it"*, inferred from the old
reference deck's 22% hintless rate, which produced a 124-card deck that was 65% hintless.

**A measurement is not automatically a rule.** The old deck being 22% hintless described a habit of
one hand-built deck; it was never permission. That is what changing the reference deck fixes.

**Rules live in `classes/ISF/style_check.py`, derived from this corpus on every call.** A predicate
the corpus violates zero times BLOCKS; one it breaks rarely advises; one it breaks often is not a
rule. `tests/test_style_check.py` asserts that property, so a rule the corpus contradicts fails CI
rather than shipping.

```
classes/ISF/.venv/bin/python classes/ISF/style_check.py --derive          # the live rule table
classes/ISF/.venv/bin/python classes/ISF/style_check.py --deck <cards>    # audit a deck
```

**To change a style rule, change the reference cards** — edit `classes/ISF/reference_cards.py`
and regenerate `reference_cards.jsonl`. The prose in this file describes the style; it does not
govern it.

# What prose is still for

Judgment — the things a corpus cannot show you:

- [yield](rules/yield.md) — is this fact worth a card? What did the teacher stress?
- [accuracy](rules/accuracy.md) — is it true, is it in the source, did you invent anything?
- [process.md](process.md) — scope, what was actually taught, review before insert.
