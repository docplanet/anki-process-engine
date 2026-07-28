---
type: Card Authoring Rule
title: No near-duplicate cards
description: Two cards that test the same fact are a duplicate; the deck-level checker surfaces near-duplicate pairs for merge/cut.
tags: [anki, card-authoring, duplicate, dedup, deck-level]
resource: anki://rule/no-duplicate
timestamp: 2026-07-13T00:00:00Z
enforcement: [mechanical, human-review]
source_defects: [wrong-duplicate]
---

# Rule

Two notes that test the **same fact** are a duplicate; keep one. This is a **deck-level** check
(a card is fine in isolation — the defect only exists relative to the rest of the deck), so it
runs after the deck is assembled, not per-card.

Intentional two-sided / split siblings of one note are **not** duplicates — they share an `id`
prefix before `::` and are expected.

# Enforcement

Duplicate/redundancy detection is the **reviewer's** job in the `run` pipeline: it flags a card
that restates another as `needs-fix` (merge/differentiate) or `cut`, with the reason in the card's
`note`. An automated near-duplicate detector (revealed-text similarity, over-carded subjects) is a
planned follow-up to fold back into the review step. Until then, the signals to watch are:

| Signal | Means |
|---|---|
| **near-dup pairs** | two cards' revealed text is ≥66% similar (same-note siblings excluded) |
| **over-carded subjects** | one `<b>` subject appears in ≥3 cards — possible redundancy |
| **suspicious extra** | the card's subject term never appears in its own `Extra` — often a sign the provenance doesn't actually support the card (this is what caught a fabricated quote in review) |

## The detector matches SENTENCE FRAMES, not facts — audit every `duplicate` before commit

`mark_duplicates` scores Jaccard overlap on the revealed word set. Two cards built from the **same
sentence frame** therefore collide even when they teach different facts — and because dedup runs at
step 1b, *before* review, a false positive is silently dropped without any reviewer ever seeing it.
**Read every card marked `duplicate` and confirm the two really teach one fact.** A shared frame is
not a shared fact.

Real cases, all four from one build (Histology Week 5) — restored, reviewed and shipped:

| flagged as duplicate of | why it was NOT one |
|---|---|
| `Type VII collagen connects the basal lamina to the connective tissue underneath` = `Type IV collagen is found in the basal lamina` | different collagen type **and** different fact; matched on "basal lamina". The lecturer named type VII among the five collagens *"I want you to know… and what they do"*, so the drop silently broke his stated list |
| `proteoglycans (aggrecan) make up about 9%` = `collagens make up about 15%` | identical frame, different component and different value |
| `Fibrocartilage resists deformation under stress` = `Type I collagen in fibrocartilage provides strength…` | different subject (tissue vs one of its fibres); it also completed the hyaline/elastic/fibrocartilage function set of a table the lecturer stressed |
| `cartilage growth … is very limited in adults` = `Cartilage growth: 1. appositional 2. interstitial` | one names the two modes, the other states the limit |

The tell: the two cards share a **template** (`X make up about N%`, `Type N collagen … basal
lamina`) while their *content words* — the ones carrying the fact — differ. Parallel structure on
contrasting terms is house style ([review-checklist](../review-checklist.md)), so a deck that cards
a comparison table well will generate these collisions by design.

**Restoring one is not a re-approval.** A card cut at step 1b was never reviewed. Set it back to
`draft` with a note saying why it is not a duplicate, and re-enter it through
`build_deck run --resume` — never straight to `approved`.

## Resolving a flag — who decides

Every flag must be **resolved, not ignored** — but an agent may resolve it itself:

- **Resolve and record the reason** when the call is about the cards in front of you: merge the
  duplicate, cut the weaker card, or keep both with a written justification (e.g. "five distinct
  objective-backed facets of one generic subject, not redundancy"). Put the reason where the next
  reviewer will see it.
- **Escalate to the user** only when the decision needs course knowledge you don't have — e.g.
  whether the instructor treats two phrasings as the same exam point.
- A **`suspicious extra`** hit is often a false positive (an abbreviation in the `Extra`); confirm by
  reading the card before acting.

An unresolved flag blocks ship. A *resolved-with-reason* flag does not.

> `flag::beyond-scope` cards are suspended, not deleted. **The user un-suspends them** when the
> material comes into scope for an exam — an agent should never silently drop or unsuspend one.

# Related

- Two-sided siblings of one note are not duplicates.
- [yield](../rules/yield.md) — over-carding a subject is also a yield question.
