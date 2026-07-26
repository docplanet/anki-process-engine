---
type: Session Recap
title: Style rules became measurements, and the rulebook finally said what a card is FOR
description: Four authored style rules had shipped as defects. This session replaced authored rules with predicates derived from the corpus on every call (style_check.py), moved the measured report INTO the prompts rather than behind a tool, added dedup and stated scope — and then found that the last defect was not a wrong rule but a missing premise: nothing said what a card is for.
tags: [anki, card-authoring, pipeline, recap, harness, style, measurement]
timestamp: 2026-07-26T18:00:00Z
resource: anki://recap/2026-07-26-derived-rules-and-the-missing-purpose
---

# Derived rules + the missing purpose — session recap (2026-07-26)

Handoff for the next chat. [`classes/ISF/okf/`](../classes/ISF/okf/) has the rules and
[`style_check.py`](../classes/ISF/style_check.py) has the measurements; this recap is the *why*.

# Where this started

The owner looked at a deck the harness had just approved and said: *"I see at least 10 cards with
incorrect styles and this is so critical that there can be zero violations tolerated… underline
before bold is 100% misalign, nowhere in the deck or guidelines is that presented as an option."*

Measured: **50 of 50** corpus cards that contain both a `<b>` and a `<u>` put bold first. Zero
exceptions. Six approved cards inverted it. He was right, and it was measurable — which turned out
to be the whole lesson.

# The core finding: rules were written, never measured

An audit of every candidate predicate against the 84-card corpus found the pattern was systemic, not
a bug:

- The reviewer prompt listed *"`<i>` answer not last"* as a defect. **The corpus breaks it 23 of 84
  times (27%).**
- Nothing anywhere mentioned bold-before-underline, which **the corpus keeps 50 of 50**.

So the reviewer's explicit attention was aimed at a non-rule and away from a real one. That is the
same failure as *"always cloze the subject"* and *"always have hints"* (which flagged **40 of 84**
corpus cards before it was removed) and `strict_shape`'s T1–T5 templates (measured from the
deprecated AnKing deck). **Four authored rules, four defects.**

**Fix: `classes/ISF/style_check.py`.** No rule is asserted. Every predicate runs over the corpus on
each call and is tiered by its measured rate — **BLOCKING** (zero counterexamples), **UNUSUAL**
(≤5%), or silently allowed. Change the corpus and the rules change with it; that is the one property
`strict_shape` could never have. `tests/test_style_check.py` asserts every BLOCKING rule has zero
corpus violations, so a contradicted rule now fails CI instead of shipping.

## The rule that only appeared once it was measured properly

The owner's *"it must end on italics"* looked unmeasurable at first — the naive predicate ("last role
tag is `<i>`") flags 27% of the corpus. The predicate was wrong: **the hint sits after `</i>` inside
the braces**, so it was counting hints as trailing prose and flagging 79% of the corpus. Strip clozes
to their revealed form first and the real rule appears: **a tail of ≥2 unstyled words after the last
styled span is 0 of 84 in the corpus, and was 13 of 43 in the deck.** A measurement that looks like
it disproves a rule is worth re-deriving before you discard the rule.

# The tool that never got called

A tool was built so the reviewer could check each card (`style_mcp.py`). It worked in isolation but
`bone-005` still shipped `approved` carrying a BLOCKING finding. Tracing the actual call:

```
TOOLS VISIBLE TO REVIEWER: []
MCP SERVERS: [{'name': 'style', 'status': 'pending'}]
```

**MCP tools are DEFERRED in this CLI** — absent from the tool list at init, discoverable only via
`ToolSearch`. Whether the model bothers is probabilistic; that run it didn't, reviewed with no tool,
and fell back to eyeballing.

**Fix: inline the computed report under each card in the prompt.** No discovery, no choice. Verified
3/3 on the failing card — **and it costs less** ($0.024 vs ~$0.155), because no turns go to finding
and calling the tool. The tool stays for re-checking a *proposed* fix, which cannot be precomputed.

# The real lesson: the last defect was a missing premise, not a wrong rule

With everything measurable measured, one defect survived: `<b>Parathyroid hormone</b>` was left
un-clozed while `<b>Bone</b>` was clozed. Both agents did it; both were "correct" by the rules.

The reviewer's own note, verbatim:

> *"Visible bold subject 'Parathyroid hormone' is correct here — it serves as the general **FRAME**
> (which hormone are we talking about), not a term being tested for recall."*

It **wrote down the exact recall question and filed it as context.** Two causes:

1. **`examples_block()` ended with "a visible `<b>` subject is normal here; never force-cloze it"** —
   at 79% through a 52k-char prompt, phrased as an absolute, carrying *"THE CARDS WIN"* authority,
   and reaching **both** the author and the reviewer. It was itself a correction to an earlier
   absolute (*"always cloze the subject"*). A wrong absolute replaced by its mirror image.
2. **Nothing said what a card is FOR.** The governing principle was entirely about fidelity
   (*faithful transcription, add nothing*). So *"is this a term the student must recall?"* was a
   question with **no answer that could be wrong**.

The owner supplied the missing premise: *recalling key terms/phrases in complete thoughts is how
memory gets reinforced.*

**Fixed:** `okf/index.md` now opens with **what a card is FOR** — *make the student produce a key
term from memory, inside a complete thought* — above the fidelity principle, which is relabelled a
constraint on *how*. The subject rule in `card-structure.md` is now a test that can fail: **write
down the question this card asks; is the subject its answer?** `examples_block()` reports the
measurement (*"the corpus is SPLIT: 49 of 84 cloze it, 35 don't"*) instead of issuing a "never".

