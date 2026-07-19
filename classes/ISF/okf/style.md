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
4. **Always have hints.**
5. **Hints read like English** — substituted into the blank, the sentence reads naturally.

That is the whole style guide.

# Everything else about shape comes from the corpus

**Do not answer a shape question from prose. Read the cards.**

**`classes/ISF/reference/style_corpus.jsonl`** is the reference — pull or refresh it with:

```
classes/ISF/.venv/bin/python classes/ISF/build_deck.py corpus
```

It is **84 cards** from `ISF::Test 2::Biochemistry::Amino Acid Structures` that the deck owner has
reviewed and accepted.

`build_deck corpus` **excludes any card tagged `wrong-*`** and reports how many it dropped.
[review-checklist.md](review-checklist.md) makes this corpus the "acceptable by definition" bar, so
a card the owner has flagged as broken must never sit in it — it would teach a reviewer to stay
silent about the exact defect they complained of. **A `wrong-*` tag means the card is still broken;
clear it once the card is fixed** and the card rejoins the corpus automatically. (All 84 are
currently clean.) When you need to know how long an answer runs, how a hint is
phrased, when to cloze an image, how a list card looks — **look at examples, don't consult a rule.**

Measured on that corpus, for orientation only (not as limits to enforce):

| | |
|---|---|
| clozes per card | 1 → 6 cards, 2 → 73, 3 → 5 |
| hints | 111, mean **1.7 words** |
| hint form | 107 of 111 end in `?` — question-form hints are house style |
| most common hints | `which AA?` (23), `abbreviations?` (20), `classification?` (20) |
| bare `what?` / `which?` | present and accepted |
| commas in hints | 0 |

**A previous version of this rulebook was calibrated to a different deck (AnKing Neurogenetics)
and concluded that hints should be bare noun phrases without question marks. That is wrong for
these decks.** It also required the subject to be clozed and flagged visible bold subjects as
defects; the reference corpus does that constantly. Both rules were prose inventions that the
owner's actual cards contradict. This is why shape is settled by examples.

# What prose is still for

Judgment — the things a corpus cannot show you:

- [yield](rules/yield.md) — is this fact worth a card? What did the teacher stress?
- [accuracy](rules/accuracy.md) — is it true, is it in the source, did you invent anything?
- [process.md](process.md) — scope, what was actually taught, review before insert.
