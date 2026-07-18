---
type: Card Authoring Reference
title: The mold — roles, colors, and the three card shapes
description: The canonical statement of the card shape that strict_shape.py enforces — the role/color system, the three allowed shapes, and the hard rejects.
tags: [anki, card-authoring, mold, markup, shape]
resource: anki://reference/mold
timestamp: 2026-07-17T00:00:00Z
---

# What this is

The canonical description of **the mold** — the card shape enforced mechanically by
`classes/ISF/strict_shape.py`. The [rules](/index.md) say *what makes a card good*; this file says
*what shape a card must have*. Measured from the AnKing Neurogenetics reference deck (368 cards),
not invented.

If a card fails `strict_shape.py`, this file explains what it wanted.

# The three roles → three colors

The color of every phrase encodes its **role**, so a card is readable at a glance. Apply it *while
authoring*, never as an afterthought.

| Wrap in | Renders | Role |
|---|---|---|
| `<b>…</b>` | mauve `#C695C6` | **SUBJECT** — the named thing the card is about |
| `<i>…</i>` | red `IndianRed` | **ANSWER** — the value / description / consequence |
| `<u>…</u>` | teal `#5EB3B3` | **FACET** — an aspect/part/condition that *scopes* the subject |
| *(none)* | plain / green in a cloze | connective scaffold — "is", "controls", "of the" |

Measured frequency: `<b>` on 98% of cards, `<i>` on 98% (usually exactly one of each), `<u>` on
only **42%** — the facet is the exception, not the rule. Never add a third color just to have one.

**A role is not a position.** Any of the three may be the clozed blank or left as plain context —
you cloze whichever role the card is testing.

## Markup mechanics

- **Wrap INSIDE the braces:** `{{c1::<b>anaphase</b>::which phase?}}` — *not*
  `<b>{{c1::anaphase}}</b>`. This keeps the term colored on sibling cards where the cloze is inactive.
- **Every role-bearing phrase gets its color**, clozed or not (a bold subject sitting as visible
  context on a list card is still `<b>`).
- **Balance every tag** — each `<b>`/`<i>`/`<u>` needs its close tag; the linter enforces this.
- The answer is **one italic span**, even when long — never chopped into several colored blanks
  ("italics all over" is a defect).

# The three shapes

## 1 · Two-sided — the default

Bold subject ↔ italic answer, two clozes, terse.

```
The {{c1::<b>brain stem</b>::brain part}} controls {{c2::<i>automatic behaviors necessary for survival</i>::what functions?}}
The {{c1::<b>Pineal gland</b>}} secretes {{c2::<i>melatonin</i>::what?}}
```

## 2 · Facet — `<u>` scopes the question (~26–42% of cards)

The facet may be plain context **or** itself be clozed:

```
facet as context:  The {{c1::<b>central sulcus</b>}} of the <u>cerebral cortex</u> {{c2::<i>separates motor and sensory areas</i>}}
facet clozed:      <b>Cerebral cortex</b> {{c1::<u>sensory areas</u>::which areas?}} {{c2::<i>control conscious awareness of sensation</i>}}
```

Cloze the facet when it's the distinguishing/testworthy term; leave it plain for pure orientation.
See [facet-underline](/rules/facet-underline.md).

## 3 · Numbered list — a set recalled together (~24–27% of cards)

```
The {{c2::<b>diencephalon</b>::which brain part?}} contains:<br><br>1. {{c1::<i>Pineal gland</i>}}<br>2. {{c1::<i>Thalamus</i>}}<br>3. {{c1::<i>Hypothalamus</i>}}
```

- **Every item shares ONE cloze number** so they reveal together.
- **The header may be clozed or left visible — judge by ambiguity.** Cloze it when the item list
  uniquely identifies it, so "given these items, name the thing" is a real test. Leave it **bold and
  visible** when many subjects could own that list, or when clozing it would need a coined hint —
  a nonsense header cloze is worse than none. When in doubt, leave it visible.
- Each item is exactly one `<i>` span, on its own line, capitalized, no trailing punctuation.
- **Hint the header if you cloze it; leave the item clozes bare** — the header is the cue, and
  per-item hints would just repeat it ([hint](/rules/hint.md), the one exception).
- Never chop an item into italic-plus-underline pieces, and never put a "term — examples" bundle in
  an item.
- Note this is the one place repeated styling is correct — items share a cloze number, so they share
  a style (see [card-structure](/rules/card-structure.md) rule 8).

# Hard rejects (what `strict_shape.py` refuses)

Beyond the shapes above:

- **`FLATTENED_MAPPING`** — never flatten a mapping into two parallel multi-item blobs.
  ❌ `{{c1::<b>cranial, caudal, ventral, dorsal</b>}} correspond to {{c2::<i>superior, inferior, anterior, posterior</i>}}`
  ✅ four atomic cards, one per pair.
- **`TRAILING_FACT`** — never append a dangling second fact after the answer via a dash / `;` / `:`.
  ❌ `The {{c1::<b>carbonyl carbon</b>}} is {{c2::<i>the C=O carbon</i>}} — C1 in aldoses, C2 in ketoses`
  ✅ two cards (or trim if covered elsewhere).
- **`TWO_ANSWER_CLOZES`** — on a non-list card, exactly ONE italic-answer cloze number.
- **`NO_ITALIC_ANSWER`** / **`UNCLOZED_ANSWER`** — the answer must be a clozed `<i>` span.
- **`CHOPPED_ANSWER`** — one cloze carries one role; never mix roles inside a single cloze.
- **`SUBJECT_NOT_LEADING`** — the `<b>` subject must appear before any `<u>` facet.
- **No arrows** (`→`, `->`) anywhere.
- **Terse** — roughly 10–14 words revealed; long or 3+ facts means split.
- **No terminal period** — see [no-terminal-period](/rules/no-terminal-period.md).

# Verify

```
classes/ISF/build_deck.py gate <cards.jsonl>      # or: classes/ISF/strict_shape.py <cards.jsonl>
```
Must print `N/N conforming (0 rejected)`. The printed *facet worklist* is advisory, not a failure.

**Exempt:** recognition/attribute cards (image⇄name, entity→attributes) are a separate genre and are
expected to fail this mold — see
[recognition-and-attribute-cards](/rules/recognition-and-attribute-cards.md).
