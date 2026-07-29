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

**What a card is FOR comes before how it is made.** A card exists to make the student *produce* a
key term or phrase from memory, inside a complete thought. That purpose decides every cloze — *what
must the student produce for this card to be doing its job?* — and it is stated in
[index.md](index.md) above the fidelity principle, because without it "should this be clozed?" has
no answer that can be wrong.

**Style rules are MEASURED from the corpus, never authored.** `style_check.py` derives them on every
call; to change a rule, change the corpus. Writing a rule down is how the last four style bugs
shipped.

**Nothing unreviewed goes into the deck — and a script enforces it, not discipline.** Shipping is
`build_deck commit` (step 12), and it **refuses to write any card that breaks a corpus invariant**.
That backstop runs on the output, deliberately *after* review, never before it. The un-gated
the old un-gated `insert` is gone. A subcommand named `insert` still exists but does something
else entirely — it pulls an EXISTING Anki deck into review→fix→re-review and writes nothing.
**Three commands write to Anki: `run` (approved cards, at the end, unless `--dry-run`), `commit`
(approved + held), and `apply` (updates reviewed cards in place).**

**You state the scope; nothing infers it.** `run --sources "powerpoint,transcript,junqueira"` names
which extracted files must be carded, and a source you name but don't have stops the run. An earlier
version tried to work out what deserved a card by counting term frequencies — that is guesswork
about something you simply declare.

**The whole pipeline is one command — `build_deck run` — and it inverts control.** `run` is a
driver *you* invoke; it orchestrates every step below itself and is the only thing that writes to
Anki. Claude is never the orchestrator — `run` calls it as two constrained sub-processes: **authoring**
(spawned with read-only tools — it returns card drafts, the driver writes them; it cannot edit a
rule, touch Anki, or skip a station) and **review** (step 9b — the reviewer sees each card with its
corpus-measured style report already inlined, plus one tool to re-check a proposed fix). The numbered
steps below are what `run` does internally, and remain the manual fallback if you run them by hand.
See [The harness](#the-harness).

Every step lists the **driver command** and the **manual fallback**. The subcommands are
independent — if the driver fails on one step, do that step by hand and continue.

Driver: `classes/ISF/.venv/bin/python classes/ISF/build_deck.py <subcommand>`
(abbreviated `build_deck` below). **Run it from the repo root** — the paths are relative, and an
agent's shell may reset its working directory between calls, so `cd` to the repo root in the same
command if unsure.

**The whole harness in one command** (render slides first — it needs a slug):
```
build_deck slides "<slides.pdf>" "<deck>/out" <slug>     # once, to render + index slides
build_deck run "<deck>" --deck "ISF::Test 2::<Subject>::Week N" --slug <slug> [--dry-run]
```
`run` extracts sources, authors (read-only sub-agent), gates, dedupes, reviews, and commits — and is
the only writer to Anki. `--dry-run` does everything except write. Every card ends up in
`<deck>/out/cards.jsonl` with a `status` (draft/approved/needs-fix/cut/held) + a `note` — nothing is dropped.

> **`classes/ISF/Exam 2/Histology/Week 3/out/cards.jsonl` is a live export, not a template.** It is
> what that deck currently contains, regenerated from Anki, and it is useful for seeing real cards —
> but do not copy its conventions. It carries `src::reviewed` in the JSONL (step 10 says *not* to do
> that when building), its `slide::` slugs (`ct`) do not match the slug its images were rendered
> with (`ct-w3`), and ~half its provenance quotes splice two transcript cues. **Read the style
> corpus for what a card should look like; read this only for what a real deck looks like.**

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

**Only a recording, no transcript yet?** The transcript is an input; the driver does not make it.
Transcribe the lecture (`.mp4`/`.m4a`) into the deck folder with mlx-whisper first:

```
mlx_whisper "<recording>" --model mlx-community/whisper-large-v3-mlx \
  --output-dir "<deck>" --output-format all --language English \
  --condition-on-previous-text False
```

> `--condition-on-previous-text False` is **mandatory** on a long lecture. Without it large-v3
> silently collapses into repetition loops — one sentence emitted thousands of times — yet exits 0
> with the right duration, so the failure is invisible unless you scan for it (it is also ~5× faster
> with the flag, having no degenerate segments to retry). **Verify every transcript before trusting
> it:** `sort "<t>.txt" | uniq -c | sort -rn | head` tops out at a few `Okay.`/`All right.` when
> clean, thousands when looped; and the last `.srt` cue must reach the recording's true length with
> real content, not a repeated line. Setup once: `brew install ffmpeg` +
> `uv tool install --python 3.13 mlx-whisper`. `--output-name` is ignored by the current build (it
> truncates the stem at a dotted date, `_7.20.26` → `_7.20`) — rename the outputs to match the recording.

## 2 · Slide DB

```
build_deck slides "<slides.pdf>" "<deck>/out" <slug>
```

> **Two slide decks in one folder: give each its own out_dir**, or the second run silently
> overwrites the first's `slides.jsonl` (the JPEGs survive — the slug is in their filenames — but
> the page-text index does not, and both runs report success):
> ```
> build_deck slides "<ct>.pptx"  "<deck>/out"     ct
> build_deck slides "<epi>.pptx" "<deck>/out/epi" epi     # then media BOTH dirs, see step 11
> ```
> Re-rendering a deck that gained slides also re-pads filenames (`slide-9` → `slide-09`), breaking
> `<img>` references in cards already authored. Re-render before authoring, not after.
Renders one JPEG per slide + `out/slides.jsonl` (slide number, image name, page text).
*Manual:* if the deck is `.pptx`, convert first —
`soffice --headless --convert-to pdf --outdir "<deck>/out" "<slides>.pptx"` — then
`pdftoppm -jpeg -r 150 slides.pdf out/slides/isf-<slug>-slide` and `pdftotext -layout`.
Note the manual path does **not** produce `slides.jsonl`; write it by hand or re-run the driver.

