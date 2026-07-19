---
type: Process
title: How to build a deck
description: The one procedure for turning lecture material into Anki cards — driver command and manual fallback for every step.
tags: [anki, card-authoring, process]
timestamp: 2026-07-17T00:00:00Z
---

# Read this first

**This is the only card-generation process.** If you find another document describing a different
pipeline, it is stale — delete it rather than follow it.

**The driver automates only the deterministic steps.** Scope, authoring, and review
are **agent work** — marked 🧠 below. *No script writes cards.* There is no "generator" to find; if a
card is wrong, fix the card and (if it names a rule the book lacks) add the rule.

**Nothing unreviewed goes into the deck.** Cards are authored, gated, reviewed and fixed *before*
they are inserted. If a card has not been through step 9, it does not get inserted — no exceptions,
including cards drafted as a byproduct of some other task.

Every step lists the **driver command** and the **manual fallback**. The subcommands are
independent — if the driver fails on one step, do that step by hand and continue.

Driver: `classes/ISF/.venv/bin/python classes/ISF/build_deck.py <subcommand>`
(abbreviated `build_deck` below). **Run it from the repo root** — the paths are relative, and an
agent's shell may reset its working directory between calls, so `cd` to the repo root in the same
command if unsure.

**Check `out/` before re-running steps 2–3.** A previous session may have already rendered slides or
extracted sources. `out/.build_deck.log` records what ran and when. All subcommands are idempotent,
so re-running is safe — but if `out/` looks half-populated, re-run rather than trust it.

---

## 1 · Materials in

Drop into the deck folder: the **slide deck**, the **learning objectives**, and the **lecture
transcript** (`.txt`/`.vtt`/`.srt`). Course material is gitignored — it stays local.

Two things vary by subject and neither is an error:
- **Slides may be `.ppt`/`.pptx`, not PDF.** `build_deck slides` converts them via LibreOffice
  automatically (`brew install --cask libreoffice`).
- **There may be no objectives PDF.** Some subjects (histology) embed the objectives as prose on the
  first few slides instead. Find them wherever they are — slides, a PDF, or the syllabus — and say in
  your scope note where you got them.

## 2 · Slide DB

```
build_deck slides "<slides.pdf>" "<deck>/out" <slug>
```
Renders one JPEG per slide + `out/slides.jsonl` (slide number, image name, page text).
*Manual:* `pdftoppm -jpeg -r 150 slides.pdf out/slides/isf-<slug>-slide` and `pdftotext -layout`.

## 3 · Extract sources to text

```
build_deck sources "<deck>"
```
*Manual:* `pdftotext -layout <objectives.pdf> -` and read the transcript directly.

> **The material in the deck folder is the only input.** Cards are derived from the slides,
> transcript, and objectives sitting in that directory — nothing else. **Never look at Anki to decide
> what to card.** Anki is where finished cards are written; it is not a source of authoring
> decisions. What other decks do or don't contain is irrelevant.

## 4 · 🧠 Scope

Read the objectives and the slide titles. State plainly what **this** deck covers — and flag any
objectives that belong to a *different* lecture (objectives files often span several). Card only
this deck's scope.

### A slide deck is not a lecture — check what was actually taught

**The transcript is the authority on what was covered, not the slide deck.** A folder's slides
routinely overrun the session. Expect all of these:

- **The lecture covers only part of its deck.** It ends with "we'll pick this up next time" — the
  remaining slides are *not yet taught*. Card only the covered portion.
- **The lecture *finishes* the previous topic before starting this week's.** This is the trap:
  that earlier material was taught **in this session**, so it is **in scope and you must card it** —
  the previous week's deck was built from the previous week's lecture and does not contain it.
  (Real case: an "Exam 2 Histology Week 3" recording was ~83% finishing epithelium, then began
  connective tissue. The epithelium portion was wrongly dropped as "Week 2's topic" and went
  un-carded anywhere.)
  **Scope by session, not by topic:** everything taught in this recording belongs to this deck,
  whichever topic it belongs to. Tag the topic; don't drop the material.
- **The deck folder holds more than one lecture's slides.**

So before authoring, **establish the covered range explicitly**: find where the topic starts in the
transcript and where the session ends, and map that to slide numbers. Write it down in your scope
note — e.g. *"transcript covers slides 1–29; slides 30–88 (collagen synthesis, elastic fibers, GAGs)
were previewed as 'next time' and are NOT carded here."*

