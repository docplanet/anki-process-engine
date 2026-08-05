---
name: anki-extract
description: Step 1 of 3. Read course material (slides, lecture transcript, textbook) and produce a fact inventory with verbatim sources — no cards yet. Use when starting an Anki deck for the Bastyr ISF course, before organizing or writing cards.
---

# What this produces

A **fact inventory**: plain statements, each with a verbatim quote and its source.
**No card markup, no clozes, no decisions about what is worth learning.** Those are steps 2 and 3.

Going straight from a source to a card is what breaks decks. The card inherits the *source
sentence's* shape instead of the *fact's* — the slide's leading clause becomes a preamble, its
bullet becomes a fused answer, its terminal noun becomes the blank. Extraction exists to break that
link. By the time cards are written the source sentence should be gone, and only the fact and its
quote remain.

# Scope

1. **The user states the folder and which files.** Never infer it from what happens to be in the
   directory. Never open Anki to decide what to card.
2. **Read the file list back before reading anything.** A lecture folder can hold both a lab
   recording and the lecture recording; they are different sessions with different content.
   *A full deck was once drafted from the wrong transcript before anyone noticed.*
3. **Read every named source end to end.** Not the first pages, not a search — end to end.

# The inventory

One entry per fact:

| field | |
|---|---|
| `fact` | one plain sentence, no markup, no cloze |
| `entity` | the specific thing the fact is about, if obvious — leave blank if not; step 2 settles it |
| `source` | `Slide N` / `Transcript` / textbook |
| `quote` | verbatim, see Fidelity |
| `image` | slide file, where there is one |
| `signal` | why it earns attention: objective / on a slide / stressed aloud / textbook only |

Facts, not sentences. If a bullet lists two independent properties, that is two entries. If a list
is itself the thing to be recalled — the three classes, the five zones — that is one.

# Emphasis

Weight by what the lecturer **stressed**, not by word count: "I need you to know", "you should know
this definition", spelling a term aloud, repeating himself, quizzing the class, minutes on one
slide. Record the signal; do not act on it — step 2 decides what survives.

Record explicit **exclusions** with equal care: "you don't need to know that", "we're not going to
talk about that today", "that value will be given to you". These are instructions, and step 2 must
see them.

# Fidelity

- **Quote verbatim.** Never tidy. A paraphrase is not a quote — "in your 20s" written as "in your
  twenties" is altered, and so is a comma standing in for a full stop.
- **Never splice two separate cues into one sentence.** Eliding with `…` is fine as long as each
  fragment is word-for-word and in order.
- Transcripts mangle technical terms. Quote the garble with the correction in `[brackets]`. Where
  the correction would be a guess, cite the slide instead.
- **The transcript is machine-generated and unreliable, so a claim that appears in it and nowhere
  else has one weak source, not one source.** Treat an odd-sounding transcript-only term as a
  probable transcription error and go looking for it in the slides, objectives or textbook. If it
  is not there, the written source's wording goes on the card and the spoken term goes in the note
  — do not put an uncorroborated term on the card face. Hedging in the audio ("you know, that's
  gonna be, you know, some…") is a further signal. *"Endomysium is areolar connective tissue" rested
  on one hedged sentence; the word appears in no slide, objective or textbook, and Junqueira says
  "reticular fibers and scattered fibroblasts".*
- **Surface every card this rule fires on when you hand over the deck — listed in full, unprompted,
  once.** Overriding what the instructor was heard to say is a judgment about a source, not a
  transcription fix, so it gets reported rather than left in a note field to be discovered. Report
  it and move on. It is not a question to put back to the user, and it is not raised twice.
- For a **spoken** fact quote the transcript and label it as such, even when a slide is also on
  screen. Never cite a slide that does not state the fact.
- Slide text inside a rasterised figure will not extract as text. Read it visually and record it —
  and note that automated checks against the text layer will not find it.
- **A fact with no resolvable source does not enter the inventory.**

# Coverage — the step that matters most

Read each source back against the inventory and ask what was taught that has no entry. Repeat until
a source comes back with nothing.

Then take the **objectives** and list them one by one, marking which are covered. Include the ones
that nothing in the material answers — step 2 needs to see the holes, because an objective-backed
gap is a reason to go looking in another source, and a gap that no source fills is something the
user must be told about rather than something to invent around.

*Skipping the coverage pass once produced a deck that carded the textbook thoroughly and skimmed
the lecture, missing two-thirds of what the lecturer emphasised.*