**Slug:** short and lowercase, naming the *subject deck*, e.g. `ct`, `epi`. Do not put the week in
it — the tag reads `slide::ct-14`, and the week is already carried by `week::NN`.

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

Write the scope note to **`<deck>/out/scope.md`** — a few lines, not a document: which slides the
session covered, where you found the objectives, and anything deferred to next time. It is what a
later session (or you, after a compaction) reads to know what this deck was supposed to contain.

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
over-mining [yield](rules/yield.md) forbids. Objective-backed material that was deferred still gets
carded, tagged `flag::beyond-scope` (see the yield rule).

## 5 · 🧠 Read the transcript for emphasis

Find what the instructor **stressed** ("you must know", "common exam question") and — just as
important — what they said **not** to memorize ("that will be given"). An explicit exclusion is a
direct instruction: do not card it. See [yield](rules/yield.md).

## 6 · 🧠 Author the gap

Read [`index.md`](index.md), [`style.md`](style.md), and **all four** rules in `rules/` — including
[`card-structure.md`](rules/card-structure.md), which is the one that decides *what gets clozed* —
then **read the reference cards themselves**: `classes/ISF/reference_cards.jsonl`, six hand-built
cards, one per shape. Shape questions are answered by those six, not by prose.

> This step used to send you to `ISF::Test 2::Biochemistry::Amino Acid Structures` — 84 cards in
> Anki. That deck is **not** the reference and has not been for some time. Its habits are the origin
> of every stale statistic in this rulebook, and following it here contradicted §3's own rule that
> you never open Anki to make an authoring decision.
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
| `src::okf-gen` | **written by you into the JSONL** — records that an agent authored this card against this rulebook. No script adds it; every card needs it, or the audit query below silently returns nothing |
| `src::reviewed` | added automatically by `build_deck commit` to every `approved` card it writes. Never tag by a search |
| `flag::beyond-scope` | correct + objective-backed, but the lecture deferred it (suspended) |
| `flag::low-yield` | shipped suspended because its yield is uncertain — for the owner's end-of-build list |
| `wrong-<defect>` | added **by the user during review** to flag a problem — never by the author |

**A deck folder often holds more than one slide deck, and both number from 1.** In the Week 3
histology folder, connective-tissue slide 14 and epithelium slide 57 are the *same figure*, so a
bare `slide::14` is ambiguous and provenance silently mis-attributes. Always carry the deck slug:
`slide::ct-14`, `slide::epi-57`. Use the same slug you passed to `build_deck slides`.

`key::…` appears on older cards; it was an idempotency key for a sync script that no longer exists.
**Don't add it to new cards.**

## 7 · Gate + review + fix — all inside `build_deck run`

