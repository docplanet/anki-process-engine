---
type: Card Authoring Rule
title: Yield — is this fact worth a card?
description: Yield is a common-sense relevance judgment, not a mechanical rule; suspected low-yield cards are flagged for human review until firm sub-rules exist.
tags: [anki, card-authoring, yield, relevance, review]
resource: anki://rule/yield
timestamp: 2026-07-13T00:00:00Z
enforcement: [human-review]
source_defects: [wrong-low-yield]
---

# Rule

Before a fact becomes a card, apply **common sense**: is this actually worth memorizing/testing?
If not, it does not earn a card.

Yield is **not** a property of the card's form. There is no rule against exact numbers,
definitions, dates, or any other content type — a number is high-yield when it matters and
low-yield when it doesn't. The test is common sense about the *fact*, never a surface heuristic.

# Status — no firm rule yet

Yield cannot currently be reduced to a mechanical check, and the common-sense boundary isn't yet
pinned into crisp sub-rules. **Therefore a card that reads as low-yield is FLAGGED for human
review — it does not ship until a human resolves it (keep / cut / rephrase), and it is never
auto-cut or silently passed.** As recurring patterns firm up, each graduates into its own
sub-rule here (and, where possible, a mechanical flag).

# Tells (flag for review — illustrative, not exhaustive)

- **Self-answering** — the answer is contained in or derivable from the prompt.
  "Staining with a **basic** dye is called {{c1::baso­philic}}" — baso = basic; the cloze answers
  itself. *(This one is semi-detectable — token overlap between prompt and answer — so it can be a
  soft mechanical flag, still routed to human.)*
- **Trivially obvious** — "The {{c1::sperm pronucleus}} combines with the {{c2::egg pronucleus}}."
- **Incidental detail** unlikely to be tested — "spermatogenesis takes {{c1::74 days}}",
  "hCG {{c1::declines for the rest of pregnancy}}".

These are review triggers, not auto-reject reasons — a human confirms.

# Enforcement

## Human-review gate

- A suspected low-yield card is set to **flagged / blocked** and must be resolved by a human
  before ship (consistent with the project rule that an open flag must be resolved, never
  silently carried).
- Optional soft mechanical assist: flag **self-answering** cards (significant prompt tokens
  appear in the answer) — routed to the same human review, not hard-rejected.

## Judgment (generator instructions)

- do not draft a card for a fact that fails the common-sense test
- when unsure, draft it but flag it for review rather than dropping it silently