**Uncovered slides are not a gap to fill** — they are next session's material and get carded with
that lecture. Do not card untaught content just because the slide exists; that is exactly the
over-mining [yield](/rules/yield.md) forbids. Objective-backed material that was deferred still gets
carded, tagged `flag::beyond-scope` (see the yield rule).

## 5 · 🧠 Read the transcript for emphasis

Find what the instructor **stressed** ("you must know", "common exam question") and — just as
important — what they said **not** to memorize ("that will be given"). An explicit exclusion is a
direct instruction: do not card it. See [yield](/rules/yield.md).

## 6 · 🧠 Author the gap

Read [`index.md`](/index.md), [`style.md`](/style.md), and the three rules in `rules/` before
writing — then **read the reference corpus itself** (`ISF::Test 2::Biochemistry::Amino Acid
Structures`, 84 owner-reviewed cards). Shape questions are answered by those cards, not by prose.
Then author, obeying the governing principle: **faithful transcription, not synthesis** — render the
source into card shape, add nothing, coin no terminology, and prefer the source's own words.

Write drafts as JSONL, one card per line. **Keys are lowercase and map to the note type's
capitalized fields:**

| JSONL key | Note field | Contents |
|---|---|---|
| `text` | `Text` | the cloze card itself |
| `extra` | `Extra` | provenance — the slide `<img>` plus a verbatim `Source:` line |
| `source` | `Source` | short origin label, e.g. `Slide 12` / `Slide 12 / Transcript` |
| `tags` | (tags) | array of strings, see below |
| `id` | — | your own reference; not written to Anki |

```json
{"id":"ct-01","type":"cloze","text":"…","extra":"<img src=\"…\"><br><br><b>Source:</b> …","source":"Slide 12","tags":["isf::histology::connective-tissue","week::03"]}
```

### Tag vocabulary

| Tag | Meaning |
|---|---|
| `isf::<subject>::<topic>` | what the card is about — e.g. `isf::histology::connective-tissue` |
| `week::NN` | source week, zero-padded |
| `test::N` | which exam block |
| `slide::<slug>-NN` | the slide the fact came from — **the slug is required** |
| `src::<origin>` | provenance of the *card* — see [index.md](/index.md) |
| `flag::beyond-scope` | correct + objective-backed, but the lecture deferred it (suspendable) |
| `wrong-<defect>` | added **by the user during review** to flag a problem — never by the author |

**A deck folder often holds more than one slide deck, and both number from 1.** In the Week 3
histology folder, connective-tissue slide 14 and epithelium slide 57 are the *same figure*, so a
bare `slide::14` is ambiguous and provenance silently mis-attributes. Always carry the deck slug:
`slide::ct-14`, `slide::epi-57`. Use the same slug you passed to `build_deck slides`.

`key::…` appears on older cards; it was an idempotency key for a sync script that no longer exists.
**Don't add it to new cards.**

## 7 · Gate

```
build_deck gate "<deck>/out/cards.jsonl"
```
Must print `N/N conforming (0 rejected)`. Fix every reject and re-run. Image-recognition cards are **exempt** — the gate does not model them.

**The gate is shape-only.** It cannot tell an answer from a clause, or a real fact from an
invented one. Passing it means nothing about whether a card is good.
*Manual:* `classes/ISF/strict_shape.py <cards.jsonl>`.

> **Schema trap when repairing existing cards.** The gate reads **lowercase** `text`/`type`. Notes
> read back out of Anki come keyed `Text`/`Extra`/`Source` (capitalized) — feed those straight in and
> every row silently reports `NO_TEMPLATE_MATCH` instead of erroring, which reads as "all rejected"
> rather than "wrong schema". Down-case the keys on the round trip from Anki.

## 8 · Dedup check

