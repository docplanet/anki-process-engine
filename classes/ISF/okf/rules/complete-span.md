---
type: Card Authoring Rule
title: The answer is a complete span
description: A cloze answer covers the entire tested value — never a fragment with the rest of that value left as plain text outside the cloze.
tags: [anki, card-authoring, cloze, answer, span]
resource: anki://rule/complete-span
timestamp: 2026-07-13T00:00:00Z
enforcement: [judgment, mechanical]
source_defects: [wrong-style-off]
---

# Rule

The `<i>` answer cloze must cover the **entire value being tested** — the whole term, definition,
or phrase — never a **fragment** of it with the remainder left as plain text outside the braces.

If a single answer is "ionic (electrostatic) bond between oppositely charged side chains," then the
whole thing is one `<i>` span. Do not cloze "ionic (electrostatic) bond" and leave "between
oppositely charged side chains" dangling after it — that splits one answer and lets the card trail
off past the blank.

# Not the same as legitimate trailing text

A card may carry trailing text *when that text is a separate scope/fact, not part of the answer*
(the reference deck does this — e.g. "…double every {{c1::48–72 hours}} for the first 2 months").
The test is: **is the plain text outside the cloze part of the same value the cloze is testing?**
- If yes → it belongs *inside* the answer span (this rule).
- If no (a separate qualifier/scope) → it may sit outside, but consider whether it earns its place
  ([yield](/rules/yield.md)).

The failure this rule names is specifically **fragmenting one answer**, not "any text after a cloze."

# Examples

| ❌ split answer (fragment clozed, rest trailing) | ✅ complete span |
|---|---|
| `A {{c1::<b>salt bridge</b>}} is an {{c2::<i>ionic (electrostatic) bond</i>}} between oppositely charged side chains` | `A {{c1::<b>salt bridge</b>}} is an {{c2::<i>ionic (electrostatic) bond between oppositely charged side chains</i>}}` |

Reference cards keep the answer whole and let it close the card: "The {{c1::cerebellum}} controls
{{c2::body movements and motor behaviors}}" — the full value is one span, ending the card.

# Enforcement

## Mechanical (candidate)

- **Flag plain text between a `</i>` answer close and the end of the card** when that text reads as a
  continuation of the answer (e.g. begins with a preposition/conjunction: "between", "of", "and",
  "in", "with"). Route to review — a human confirms whether it's a split answer (fold in) or a
  separate scope (leave/trim). Validate against the reference so genuine fact-completion trailing
  isn't over-flagged.

## Judgment (generator instructions)

- Identify the full value being tested and cloze all of it as one `<i>` span.
- If text after the answer completes the same value, it goes inside the span; if it's a distinct
  scope, decide by yield whether it belongs on the card at all.

# Related

- [card-structure](/rules/card-structure.md) rule 6 — a cloze holds only the tested term, styled
  uniformly. This rule is its complement: a cloze holds *all* of the tested term.
- [subject-first](/rules/subject-first.md) — subject leads; combined with this, a card reads
  subject → complete answer.
