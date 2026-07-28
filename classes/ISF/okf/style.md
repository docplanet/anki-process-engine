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
3. **Lists:** a bold header, then numbered items in italics — `1.` `2.` `3.`
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

**`classes/ISF/reference/style_corpus.jsonl`** is the reference — pull or refresh it with:

```
classes/ISF/.venv/bin/python classes/ISF/build_deck.py corpus
```

It is **`ISF::Test 2::Histology::Bone`** — 37 cards the owner has reviewed and accepted.

**It is LLM-authored on purpose.** The previous reference was `Amino Acid Structures`, built by hand
over months, and it carried habits the pipeline could not reproduce — most damagingly a 22% hintless
rate. Measured, that read as "hints are optional", which became a 124-card deck that was 65%
hintless. Bone is what this harness produces when it is working: every cloze hinted, 94% two-cloze,
zero style findings. **A reference the author can actually hit beats an ideal it cannot.**

`build_deck corpus` **excludes any card tagged `wrong-*`** and reports how many it dropped.
[review-checklist.md](review-checklist.md) makes this corpus the "acceptable by definition" bar, so
a card the owner has flagged as broken must never sit in it — it would teach a reviewer to stay
silent about the exact defect they complained of. **A `wrong-*` tag means the card is still broken;
clear it once the card is fixed** and the card rejoins the corpus automatically. (All 37 are
currently clean.) When you need to know how long an answer runs, how a hint is
phrased, when to cloze an image, how a list card looks — **look at examples, don't consult a rule.**

Measured on that corpus, for orientation only (not as limits to enforce):

| | |
|---|---|
| clozes per card | 1 → 3 cards, **2 → 32**, 3 → 2 |
| hints | **73 of 73 clozes** — every one, mean 1.9 words |
| hint form | 73 of 73 end in `?` — question-form hints are house style |
| most common hints | `what?` (12), `which process?` (7), `which cells?` (6) |
| bare `what?` / `which?` | present and accepted |
| commas in hints | 0 |
| facet `<u>` | 20 of 37 cards |

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

**To change a style rule, change the corpus** — fix or add cards in
`ISF::Test 2::Histology::Bone`, then `build_deck corpus`. The prose in this file
describes the style; it does not govern it.

# What prose is still for

Judgment — the things a corpus cannot show you:

- [yield](rules/yield.md) — is this fact worth a card? What did the teacher stress?
- [accuracy](rules/accuracy.md) — is it true, is it in the source, did you invent anything?
- [process.md](process.md) — scope, what was actually taught, review before insert.
