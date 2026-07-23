---
type: Review Procedure
title: Per-card review
description: The checks a review runs on every card, before insert.
tags: [anki, card-authoring, review, process]
timestamp: 2026-07-18T00:00:00Z
---

# Per-card review

Run on **every card, before it is inserted.** A rewrite is new material — it re-enters this
checklist rather than shipping from inside a review.

## The bar: the corpus is acceptable BY DEFINITION

**Before reporting anything, ask: would this be a defect in the reference deck too?** If the same
construction appears in `classes/ISF/reference/style_corpus.jsonl` — 84 cards the owner has
reviewed and accepted, with anything they tagged `wrong-*` excluded — **it is not a finding.**
Say nothing.

This is not a tiebreaker; it is the threshold. A review with no bar reports every deviation from an
imagined ideal at the same severity, and a card that is simply *fine* never gets to be fine.

Things that are **house style, not defects** (all measured in the corpus):

- **Two-option hints** — `collagen or elastic fibres?`, `protonated or deprotonated?`, `high or low`,
  `5' or 3'`. A 50/50 hint is the hint doing its job — its purpose is to make recall *fast*, by
  letting you assemble known pieces instead of decoding what is being asked. Listing both options
  is **not** a leak; you still have to recall which one. Do not call these coin flips or
  self-answering.
- **Question-form hints**, including bare `what?` and `which?` — 107 of 111 corpus hints end in `?`.
- **Visible bold subjects** outside the cloze braces — the corpus does this constantly.
- **Two cards on one slide** covering different aspects of one thing. Two is not over-carding.
- **A matched pair** on contrasting terms with parallel structure — that similarity is the point.

**Real findings** look like: a fact the source never states; a `Source:` quote that isn't verbatim
or that joins separate cues; a card contradicting another card or its own cited slide; an answer no
one could produce as a unit; a hint using a term nobody in the field says.

*Why this section exists: a five-axis review flagged 41 of 78 cards. The owner looked at the deck
and said it was fine, then confirmed three flagged cards as correct as-written. The reviewers had
the corpus for measuring hint length and comma counts, but were never told it defines an acceptable
card — so they measured surface statistics against it while judging quality against nothing.*

**Review reports findings; it does not author replacements.** Compose fixes as a separate step,
then review those. (A review that both diagnosed and rewrote once shipped five cards nobody had
ever checked.)

**If you are rejecting a card's *second* attempt, say so explicitly and recommend escalating.** Two
failed attempts means the third will be markup-shuffling, not a fix — see
[process.md](process.md) step 10. Say plainly when the original was better than both attempts;
that has been the right answer more than once.

## 1 · Sense — read it as a student, not a linter

- Does the sentence make basic logical sense?
- **Is each answer something you can recall as a unit?** A clause with its own subject and verb is
  a sentence, not an answer.
- Hide each cloze in turn: does the remaining visible text — *including the sibling answers* — give
  it away? Watch complement pairs (resident/wandering, regular/irregular), where each answer
  implies the other.
- Does the hint read as natural English in the blank?

## 2 · Yield — is it worth knowing

See [yield](rules/yield.md). Did the teacher signal this as need-to-know, or is it a bullet that
happened to be on a slide? **Cards should land where the emphasis is, not where the text is** — a
lecture's most-carded slide should be the one he stressed, not the one with the most bullets.

## 3 · Accuracy — is it true and is it in the source

See [accuracy](rules/accuracy.md).

- Every fact checked against the slides **and** transcript.
- **Every `Source:` quote verbatim.** Never join separate cues into one sentence.
- Every term is language the source actually uses — including in hints.
- The cited slide image shows what the card claims.

## 4 · Style — a per-card conformance check, not a holistic glance

See [style.md](style.md). This is **not** "do these look about right" — it is a specific check on
**every** card, because the two defects below are shape-valid and sail through the gate:

- **Facet not marked (`<u>`).** Does the sentence name the *aspect* being asked about — a pH, a
  property, a role, a timing, a direction, an axis — sitting as plain prose? That is the facet and
  takes `<u>`. The corpus marks facets on a large share of cards; a deck that barely uses `<u>` is
  under-styled. (Real miss: a whole 65-card deck shipped with almost no facets marked because this
  axis was run as a glance.)
- **Testable role left as visible prose.** Is there a second distinct node left un-clozed in the
  trailing text? Cloze it — but respect the ceiling (≤3, two is normal) and never manufacture a
  cloze to fill a slot.

Then confirm: bold = subject, italics = answer, a hint on every cloze that reads as English, lists
as a bold header + numbered italics. **The bar is the corpus** — put the card beside real cards from
`ISF::Test 2::Biochemistry::Amino Acid Structures`; do not invent a denser style than they have.

Because this is a distinct per-card pass and easy to skip under time pressure, an authoring agent
grading its own output is not enough — run it as its own read, the same way 9a is its own script.
Three things make it hard to skip:

1. **Grade against same-shape corpus cards, pulled up — not from memory.** For each card, open the
   2–3 corpus cards of the same template and put them side by side. "Looks about right" from memory
   is how a whole deck shipped at ~6% facets against the corpus's ~86%.
2. **`check_cards.py` now reports the deck's style distribution vs the corpus** (facet-rate on prose
   cards, multi-cloze share) and marks a clear outlier `⚠ UNDER-STYLED`, making the exit non-zero.
   That is the mechanical backstop for this axis — resolve it by marking the missing facets and
   clozing the untested roles, **or** by explaining why this deck is legitimately flatter. Do not
   run past it.
3. **Look at a rendered card before it is inserted** (front, then reveal). Under-clozing and a bare
   answer are obvious in the student view and easy to miss in the JSONL. The distribution check is
   what enforces this when no one renders.

## 5 · Duplicate

See [no-duplicate](rules/no-duplicate.md). Also: is this fact already sitting unclozed in another
card's `Extra`?

---

The mechanical shape gate (`strict_shape`, run inside the review step of `build_deck run`) checks
shape only. **It cannot see anything on this list** — a card that clears the gate has not been
reviewed. Everything above is the reviewer's job.
