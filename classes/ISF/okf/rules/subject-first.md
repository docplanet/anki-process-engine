---
type: Card Authoring Rule
title: The subject leads the card
description: A card opens on its subject term, never on a statistic, an "Of the…" clause, or temporal scene-setting.
tags: [anki, card-authoring, structure, sentence]
resource: anki://rule/subject-first
timestamp: 2026-07-13T00:00:00Z
enforcement: [judgment, mechanical]
source_defects: [wrong-style-off, wrong-sentence-structure]
---

# Rule

A card **opens on its subject** — the named thing it is testing (the `<b>` term). The reader
should hit the key term first, not wade through scene-setting to reach it.

Never open a card with:
- a **statistic or quantity** ("Only about 1% of sperm…")
- an **"Of the …" / partitive clause** ("Of the two parts of the basement membrane…")
- **temporal or circumstantial scene-setting** ("Prior to…", "During routine fixation…",
  "At puberty, of the oocytes remaining…")

The subject may be preceded only by a bare article ("The", "A", "An") or nothing at all.

# Reference basis

Measured against the Neurogenetics reference deck (368 cards): the subject leads essentially
every card — only **1 of 368** opens with a scene-setting clause. Cards lead with the term
directly, with or without an article:

- "The {{c1::<b>brain stem</b>::brain part}} processes information between …"
- "{{c1::<b>Gyri</b>}} are {{c2::<i>elevated ridges of the cerebral cortex</i>::what?}}"
- "An {{c1::<b>axon</b>}} conveys information from {{c2::<i>the soma to its terminal buttons</i>}}"

# Examples

Before → after, from real flagged cards (`wrong-style-off`).

| ❌ before (subject buried) | ✅ after (subject leads) |
|---------------------------|-------------------------|
| "Only about {{c1::1%}} of {{c2::<b>sperm</b>}} deposited in the vagina enter the cervix" | "{{c1::<b>Sperm</b>}} entering the cervix number only {{c2::<i>~1% of those deposited</i>::what fraction?}}" |
| "Of the two parts of the {{c1::<b>basement membrane</b>}}, the {{c2::<i>reticular lamina</i>}} is the more diffuse layer" | "The {{c1::<b>reticular lamina</b>::basement-membrane part}} is {{c2::<i>the more diffuse, fibrous layer beneath the basal lamina</i>}}" |
| "Of the primary oocytes remaining at puberty, only about {{c1::500-700}} reach ovulation" | "Of the primary oocytes present at puberty, {{c1::<i>~500-700</i>::how many?}} reach ovulation" — *still opens on "Of the"; rewrite so the subject leads* → "{{c1::<b>Primary oocytes</b>}} reaching ovulation number about {{c2::<i>500-700</i>::how many?}}" |

The reshaping sometimes changes which term is the subject (e.g. the reticular lamina becomes
the subject rather than the basement membrane) — pick the term the card is really testing and
lead with it.

# Enforcement

## Mechanical (hard-gate candidate)

- **Reject an opening that is not the subject.** If the visible text before the first `<b>`
  subject cloze matches a scene-setting opener — starts with a digit/percentage, or with a
  lowercase-tolerant `of the`, `only`, `during`, `prior to`, `at ` + noun, `when`, `for the` —
  flag the card. Validate against the reference deck first so the openers list does not
  over-reject house-style cards (the reference's 1 exception tells us the false-positive budget
  is tiny).

## Judgment (generator instructions + examples)

- choose the term the card actually tests as the subject, and lead with it
- reword so the fact still reads naturally once the subject is fronted