Steps 7–10 are not run by hand any more — **`build_deck run` does them**, over the one status file.
The pieces (understand them; you don't invoke them separately):

- **Author + review, ONE SOURCE FILE AT A TIME** (step 1) — the loop is per file, not one pass over
  all of them. So by the time steps 1b and 1c run, every card has already been reviewed once.
- **Dedup** (step 1b) — **an agent** reads the whole set and names the pairs that teach one fact. It
  replaced a word-overlap score, which matched sentence frames: it called *type IV collagen in the
  basal lamina* a duplicate of a type VII card. The later is flagged **`duplicate`** — a **sixth
  status**, not in the list above, never written to Anki by `run` or `commit`. Audit them: see
  [no-duplicate](rules/no-duplicate.md).
- **Transcript check** (step 1c) — a second agent reads the recording and reports only what the
  lecturer SAID, which no other source can settle: **contradicted** (→ `needs-fix`, a wrong fact is
  fixable) or **excluded**, meaning he told the class not to learn it (→ `held`, for you — no
  rewrite saves it). Absence from the transcript is **not** a finding: most sources are handouts he
  never read aloud, and treating absence as a defect once sent correct cards from assigned readings
  into a fix loop the fixer could not resolve.
- **Media** — `run` pushes `out/slides/*.jpg` into Anki before the gate, because the gate flags
  `image not in Anki media` and no rewrite fixes that. Step 11 below is the standalone form.
- **Style invariants** (`style_check`) — measured from the corpus on every call, not written down. A
  predicate the corpus violates **zero** times BLOCKS; one it breaks rarely advises; one it breaks
  often is not a rule and is never reported. See `style_check.py --derive` for the live table.
- **Provenance checks** (`check_cards`) — every `Source:` quote is a verbatim substring of the deck's
  own sources, images present, ≤3 clozes. A miss → `needs-fix`.
- **Reviewer** (a fresh claude, batches run concurrently) — flags `approved` / `needs-fix` / `cut` +
  a note, judging against `review-checklist.md` and the corpus. **Each card arrives with its style
  report inlined**, so the reviewer reads measured findings rather than recalling rules. It does not
  rewrite; the author fixes.
- **Fix verification** — every card the author returns is re-checked immediately. One that still
  breaks an invariant goes straight back to a fresh fixer, without spending a review call. This is
  what stops a fix that resolves the note while introducing a new defect.

## 9 · 🧠 Review (what the reviewer judges)

> **Work from current text, never a stale copy.** When repairing *live* cards, re-read them from
> Anki each round — a copy taken before the last round of fixes shows superseded text, and one
> round recommended **deleting a live card** on duplication grounds that were all true of the old
> text and all false of the current one. When building a *new* deck there is nothing in Anki yet;
> your `cards.jsonl` is the current text.

The reviewer (inside `run`) checks **what a script cannot** — is every testable role clozed, does the
card read like the corpus, is a facet mismarked as an answer, is a chain crammed into one card, is it
worth knowing. It judges against [`review-checklist.md`](review-checklist.md) + the [rules](rules/)
+ the corpus, and flags `approved` / `needs-fix` / `cut` + a note. The mechanical checks (§7) run
first and mark shape/quote defects; the reviewer never re-does those.

The verbatim-quote check compares against the extracted sources **plus** the OCR'd slide-image text
(`run` OCRs the slides into `out/sources/slides-ocr.txt`), so a quote lifted off a figure the
`pdftotext` layer misses still verifies. A quote spliced from two cues with `…` will not verify —
that is the defect [accuracy](rules/accuracy.md) exists to catch, and it becomes `needs-fix`.

> **Why the reviewer is a separate program, not a glance.** "Agent, check each card against the
> rules" was an instruction every reviewer *claimed* to do and skipped — reading a batch and
> asserting "looks good," while a testable node shipped as visible prose. The reviewer is a fresh
> model call per batch, judged in isolation — and every card arrives with its **measured** style
> findings inlined, so what the corpus can prove is never left to a claim.
> **Do not** fan review out into per-axis subagents (one re-reading the whole rulebook per card
> turned a 20-card review into two hours). One controlled call per batch is the loop.

## 10 · 🧠 Fix and re-review

Inside `run` this is automatic: a `needs-fix` card is re-authored from its note and **re-reviewed**
before it can become `approved`; a rewrite is never approved by the pass that flagged it. A card the
loop can't resolve within `--max-author-rounds` (**the flag defaults to 5; pass `2` to match the
two-attempt policy below**) becomes `held` — surfaced in the status
file, and shipped to Anki suspended under `flag::held`, never silently passed. `commit` tags every
`approved` card `src::reviewed` automatically. When you repair a **live** card by hand (the ongoing
loop below), **read the note's current text before editing it** — note-ids are easy to mistake, and
editing the wrong one has silently destroyed a card before.

