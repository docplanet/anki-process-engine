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

**Review reports findings; it does not author replacements.** Compose fixes as a separate step,
then review those. (A review that both diagnosed and rewrote once shipped five cards nobody had
ever checked.)

## 1 · Sense — read it as a student, not a linter

- Does the sentence make basic logical sense?
- **Is each answer something you can recall as a unit?** A clause with its own subject and verb is
  a sentence, not an answer.
- Hide each cloze in turn: does the remaining visible text — *including the sibling answers* — give
  it away? Watch complement pairs (resident/wandering, regular/irregular), where each answer
  implies the other.
- Does the hint read as natural English in the blank?

## 2 · Yield — is it worth knowing

See [yield](/rules/yield.md). Did the teacher signal this as need-to-know, or is it a bullet that
happened to be on a slide? **Cards should land where the emphasis is, not where the text is** — a
lecture's most-carded slide should be the one he stressed, not the one with the most bullets.

## 3 · Accuracy — is it true and is it in the source

See [accuracy](/rules/accuracy.md).

- Every fact checked against the slides **and** transcript.
- **Every `Source:` quote verbatim.** Never join separate cues into one sentence.
- Every term is language the source actually uses — including in hints.
- The cited slide image shows what the card claims.

## 4 · Style — compare against the corpus, not against prose

See [style.md](/style.md). Put the card next to real cards from
`ISF::Test 2::Biochemistry::Amino Acid Structures` and ask whether it looks like them: bold /
underline / italics doing their jobs, a hint on every cloze that reads as English, lists as a bold
header plus numbered italics.

## 5 · Duplicate

See [no-duplicate](/rules/no-duplicate.md). Also: is this fact already sitting unclozed in another
card's `Extra`?

---

The mechanical gate (`build_deck gate`) runs alongside this and checks shape only. **It cannot see
anything on this list.** A card that passes the gate has not been reviewed.
