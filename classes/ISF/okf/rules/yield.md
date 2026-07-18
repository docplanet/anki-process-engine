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

## The governing principle — RESTRAINT

**Teachers are clear about what needs to be known.** The slides are the teacher's signal; the
transcript reveals what was *stressed*. The bar is **not** "is this true / is this in the textbook"
but **"did the teacher signal this as need-to-know?"** Mining every fact mints low-yield cards.

- **Default is 1 card per stressed slide.** Occasionally 2.
- **0 is normal and legitimate** — a title/agenda slide, something waved past, or a fact already
  carded elsewhere earns zero. Not a failure.
- **Density reference:** the AnKing Neurogenetics deck is ~1 card per stressed slide; a whole
  semester ≈ 670 cards. If a lecture is trending past ~1 card/slide, you're mining, not measuring.
- **Listen for explicit exclusions.** When the instructor says a value "will be given" or not to
  memorize something, that is a direct instruction — do not card it.

## Objectives are the contract (restraint has a floor)

A learning **objective** is a promise about what must be known, and it outranks slide emphasis.
Restraint governs *slides*, never *objectives*: **an objective-backed fact is never dropped to 0.**
If the transcript defers it ("not on this exam"), it is still carded — tagged `flag::beyond-scope`
(suspendable), never deleted.

Document precedence: **objectives = the coverage contract** ▸ **slides = the anchor** ▸
**transcript = emphasis/priority** ▸ **textbook = precision**.

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