### When to stop — two attempts, then hold

**A card gets two authoring attempts. If the second is also rejected, do not write a third.** Stop,
and put the original text and both attempts in front of the owner. Ask which they prefer.

Round three is a signal that the problem is not in the card. By then the agent is reshaping markup
instead of re-reading the source — the failure [yield](rules/yield.md) names: *you are editing
markup and the fact hasn't changed*.

*Real case: two cards went three rounds each. Every round fixed the named defect and introduced a
different one. The owner then read both and said the **originals** were fine. Two rounds would have
reached the right answer sooner, and the right answer was "leave it alone."*

**Escalate immediately, without a second attempt, when:**
- the fact itself is disputed (two sources disagree, or a slide contradicts the textbook)
- the card is the only one covering its topic — cutting it would leave a hole (see the coverage
  floor in [yield](rules/yield.md))
- the fix would change what the card teaches rather than how it is worded

## 11 · Media into Anki

```
build_deck media "<deck>/out"
```
Pushes the slide JPEGs into Anki's media collection so `extra` images render. Idempotent.

> **Run it once per slide deck.** `media` globs `<out_dir>/slides/*.jpg` only. A folder with two
> slide decks renders the second to its own directory (e.g. `out/epi/slides/`), and those images
> are NOT pushed by a single run — `check_cards.py` will then report `image not in Anki media` for
> every card citing them. Run `build_deck media "<deck>/out"` **and** `build_deck media
> "<deck>/out/<slug>"`.
*Manual:* copy `out/slides/*.jpg` into the Anki profile's `collection.media/`.

## 12 · Ship to Anki — `commit` by status

`build_deck run` writes nothing when `--dry-run`. To ship the reviewed deck (push slide images
first so `<img>` renders):

```
build_deck media  "<deck>/out"
build_deck commit "<deck>/out/cards.jsonl" --deck "ISF::Test 2::Histology::Week 4" [--approved-only]
```
`commit` is the **only** path that writes cards to a live deck, and it writes **by status**:
`approved` cards are added and tagged `src::reviewed`; `held` cards are added tagged `flag::held` and
**suspended** (so you can find them with `tag:flag::held` and finish them in Anki); `cut` cards are
never written. `--approved-only` skips the held cards. The note type `Custom Cloze` is created if
missing.

> **`commit` is not idempotent** (Anki dedupes on the first field only). If you edit a card's `text`
> and re-commit, the edited card is no longer a duplicate — you get a **second note beside the stale
> one**. After a repair, edit the live note in Anki rather than re-committing. `out/.build_deck.log`
> records every write.

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

# Why it holds together

**A script drives, and the agent is only ever a constrained sub-call.** `build_deck run` is the
orchestrator and the only writer to Anki. It calls Claude for exactly two jobs — **authoring**
(read-only `Read/Grep/Glob` tools: it reads slides/sources/images and returns drafts, and cannot
write files, reach Anki, or skip a step) and **review** (sees the card + rules + corpus + the card's
measured style report; one tool, to re-check a fix it proposes — a reviewer that had to *fetch* the
checker sometimes never did, because MCP tools are deferred in this CLI and must be discovered
first). The author cannot edit the rules — "fixed code the agent can't touch" holds *by
construction*, because the driver spawns it with no write tools, not by a lock. To change a rule or
the style, edit the `okf/` files directly; the next `run` picks them up.

---

# The ongoing loop

Review cards in Anki. Tag anything wrong with **`wrong-<defect>`** (e.g. `wrong-first-hint`,
`wrong-low-yield`). Then, for each flagged card:

The commands, since no driver subcommand covers this path — use the `anki` MCP:

| Step | Call |
|---|---|
| find the flagged cards | `anki_find_notes` with `deck:"<name>" tag:wrong-*` |
| **read current text before editing** | `anki_get_notes_info` — note-ids are easy to mistake, and editing the wrong one has destroyed a card |
| fix | `anki_update_note_fields` |
| it is unreviewed again | `anki_remove_tags` → `src::reviewed`, then re-run step 9 |
| re-tag once reviewed | `anki_add_tags` by explicit note id — **never** by a `-tag:src::reviewed` search |
| suspend, if it should not ship | not exposed by the MCP — suspend by hand in Anki, or via AnkiConnect `suspend` |

1. Fix the card, and
2. **If the defect names a rule the book lacks, add the rule** — so the same class is caught
   mechanically next time instead of by eye.

Every rule in `rules/` came from a real flagged card. That is how the rulebook grows.
