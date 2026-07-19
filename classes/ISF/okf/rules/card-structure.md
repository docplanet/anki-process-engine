---
type: Card Authoring Rule
title: Card structure — a complete sentence, every testable role clozed, max 3 clozes
description: A cloze note is a complete true sentence tested from either side; cloze every testable role, never more than 3 distinct clozes, split beyond.
tags: [anki, card-authoring, structure, cloze, atomicity]
resource: anki://rule/card-structure
timestamp: 2026-07-13T00:00:00Z
enforcement: [judgment, mechanical]
source_defects: [wrong-structure, wrong-missing-cloze, wrong-incorrect-clozes]
---

# Foundation — what a cloze card is

A cloze note is **not** a fill-in-the-blank drill. It is a **complete, true sentence** that can
be tested from either side — a more flexible front/back. Concepts are learned better as whole
sentences than as a reveal-the-blank system, so the sentence must always read as true, natural
English (see [hint](/rules/hint.md)); the clozes only choose *which concepts get tested*.

Everything below follows from that.

# Rule

1. **The card is a complete sentence stating one fact (or one short causal chain).**
2. **Cloze every testable role in that fact** — the subject, the value, and each node of a
   relationship. A role that matters is a role you test; do not leave it as un-clozed prose. In
   particular, **the condition a fact hinges on is a testable role, not free context** — "the
   carboxyl group is deprotonated at physiological pH" hinges on *physiological pH*, so cloze it;
   leaving it visible tests a peripheral piece and makes the subject unclear.
3. **Never more than 3 distinct clozes. Two is typical.**
   **"Typical" is an observation, not a quota.** One cloze is a fully legitimate card — 110 of the
   368 reference cards have exactly one. **Never invent a second cloze to reach the typical count,
   and never replace a defective cloze just to preserve it.** When review kills a cloze, the
   default outcome is a one-cloze card; adding new content to fill the slot is authoring, and it
   re-enters review as new material.

   *Real case: a two-cloze card had a self-answering `c2`. Instead of deleting it, the repair
   swapped in the nearest adjacent transcript line to keep the count at two — content the source
   never tied to the card's fact. The count was preserved; the card got worse.*
4. **If the fact needs more than 3 roles tested, split it into linked cards** — the split is
   *forced by the ceiling*, not a stylistic choice.
5. **No un-clozed asides.** A parenthetical or qualifier that isn't worth testing should be cut,
   not left dangling ("(including germ cells)").
6. **A cloze holds only the tested term, styled uniformly.** The braces contain the answer and
   nothing else — scoping/context nouns stay *outside* the cloze, and every character inside a
   cloze carries the same role markup.
   - ❌ `{{c1::<b>lysine</b> side chain::…}}` — "side chain" is context, and it's unstyled while
     "lysine" is bold (mixed styling in one cloze).
   - ✅ `The {{c1::<b>lysine</b>::which residue?}} side chain has a <u>pKa</u> of about {{c2::<i>10.5</i>}}`
     — cloze = the term only, uniformly bold; "side chain" and the `<u>pKa</u>` facet sit outside it.
   - **Cloze the distinguishing word; keep a generic head noun visible.** When the term is
     `distinguisher + generic head` ("**carboxyl** group", "**amino** group", "**basal** lamina"),
     cloze only the distinguisher and leave the head noun visible — but **bold it too**, so the whole
     subject phrase reads bold: `The {{c1::<b>carboxyl</b>}} <b>group</b> of an amino acid has a
     <u>pKa</u> of about {{c2::<i>1.8–2.4</i>}}`. The visible head noun frames the blank and defuses most leaks — but **still give the cloze a
     hint** ([hint](/rules/hint.md)); an option-listing one often fits best here
     (`regular or irregular?`, `embryonic, proper, or specialized?`). These are ONE question listing
     options — correct under [hint](/rules/hint.md) requirement 9, and not to be confused with a
     two-question hint like `which cells, arriving how?`, which is always a defect.
7. **No cloze reveals another (no self-answering).** On a multi-cloze card, no cloze's *answer* may
   give away a sibling cloze. Watch for a value that IS the other cloze under another name:
   - ❌ `An amino acid's {{c1::<b>carboxyl group</b>}} is {{c2::<i>deprotonated (–COO⁻)</i>}}` — "–COO⁻"
     is the carboxylate, i.e. the carboxyl group, so c2 hands you c1.
   - ✅ drop the revealing token from the answer (cloze only the state: `{{c2::<i>deprotonated</i>}}`)
     and move the structural form to `Extra`. Test by hiding each cloze in turn: the visible text
     (including the *other* answers) must not contain or spell out the hidden one.