```
build_deck dedupe "<deck>/out/cards.jsonl"
```
Advisory worklist: near-duplicate pairs, over-carded subjects, and "suspicious extra" (the subject
term is missing from the card's own `Extra` — often a provenance problem).

**Every flag must be resolved, but you may resolve it yourself** — merge, cut, or keep-both-with-a-
written-reason. Escalate only when the call needs course knowledge you don't have. See
[no-duplicate](/rules/no-duplicate.md).
*Manual:* `classes/ISF/content_check.py <cards.jsonl>`.

## 9 · 🧠 Review

> **Re-dump the deck before every review round.** Reviewers judge cards against the deck they are
> handed. A dump taken before the last round of fixes shows *superseded* text, and an agent will
> build confident arguments on it — one round recommended **deleting a live card** on duplication
> grounds that were all true of the old text and all false of the current text. Pull fresh from
> Anki each time, and say in the prompt when the dump was taken.

Run [`review-checklist.md`](/review-checklist.md) — **every check, per card**, not a "looks right"
pass. Best run as parallel subagents on separate axes:

- **sense & yield** — read each card as a *student*, not a linter: does it make basic logical sense?
  Does the hint line up with the blank? Is this worth carding at all, or is it a slide-outline
  artifact? **Run this axis first** — it catches the defects the others structurally miss, because
  style/accuracy checks can all pass on a card that is simply nonsense or not worth knowing.
- **accuracy** — each fact against the slides *and* transcript
- **terminology grounding** — is every term real field language? (catches invented/editorialized
  wording that a factual check passes) — **this covers hints too**, which are card text
- **style** — against every rule in `rules/`
- **coverage** — objectives and transcript emphasis vs. what got carded

## 10 · 🧠 Fix and re-review

**Tag every card that has passed review `src::reviewed`** (in addition to its `src::` origin), and
do it as the last act of this step. `src::okf-gen` records only *how a card was made*, not whether
anyone checked it — six unreviewed cards once sat in a live deck indistinguishable from reviewed
ones precisely because nothing recorded the difference. An untagged card in a deck is a bug you can
now actually find: `tag:src::okf-gen -tag:src::reviewed`.

An edited card **loses** the tag until it is re-reviewed.

Apply findings. Two hard-won rules:
- **Any edited card re-enters review.** A card changed after its last review is unreviewed.
- **Read a note's current text before editing it.** Note-ids are easy to mistake; editing the wrong
  note has silently destroyed a card before.

## 11 · Media into Anki

```
build_deck media "<deck>/out"
```
Pushes the slide JPEGs into Anki's media collection so `extra` images render. Idempotent.
*Manual:* copy `out/slides/*.jpg` into the Anki profile's `collection.media/`.

## 12 · Insert

```
build_deck insert "<deck>/out/cards.jsonl" --deck "ISF::Test 2::Histology::Connective Tissue" [--dry-run]
```
Adds notes with note type `Custom Cloze` (fields Text/Extra/Source). Use `--dry-run` first.
*Manual:* `anki` MCP `anki_add_notes`.

**Tagging reviewed cards: use `--tag-reviewed`, never a query.**

```
build_deck insert "<cards.jsonl>" --deck "<name>" --tag-reviewed
```
It tags **exactly the notes that call created**. Do not tag by a negative search like
`-tag:src::reviewed` — that matches every older untagged card in the deck and marks unreviewed
work as reviewed. This has happened twice, the second time hours after the first was documented,
which is why the safe path is a flag rather than a note in this file.

**Deck naming — deck by LECTURE, tag by TOPIC.**

`ISF::Test <N>::<Subject>::<Lecture>` — e.g. `ISF::Test 2::Histology::Week 3`. The deck is the
*session*: one recording, one date, everything taught in it. Topics are carried by
`isf::<subject>::<topic>` tags, so you can still review a topic across sessions.

**Why not deck-by-topic:** a lecture is not a topic. A single session routinely *finishes* one topic
and *starts* another — the Week 3 histology lecture closed out epithelium and opened connective
tissue. Deck-by-topic has nowhere to put such a session, and the material that doesn't match the
deck's topic silently falls out. (That is exactly what happened: 83% of a recording was dropped as
"the previous week's topic".)

So a single deck may legitimately carry cards tagged with two topics. That's correct, not a defect.

**Check the existing deck list first** (`anki_list_decks`) and match what's there rather than
inventing a sibling.

> Some older decks read `ISF::Test 1::Week 2::Histology (Engine)::Epithelium` — a meaningless
> `(Engine)` suffix and a topic leaf, both legacy. Don't copy that shape.

## 13 · Sync

```
build_deck sync
```
*Manual:* `anki` MCP sync, or the Sync button.

---

# The ongoing loop

Review cards in Anki. Tag anything wrong with **`wrong-<defect>`** (e.g. `wrong-first-hint`,
`wrong-low-yield`). Then, for each flagged card:

1. Fix the card, and
2. **If the defect names a rule the book lacks, add the rule** — so the same class is caught
   mechanically next time instead of by eye.

Every rule in `rules/` came from a real flagged card. That is how the rulebook grows.
