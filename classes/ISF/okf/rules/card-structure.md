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
   relationship. A role that matters is a role you test; do not leave it as un-clozed prose.
3. **Never more than 3 distinct clozes. Default to 2.**
4. **If the fact needs more than 3 roles tested, split it into linked cards** — the split is
   *forced by the ceiling*, not a stylistic choice.
5. **No un-clozed asides.** A parenthetical or qualifier that isn't worth testing should be cut,
   not left dangling ("(including germ cells)").

Roles use the markup convention: `<b>` = subject, `<i>` = value/answer, `<u>` = facet
(see [missing-underline] once written). Put markup inside the braces: `{{c1::<b>term</b>::hint}}`.

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

## Judgment (generator instructions + examples)

- identify every testable role in the fact and cloze it, up to the ceiling
- pick the split point when a chain exceeds 3 roles; overlap linked cards at the shared node
- cut non-testable asides rather than leaving them un-clozed
