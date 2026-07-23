---
type: Card Authoring Rule
title: Card structure — a complete sentence, every testable role clozed, max 3 clozes
description: A cloze note is a complete true sentence tested from either side; cloze every testable role, never more than 3 distinct clozes, split beyond.
tags: [anki, card-authoring, structure, cloze, atomicity]
resource: anki://rule/card-structure
timestamp: 2026-07-21T00:00:00Z
enforcement: [judgment, mechanical]
source_defects: [wrong-structure, wrong-missing-cloze, wrong-incorrect-clozes]
---

> **This rule was deleted once and that was the mistake.** It was removed in the "collapse to a
> 5-line style guide + the corpus" cleanup, filed as *shape prose that drifted*. It is not style
> marking — it is card **construction** (which roles become blanks), and the corpus cannot teach it
> for fact shapes it lacks (chain facts: A does B which does C). Its absence is exactly what let a
> card ship testing the cell and the hormone but leaving "corpus luteum" as visible prose. Restored.

# Foundation — what a cloze card is

A cloze note is **not** a fill-in-the-blank drill. It is a **complete, true sentence** that can
be tested from either side — a more flexible front/back. The sentence must read as true, natural
English; the clozes only choose *which concepts get tested*.

# Rule

1. **The card is a complete sentence stating one fact (or one short causal chain).**
2. **Cloze every testable role in that fact** — the subject, the value, and each node of a
   relationship. A role that matters is a role you test; do not leave it as un-clozed prose. In
   particular, **the condition a fact hinges on is a testable role, not free context** — "the
   carboxyl group is deprotonated at physiological pH" hinges on *physiological pH*, so cloze it;
   leaving it visible tests a peripheral piece.
3. **Never more than 3 distinct clozes. Two is typical.**
   **"Typical" is an observation, not a quota.** One cloze is a fully legitimate card. **Never
   invent a second cloze to reach the typical count, and never replace a defective cloze just to
   preserve it.** When review kills a cloze, the default outcome is a one-cloze card.
4. **If the fact needs more than 3 roles tested, split it into linked cards** — the split is
   *forced by the ceiling*, not a stylistic choice.
5. **No un-clozed asides.** A parenthetical or qualifier that isn't worth testing should be cut,
   not left dangling ("(including germ cells)").
6. **A cloze holds only the tested term, styled uniformly.** The braces contain the answer and
   nothing else — scoping/context nouns stay *outside* the cloze, and every character inside a
   cloze carries the same role markup.
   - ❌ `{{c1::<b>lysine</b> side chain::…}}` — "side chain" is context, unstyled, inside the cloze.
   - ✅ `The {{c1::<b>lysine</b>::which residue?}} side chain has a <u>pKa</u> of about {{c2::<i>10.5</i>}}`
   - **Cloze the distinguishing word; keep a generic head noun visible** — for `distinguisher +
     generic head` ("**carboxyl** group", "**basal** lamina"), cloze only the distinguisher and
     leave the head visible **but bold it too**, then still give the cloze a hint (an option-listing
     one often fits: `regular or irregular?`).
7. **No cloze reveals another (no self-answering).** On a multi-cloze card, no cloze's *answer* may
   give away a sibling. Watch for a value that IS the other cloze under another name:
   - ❌ `An amino acid's {{c1::<b>carboxyl group</b>}} is {{c2::<i>deprotonated (–COO⁻)</i>}}` — "–COO⁻"
     is the carboxylate, so c2 hands you c1.
   - Test by hiding each cloze in turn: the visible text (including the *other* answers) must not
     contain or spell out the hidden one.
8. **Distinct clozes are distinctly styled — ONE red answer per card.** Two *different* cloze
   numbers must not share the same role markup. **The corpus is unambiguous: 0 of 84 cards have two
   `<i>` answers.** The house style is one bold subject, one red `<i>` answer, one optional teal
   `<u>` facet — never two reds. A chain fact (A secretes B, which maintains C) does **not** become
   a second red answer; either the extra node is the subject/context of the sentence, or the fact
   is **split into two linked cards** (rule 4). Same styling is reserved for the items of ONE list
   cloze (all `<i>`).

**Complete span.** The `<i>` answer cloze covers the *entire* value tested — do not cloze a fragment
and leave the rest as trailing prose (❌ `{{c1::<i>ionic bond</i>}} between oppositely charged side
chains` — cloze the whole answer).

**Whole insight.** On a causal/explanatory clause (*because…*, *which…*, *so that…*), cloze the whole
mechanism, not just the end-state. If the card's point is *why*, the *why* is the answer.

Roles: `<b>` = subject, `<i>` = value/answer, `<u>` = facet (see [style.md](../style.md)). Put markup
inside the braces: `{{c1::<b>term</b>::hint}}`.

# The two is normal, one is fine, three is the ceiling

Measured on the reference corpus, prose (non-list, non-image) cards are overwhelmingly 2-cloze; a
single-cloze prose card that leaves a second testable role visible is the deck's most common
under-cloze defect. Three is the hard ceiling; beyond it, split.

# Examples

Before → after, from real flagged cards. The defect is almost always the same: **a testable role
was left un-clozed.**

## S1 — a downstream node left untested, fixed WITHOUT a second red answer

A chain "A secretes B, which maintains C" has a subject and two values. The corpus never puts two
values in red on one card, so you do **not** cloze both B and C as `<i>`. Two correct options:

- **Split into two linked cards** (each one red answer):
  - "The {{c1::<b>syncytiotrophoblast</b>::which layer?}} secretes {{c2::<i>hCG</i>::which hormone?}}"
  - "{{c1::<b>hCG</b>::which hormone?}} maintains the {{c2::<i>corpus luteum</i>::maintains what?}}"
- ❌ **Wrong:** "…secretes {{c2::<i>hCG</i>}}, which maintains the {{c3::<i>corpus luteum</i>}}" — two
  red answers, which the corpus has 0 of. (This was a real mistake: the card was "fixed" this way,
  and it took a look at the rendered card — two reds — to see the style was wrong.)

## S2 — context or subject mis-coloured as an answer

Often a card has only one real answer and a second span is context or the subject, wrongly wrapped
in `<i>`:

- ❌ "{{c2::<i>After gastrulation</i>::when?}}, the <b>primitive streak</b> {{c1::<i>disappears</i>}}"
  — "After gastrulation" is temporal context, not an answer; colouring it red makes two reds.
- ✅ "After gastrulation, the <b>primitive streak</b> {{c1::<i>disappears</i>::what happens to it?}}"
  — one red answer; the context stays plain.
- ❌ "<b>Gastrulation</b> converts the {{c1::<i>bilaminar disc</i>}} into a {{c2::<i>trilaminar disc</i>}}"
  — the starting material is context.
- ✅ "<b>Gastrulation</b> converts the bilaminar disc into a {{c1::<i>trilaminar disc</i>::into what?}}"

# Enforcement

- **Mechanical (gate):** `strict_shape` rejects > 3 distinct clozes and a `<b>` subject not
  inside a cloze (except list headers). It does **not** see an un-clozed testable *value* left as
  prose, self-answering, complete-span, or whole-insight — **those are the reviewer's job** (the
  tool-less review step inside `build_deck run`).
- **Judgment:** identify every testable role and cloze it up to the ceiling; split a chain that
  exceeds 3; cut non-testable asides rather than leaving them un-clozed.
