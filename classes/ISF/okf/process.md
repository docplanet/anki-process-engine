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

**The driver automates only the deterministic steps.** Scope, audit-and-reuse, authoring, and review
are **agent work** — marked 🧠 below. *No script writes cards.* There is no "generator" to find; if a
card is wrong, fix the card and (if it names a rule the book lacks) add the rule.

Every step lists the **driver command** and the **manual fallback**. The subcommands are
independent — if the driver fails on one step, do that step by hand and continue.

Driver: `classes/ISF/.venv/bin/python classes/ISF/build_deck.py <subcommand>`
(abbreviated `build_deck` below).

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

## 4 · 🧠 Scope

Read the objectives and the slide titles. State plainly what **this** deck covers — and flag any
objectives that belong to a *different* lecture (objectives files often span several). Card only
this deck's scope.

### A slide deck is not a lecture — check what was actually taught

**The transcript is the authority on what was covered, not the slide deck.** A folder's slides
routinely overrun the session. Expect all of these:

- **The lecture covers only part of its deck.** It ends with "we'll pick this up next time" — the
  remaining slides are *not yet taught*. Card only the covered portion.
- **The lecture spends most of its time on the *previous* week's material** before starting this
  week's topic. (Real case: an "Exam 2 Histology Week 3" recording was ~78% Week-2 epithelium
  review; connective tissue didn't start until three-quarters through.)
- **The deck folder holds more than one lecture's slides.**

So before authoring, **establish the covered range explicitly**: find where the topic starts in the
transcript and where the session ends, and map that to slide numbers. Write it down in your scope
note — e.g. *"transcript covers slides 1–29; slides 30–88 (collagen synthesis, elastic fibers, GAGs)
were previewed as 'next time' and are NOT carded here."*

**Uncovered slides are not a gap to fill** — they are next session's material and get carded with
that lecture. Do not card untaught content just because the slide exists; that is exactly the
over-mining [yield](/rules/yield.md) forbids. Objective-backed material that was deferred still gets
carded, tagged `flag::beyond-scope` (see the yield rule).

## 5 · 🧠 Audit existing decks and REUSE first

**Before authoring anything**, query Anki for decks already covering this material
(`anki_find_notes`, `anki_get_notes_info`). If good cards exist, **reuse them** — tag and move them
into the target deck rather than regenerating. Then identify only the **genuine gap**.

This is the single biggest yield lever: on the amino-acids deck it reused 40 existing cards and cut
authoring to the ~24 the course actually added.

## 6 · 🧠 Read the transcript for emphasis

Find what the instructor **stressed** ("you must know", "common exam question") and — just as
important — what they said **not** to memorize ("that will be given"). An explicit exclusion is a
direct instruction: do not card it. See [yield](/rules/yield.md).

## 7 · 🧠 Author the gap

Read [`index.md`](/index.md), [`mold.md`](/mold.md), and **every rule** in `rules/` before writing.
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
| `slide::NN` | the slide the fact came from |
| `src::<origin>` | provenance of the *card* — see [index.md](/index.md) |
| `flag::beyond-scope` | correct + objective-backed, but the lecture deferred it (suspendable) |
| `wrong-<defect>` | added **by the user during review** to flag a problem — never by the author |

`key::…` appears on older cards; it was an idempotency key for a sync script that no longer exists.
**Don't add it to new cards.**

## 8 · Gate

```
build_deck gate "<deck>/out/cards.jsonl"
```
Must print `N/N conforming (0 rejected)`. Fix every reject and re-run.
Recognition/attribute cards are **exempt** — see
[recognition-and-attribute-cards](/rules/recognition-and-attribute-cards.md).
*Manual:* `classes/ISF/strict_shape.py <cards.jsonl>`.

## 9 · Dedup check

```
build_deck dedupe "<deck>/out/cards.jsonl"
```
Advisory worklist of near-duplicates and over-carded subjects — a human resolves each.
*Manual:* `classes/ISF/content_check.py <cards.jsonl>`.

## 10 · Media into Anki

```
build_deck media "<deck>/out"
```
Pushes the slide JPEGs into Anki's media collection so `extra` images render. Idempotent.
*Manual:* copy `out/slides/*.jpg` into the Anki profile's `collection.media/`.

## 11 · Insert

```
build_deck insert "<deck>/out/cards.jsonl" --deck "ISF::Test 2::Histology::Connective Tissue" [--dry-run]
```
Adds notes with note type `Custom Cloze` (fields Text/Extra/Source). Use `--dry-run` first.
*Manual:* `anki` MCP `anki_add_notes`.

**Deck naming:** `ISF::Test <N>::<Subject>::<Topic>` — e.g.
`ISF::Test 2::Biochemistry::Amino Acid Structures`. Subject is the strand (Biochemistry, Histology,
Embryology); Topic is the lecture. **Check the existing deck list first** (`anki_list_decks`) and
match what's there rather than inventing a sibling.

> Some older decks read `ISF::Test 1::Week 2::Histology (Engine)::Epithelium` — that carries a
> now-meaningless `(Engine)` suffix and an extra week level, both left over from a deleted pipeline.
> Don't copy that shape for new decks.

## 12 · 🧠 Review

Run [`review-checklist.md`](/review-checklist.md) — **every check, per card**, not a "looks right"
pass. Best run as parallel subagents on separate axes:

- **accuracy** — each fact against the slides *and* transcript
- **terminology grounding** — is every term real field language? (catches invented/editorialized
  wording that a factual check passes)
- **style** — against every rule in `rules/`
- **coverage** — objectives and transcript emphasis vs. what got carded

## 13 · 🧠 Fix and re-review

Apply findings. Two hard-won rules:
- **Any edited card re-enters review.** A card changed after its last review is unreviewed.
- **Read a note's current text before editing it.** Note-ids are easy to mistake; editing the wrong
  note has silently destroyed a card before.

## 14 · Sync

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
