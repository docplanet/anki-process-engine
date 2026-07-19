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
construction appears in `ISF::Test 2::Biochemistry::Amino Acid Structures` — 84 cards the owner has
reviewed and accepted — **it is not a finding.** Say nothing.

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

## 4 · Style — compare against the corpus, not against prose

See [style.md](style.md). Put the card next to real cards from
`ISF::Test 2::Biochemistry::Amino Acid Structures` and ask whether it looks like them: bold /
underline / italics doing their jobs, a hint on every cloze that reads as English, lists as a bold
header plus numbered italics.

## 5 · Duplicate

See [no-duplicate](rules/no-duplicate.md). Also: is this fact already sitting unclozed in another
card's `Extra`?

---

The mechanical gate (`build_deck gate`) runs alongside this and checks shape only. **It cannot see
anything on this list.** A card that passes the gate has not been reviewed.
