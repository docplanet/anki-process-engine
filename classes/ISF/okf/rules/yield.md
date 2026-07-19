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

## ANY flag sends you back to the SOURCE, not to the markup

> **This section is written around low-yield flags, but it governs every flag** — self-answering,
> leaking hint, wrong terminology, all of them. A flag means *this card failed*; it does not mean
> *edit this text until it passes*. Re-read the source and ask what the teacher wanted known, then
> card that — even if the flagged card disappears entirely.
>
> **The tell is the same in every case: you are editing markup and the fact hasn't changed.**



When a card is flagged low-yield, **do not fix it by moving the clozes around.** Reframing inside a
weak fact keeps it weak — you get a better-shaped card testing something still not worth knowing.

Go back to the source and ask: *what did the teacher actually want known here?* Then card **that**,
even if it means the flagged card is discarded entirely and replaced by a different fact.

**Real case.** A card read *"A rod of collagen has a higher tensile strength than steel."* Flagged
low-yield. It was "fixed" twice by re-clozing within that same sentence — first the comparison, then
the property — and stayed low-yield both times, because *stronger than steel* is a colorful aside,
not an exam point. Nine lines away in the same transcript sat the fact that earns a card:

> "Some of these fibers provide strength, like collagen. Others, like elastic fibers, provide elasticity."

The examinable point was **discriminating collagen from elastic fibres** — a fact the shape-fixes
never approached, because they never left the card.

Symptom to watch for: you are editing markup and the *fact* hasn't changed. Stop and re-read the
source.

## When an objective is itself wrong

The objectives-are-the-contract floor assumes the objective is *correct*. Occasionally an objectives
slide compresses a list into a false structure, and the primary content slide plus the textbook both
contradict it. **A contradicted objective does not create a card.** Card the scheme the content
slide and textbook agree on, and raise the conflict with the course owner — do not ship both, which
would put a flat contradiction inside one deck.

**Real case.** Objective slide 3 read "loose CT is subdivided into areolar, reticular, adipose."
Slide 7 (Ross) and Junqueira Table 5–6 both class **reticular and adipose as *Specialized***, and
Junqueira uses **areolar as a synonym** for loose, not a subtype ("Also called areolar tissue, loose
connective tissue…"). Strip the mis-slotted items and nothing remains — the "subtypes" reduce to the
word *loose* again. The card was **suspended and tagged `wrong-contradicts-slide-7`**, not deleted — the true fact
(CT proper grades loose or dense) was already carded from slide 7. *(An earlier draft of this rule
said "the card was cut." It was not; it is still in the collection, suspended. A rulebook that
misreports the deck's actual state is worse than one that says nothing.)* The tell: the card's own `Extra` embedded slide 7, the very slide that
contradicted its answer — **when a card's provenance image disagrees with its answer, the card is
wrong**, not the slide.

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
