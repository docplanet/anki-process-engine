---
type: Card Authoring Rule
title: Accuracy — every fact must match its cited source
description: A card may assert only what its cited source supports; added qualifiers, distortions, or ungrounded facts flag for accuracy review.
tags: [anki, card-authoring, accuracy, provenance, review]
resource: anki://rule/accuracy
timestamp: 2026-07-13T00:00:00Z
enforcement: [human-review]
source_defects: [wrong-information]
---

# Rule

A card may assert **only what its cited source supports** — no more. The `Extra` field carries
the provenance (the slide image and/or a verbatim `Source:` line); the card's fact must be
exactly grounded in it. Any of the following is a defect:

- **Added qualifier / embellishment** — the card states more than the source
  ("takes ~2 months" → "takes ~2 months **per cycle**").
- **Distortion** — the card changes the source's meaning.
- **Ungrounded fact** — the source is missing, or too garbled to support the claim
  (a fact derived from an unreadable transcript line is not grounded).
- **Factual error** — the claim is wrong on the subject matter, regardless of source.
- **Invented or misapplied terminology (editorializing)** — a term or framing no one in the field
  uses, or a real term applied where it's non-standard, *even when the underlying fact is true*.
  This is a distinct, sneaky failure: a made-up label passes a factual check because it's
  "true-adjacent." Example: calling a **free** amino acid's α-amino/α-carboxyl groups the
  "**backbone** amine/acid" — "backbone" is real (the peptide main chain) but a free amino acid
  has no backbone, so the usage is invented. Also: pseudo-classification subtypes ("cyclic",
  "imino acid" for proline), and hedged characterizations ("borderline", "the most basic", loose
  qualifiers like "hydrolyzable"). **Rule: cite or omit, never coin.** Use only established field
  terminology; if no standard term fits a hint or label, leave it out (a hint is optional) rather
  than invent one. Prefer the source's own words.

# Status — review gate, not mechanical

Accuracy cannot be checked by shape tooling. A card whose fact is not clearly supported by its
cited source is **flagged for accuracy review and does not ship until a human confirms it**
(consistent with the project rule that an open flag must be resolved, never silently carried).
For clinical/board facts, confirmation is a human/expert call.

# Examples

From real flagged cards (`wrong-information`).

| card claim | source | defect |
|-----------|--------|--------|
| "{{oogenesis}} takes {{~2 months per cycle}}" | "…takes ~2 months" | added "per cycle" |
| "In {{pseudostratified epithelium}}, {{not all cells reach the free surface}}" | garbled transcript ("So only one cell where in depth…") | ungrounded — source can't support it |

# Enforcement

## Citing a transcript-only fact (the title-slide case)

A slide is often just a **title over an image**, with the actual content spoken. When the fact comes
from the transcript but was said *over* a slide:

- **Show the slide image** in `Extra` (it's the visual referent), **but the `Source:` line must be
  the verbatim transcript quote**, labelled as such.
- **Never imply the slide states it.** `Source: Slide 5` on a transcript-only fact is a false
  citation — the reviewer checking the slide will find nothing.
- Set the `source` field to `Transcript` (or `Slide N / Transcript` when both genuinely contribute).

```
Extra: <img src="…slide-05.jpg"><br><br><b>Source (transcript):</b> "…verbatim words…"
source: Transcript
```

A quote presented as verbatim must be **exactly** what was said — do not tidy it, merge lines, or
insert words. (A real defect caught in review: a mnemonic's words were written into a "verbatim"
transcript quote the lecturer never spoke.)

## Quoting a garbled transcript

Lecture transcripts are machine-generated and **mangle exactly the technical terms cards are made
of.** Real cases from one lecture:

| transcript says | means |
|---|---|
| "the absence of Diane Arms" | dynein arms |
| "Women for sites" | lymphocytes |
| "They called it a cirrus demilune" | serous demilune |
| "Two common epithelial cells" | columnar |
| "Cartagena syndrome" | Kartagener |
| "immortal cilia syndrome" | immotile |

This collides with the verbatim rule: quotes must be exact, but the exact text is wrong. **The
convention:**

1. **Quote verbatim, and put the correction in square brackets immediately after the garble** —
   `"the absence of Diane [dynein] Arms"`. This is the standard scholarly form: the reader sees
   both what was said and what was meant, and nothing is silently rewritten.
2. **Never silently correct a quote.** A cleaned-up quote is indistinguishable from a fabricated
   one, and a later reviewer grepping the transcript will not find it and will report it as
   invented.
3. **Card text uses the correct term**, not the garble. The brackets live in the `Source:` quote
   in `Extra`; the card face says *dynein arms*.
4. **If the garble is bad enough that the correction is a guess, cite the slide instead** and say
   so. Do not reconstruct a sentence you cannot verify — cross-check against the slide text or
   Junqueira and cite that.
5. **A cue that is merely inaudible is not a garble.** Do not fill gaps: if the transcript has a
   silent stretch where a term was clearly spoken, cite the slide that carries it, and note the
   gap.

Corollary of the verbatim rule, worth stating on its own because it keeps recurring: **never join
separate transcript cues into one sentence.** Two adjacent cues quoted as a single continuous
sentence produce something the lecturer never said — this has shipped repeatedly, once as a merged
quote spanning a *speaker boundary*. Quote each cue separately and label them.

## Human-review gate

- Compare each card's fact against the `Source:` in its `Extra`. If the card asserts anything the
  source does not support, set **flagged / blocked** and route to human accuracy review.
- **Run a terminology-grounding pass** — a skeptical domain expert asks "would a practitioner
  actually say this? is every term standard?" This is SEPARATE from the factual-accuracy pass,
  which does not catch editorializing (a made-up term is often true-adjacent and passes it). The
  factual reviewer checks *is it true*; this reviewer checks *is it real field language*.
- **Provenance is a precondition:** a card with no resolvable source (no slide image and no
  verbatim `Source:` line) cannot be accuracy-checked — treat missing provenance as an automatic
  flag. (See the provenance requirement in the pipeline's fill contract.)

## Judgment (generator instructions)

- assert only what the source states; do not add qualifiers, round differently, or infer beyond it
- if the source is garbled or absent, do not fabricate — flag the gap instead
