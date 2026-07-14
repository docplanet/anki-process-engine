---
type: Card Authoring Rule
title: Underline the facet
description: The aspect/category word that frames a fact is underlined (<u>); if that facet is itself testable, cloze it too.
tags: [anki, card-authoring, markup, facet, underline]
resource: anki://rule/facet-underline
timestamp: 2026-07-13T00:00:00Z
enforcement: [judgment, mechanical]
source_defects: [wrong-missing-underline]
---

# Rule

Mark the **facet** with `<u>…</u>`. The facet is the word naming the *aspect, category,
dimension, or axis* a fact is about — the lens of the card. It is neither the subject (`<b>`) nor
the answer (`<i>`); it frames them.

A facet is most often the **category word that frames the answer**: "adhesion molecules
including ___", "an epithelium called ___", "a DNA segment known as ___", "the primordium of ___".

**A facet may be plain or clozed:**
- **plain** when it's context, not a thing to test: `<u>adhesion molecules</u>`
- **clozed *and* underlined** when the facet is itself worth testing: `{{c2::<u>simple squamous epithelium</u>}}`.
  Markup goes inside the braces. A testable facet is a clozed role — see
  [card-structure](/rules/card-structure.md) (cloze every testable role, max 3).

# Reference basis

155 of 368 reference cards (42%) use `<u>`. What it wraps, from the deck: `morphology`,
`DNA segment`, `nuclei`, `pathway`, `cerebral cortex`, `the main difference between neurons`,
`increase`/`decrease` — all facet/aspect words, never the bare subject or answer.

- "…display {{c2::<i>…</i>}} <u>morphology</u> and are located in {{c3::<i>…</i>}}"
- "…mutations involve a <u>DNA segment</u> known as {{c2::<i>…</i>}}"

# Examples

From real flagged cards (`wrong-missing-underline`).

| fact | facet | plain or clozed |
|------|-------|-----------------|
| "…mediated by adhesion molecules including {{integrins and L-selectins}}" | `adhesion molecules` | plain → `<u>adhesion molecules</u>` |
| "All {{blood vessels}} are lined by a simple squamous epithelium called {{endothelium}}" | `simple squamous epithelium` | **clozed** → `{{c2::<u>simple squamous epithelium</u>}}` (3-cloze card) |
| "The connecting stalk is the primordium of the {{umbilical cord}}" | `primordium` | plain → `<u>primordium</u>` |
| "…completes the first meiotic division, forming {{a secondary oocyte + polar body}}" | `first meiotic division` | plain → `<u>first meiotic division</u>` |

# Enforcement

## Mechanical (soft assist)

- **Flag a framing word before an answer cloze with no nearby `<u>`.** When one of
  `including`, `called`, `known as`, `type of`, `such as`, `the … of`, sits immediately before an
  `<i>` answer cloze and no `<u>` appears in the card, flag it as a likely missing facet. Route to
  review (not hard-reject) — the human/generator confirms and decides plain vs. clozed. Validate
  against the reference so it does not over-flag.

## Judgment (generator instructions)

- identify the aspect/category word that frames the fact and underline it
- decide plain vs. clozed by yield: if the facet is itself worth testing, cloze it (inside `<u>`)
