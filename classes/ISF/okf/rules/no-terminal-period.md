---
type: Card Authoring Rule
title: No terminal punctuation
description: A card never ends with a sentence-final period or comma; it ends on the answer.
tags: [anki, card-authoring, punctuation, mechanical]
resource: anki://rule/no-terminal-period
timestamp: 2026-07-13T00:00:00Z
enforcement: [mechanical]
source_defects: [wrong-style-off]
---

# Rule

A card carries **no sentence-final punctuation.** The rendered card (answer substituted in, hints
dropped) ends on the answer token itself — no trailing `.` and no trailing `,`.

# Reference basis

Measured on the Neurogenetics reference deck (368 cards): **0 end with a period, 0 end with a
comma.** The terminal character is always the last letter of the answer (or a closing paren). This
is a hard, exceptionless house convention. It pairs with [complete-span](/rules/complete-span.md):
the answer is whole *and* closes the card, with nothing — not even a period — after it.

Applies to the visible card body. A period *inside* a cloze answer that is genuinely part of the
value (e.g. an abbreviation) is a different matter; this rule is about the card's terminal char.

# Examples

- ✅ `The {{c1::<b>cerebellum</b>::brain part}} controls {{c2::<i>body movements and motor behaviors</i>::what?}}`
- ❌ `The {{c1::<b>cerebellum</b>}} controls {{c2::<i>body movements and motor behaviors</i>}}.` — trailing period

# Enforcement

## Mechanical (hard-gate)

- **Reject a card whose rendered text ends in `.` or `,`** (strip trailing whitespace/`<br>`/`&nbsp;`
  first). Trivial and exceptionless per the reference — over-reject budget is zero.