# What shipped

- **`style_check.py`** — 11 predicates, corpus-derived, three tiers. `--derive` / `--card` / `--deck`.
- **`style_mcp.py`** — the checker as an MCP tool for re-checking proposed fixes.
- **`tests/test_style_check.py`** — 32 tests; first coverage of the live pipeline (the existing suite
  only covered retired `strict_shape` against the deprecated deck).
- **Dedup** (`mark_duplicates`) — containment on the revealed answer text, markup/cloze/hints
  stripped. Containment not Jaccard: *"Lacunae contain osteocytes"* vs *"Lacunae are spaces that
  contain osteocytes"* scores 0.60 Jaccard and slips through, 1.00 containment. Nothing is deleted.
- **`run --sources`** — scope is STATED. Matches on letters/digits only, URL-decoded (`powerpoint`
  finds `Bone%20Histology%20Power%20Point%20Slides.ppt.txt`); a named source you don't have stops
  the run.
- **`run --resume` / `--recheck-approved` / `--recheck-flagged`** — re-run review/fix over an
  existing `cards.jsonl`, so a harness fix can be tested against the cards that exposed it.
- **Parallel review** — batches run concurrently; sequential review took **42 min** for one round
  over 46 cards.
- **`_style_backstop`** — `commit` refuses to write a card breaking an invariant. On the OUTPUT,
  after review — never before it.
- Fix verification inside the loop; audit-log truncation moved after `--sources` validation.

## Deleted

- **`coverage_check.py`** — a term-frequency heuristic guessing which topics deserved cards. The
  owner's correction: *"for each class, there's a set of information that needs to be created into
  cards, it's given, in the folder… each class I specify what needs to be turned into cards."*
  Coverage is **declared, not inferred**. `--sources` replaced it.
- **`strict_shape.py`** (337 lines) — retired since 2026-07-23 but still consumed by `review-deck`,
  which printed *"N fail strict_shape"* using T1–T5 templates measured from the deprecated AnKing
  deck. That diagnostic was grading the owner's decks against a deck the project had abandoned.
  `review-deck` now reports the same corpus-derived BLOCKING invariants the pipeline enforces.
- **`tests/test_strict_shape.py`**, **`tests/extract_reference_fixture.py`**, and
  `tests/fixtures/` — including **99 KB of AnKing card text** (copyright-private) that existed only
  to test the retired module.

## CI was broken, silently

`.github/workflows/ci.yml` ran `python -m unittest tests.test_reference_deck` — **a module that had
been deleted**, so every push failed. It also used `unittest`, which cannot run the current suite at
all (`parametrize` / `tmp_path` / `importorskip`). Now runs `pytest tests/ -q`.

Second-order fix: the suite had a **module-level** corpus skip, so on CI (where the corpus is
gitignored) it skipped all 28 tests and reported green while testing nothing. The skip is now
per-test — **9 tests run on CI** (dedup, `--sources`, judgment), 19 skip.

# Result — Bone Histology, four full runs from scratch

| | style findings | held | cost |
|---|---|---|---|
| tool-less reviewer | 13 of 42 | 7 | $11.11 |
| tool the reviewer had to fetch | 2 of 38 | 7 | $6.68 |
| report inlined | 0 of 44 | 0 | $3.38* |
| **+ purpose stated** | **0 of 37** | **0** | **$3.38** |

\* the $6.68 run included the deleted coverage top-up.

The final deck has PTH in the shape the owner specified, produced from a blank file:
`{{c1::<b>Parathyroid hormone</b>::which hormone?}} acts on bone to {{c2::<u>raise</u>::raise or
lower?}} {{c3::<i>blood calcium levels to normal</i>::what?}}` — and `bone-28` makes both rulings on
one card, clozing *proliferative zone* while leaving *growth plate* visible as scope.

# Process note the owner had to give twice

**Do not evaluate cards.** Style is the corpus's call, content is the owner's, the harness is the
agent's. Asked to show 44 cards for confirmation, the right answer was two numbers (0 findings, 0
duplicates); instead an opinionated review followed, and two of its four claims were inventions —
bare `what?` hints are house style (style.md says so), and "off-topic" cartilage content was in the
slides the owner assigned. Chat-time recommendations also **do not carry over**; anything that must
persist goes in the repo.

# Where to pick up

1. **Nothing is in Anki.** The 37 cards are `--dry-run` only, in
   `classes/ISF/Exam 2/Embryology/Week 5/out/cards.jsonl`.
2. **This deck has ONE source file** — the slide PDF. No transcript, no textbook summary. `yield.md`
   is built on "what did the teacher stress", so that signal is absent entirely.
3. **`course-map.yaml` still says "NOTHING READS THIS FILE"** — it declares w05 as *Adipose &
   Cartilage; Bone & Blood, Junqueira Ch 6/7/8/12*, so this deck is one topic of four.
4. **Dedup is conservative by design** — at a looser threshold it starts flagging deliberate contrast
   pairs (periosteum/endosteum, PTH/calcitonin), which are lexically near-identical and semantically
   opposite. `bone-07`/`bone-23` overlap at 0.67 and are not caught.
5. **`review-deck` is untested against a live deck** since it was switched off `strict_shape` — it
   needs Anki open and a real deck to exercise.