8. **Distinct clozes are distinctly styled.** Two *different* cloze numbers on a card must not share
   the same role markup — each gets its own styling (`<b>` / `<i>` / `<u>`) so the reader can tell the
   roles apart. Same styling is reserved for items that share ONE cloze number (a list, whose items
   are all `<i>`). Example: an attribute card's two clozes were both `<i>` and read identically — fix
   is one `<u>`, one `<i>` (see [recognition-and-attribute-cards](/rules/recognition-and-attribute-cards.md)).
Roles use the markup convention: `<b>` = subject, `<i>` = value/answer, `<u>` = facet — see
[mold.md](/mold.md) and [facet-underline](/rules/facet-underline.md). Put markup inside the braces:
`{{c1::<b>term</b>::hint}}`.

# Reference basis

Measured on the Neurogenetics reference deck (368 cards): distinct clozes per card are
**1 → 110 cards, 2 → 237, 3 → 21, more than 3 → 0.** Two is the norm; three is the hard ceiling.

# Examples

Before → after, from real flagged cards (`wrong-structure`). The defect is almost always the
same: **a testable role was left un-clozed.**

## S1 — subject shown but not tested

- ❌ "The <b>syncytiotrophoblast</b> secretes {{c1::<i>proteolytic enzymes</i>::secretes what?}} that enable invasion"
- ✅ "The {{c1::<b>syncytiotrophoblast</b>::which trophoblast?}} secretes {{c2::<i>proteolytic enzymes</i>::secretes what?}} that enable invasion"

## S2 — the real agent buried in an un-clozed phrase

- ❌ "{{c1::<b>Estrogen</b>}} secreted by ovarian follicular cells stimulates {{c2::<i>the proliferative phase</i>}}"
- ✅ "{{c1::<b>Follicular cells</b>::which ovarian cells?}} secrete {{c2::<i>estrogen</i>}}, which stimulates {{c3::<i>the proliferative phase of the endometrium</i>::stimulates what?}}"
- *(your Extra note: "Card should be follicular cells (cloze) secrete Estrogen (cloze) that stimulates… (cloze)")*

## S3 — a downstream node left un-clozed → make it a 3-cloze card

- ❌ "The {{c1::<b>hypothalamus</b>}} secretes {{c2::<i>GnRH</i>}}, which stimulates the anterior pituitary"
- ✅ "The {{c1::<b>hypothalamus</b>}} secretes {{c2::<i>GnRH</i>}}, which stimulates the {{c3::<i>anterior pituitary</i>::stimulates what?}}"

## Ceiling → split

The full pathway hypothalamus → GnRH → anterior pituitary → FSH/LH → ovary would need 5 clozes.
Over the ceiling, so split into two linked cards (overlapping at the shared node):

- Card A: "The {{c1::<b>hypothalamus</b>}} secretes {{c2::<i>GnRH</i>}}, which stimulates the {{c3::<i>anterior pituitary</i>}}"
- Card B: "The {{c1::<b>anterior pituitary</b>}} releases {{c2::<i>FSH and LH</i>}}, which act on the {{c3::<i>ovary</i>}}"

# Enforcement

## Mechanical (hard-gate)

- **Reject > 3 distinct cloze numbers** in a card. (Reference-proven; over-reject budget is zero.)
- **Flag a `<b>` subject that is not inside a cloze** (S1) — a displayed-but-untested subject.
  **Except on list cards**, where a visible bold header is legitimate ([mold](/mold.md) shape 3).
- **Flag a cloze that mixes a styled span with trailing/leading plain text** (rule 6), e.g.
  `<b>lysine</b> side chain`. NOTE: the current `strict_shape.py` `CHOPPED_ANSWER` check only
  catches a cloze carrying two *role* tags (`<i>`+`<u>`); it does NOT catch a styled term plus
  unstyled context in one cloze — that gap is why these shipped. Worth extending the mold.

## Judgment (generator instructions + examples)

- identify every testable role in the fact and cloze it, up to the ceiling
- pick the split point when a chain exceeds 3 roles; overlap linked cards at the shared node
- cut non-testable asides rather than leaving them un-clozed
