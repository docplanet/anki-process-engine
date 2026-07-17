---
type: Card Authoring Rule
title: Cloze the whole insight, not a fragment of it
description: The answer is the entire high-yield unit — for a causal/explanatory clause, cloze the whole clause, not just its end-state.
tags: [anki, card-authoring, cloze, yield, answer]
resource: anki://rule/whole-insight
timestamp: 2026-07-13T00:00:00Z
enforcement: [judgment]
source_defects: [wrong-low-yield]
---

# Rule

Before clozing, ask **"what is the insight this card teaches?"** — and cloze *that whole thing*.
The answer is the entire high-yield unit, not a convenient fragment of it.

This bites hardest on **causal / explanatory clauses** ("… because X", "… which does Y", "… so that
Z", "… due to W"). The insight is the *whole* explanation. Do **not** cloze only its tail (the
end-state, a predicate fragment) while leaving the clause's subject and verb visible — that tests a
low-yield fragment and hands over the crux.

# Why (the yield argument)

If the card reads "…breaks at low pH because aspartate becomes {{protonated and neutral}}", the
reviewer sees "aspartate becomes ___" and only has to supply the end-state. They never recall the
actual mechanism — *which* residue changes and *that* it changes. The examinable insight is the full
clause "aspartate becomes protonated and neutral"; clozing a fragment of it is low-yield
([yield](/rules/yield.md)).

# Example

| ❌ fragment clozed (crux given away) | ✅ whole insight clozed |
|---|---|
| `…breaks at low pH because aspartate becomes {{c3::<i>protonated and neutral</i>}}` | `…breaks at low pH because {{c3::<i>aspartate becomes protonated and neutral</i>}}` |

Hiding the cloze should leave a genuine question: "…breaks at low pH because ___" demands the full
mechanism, not just an adjective.

# Distinction from complete-span

- [complete-span](/rules/complete-span.md): given the answer, don't split it into a clozed fragment
  plus dangling text. (About not fracturing a *known* answer.)
- **This rule**: *identify* the answer correctly in the first place — the whole insight/clause is the
  answer, not its tail. (About choosing the right *unit* to cloze.)

They compound: pick the whole insight (this rule), then cloze all of it as one span (complete-span).

# Enforcement

## Judgment (generator instructions + review)

- For each card, name the insight in one phrase, then confirm the cloze covers that whole phrase.
- On any "because / which / so that / due to" clause, the default is to cloze the entire clause; only
  leave part visible if that part is genuinely given context, not the mechanism.
- Review check: hide the cloze — does the visible stem still reveal the mechanism (subject + verb of
  the explanation)? If yes, the cloze is too small.
