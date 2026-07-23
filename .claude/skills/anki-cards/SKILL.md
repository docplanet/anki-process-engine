---
name: anki-cards
description: Build or fix Anki flashcards from course material (slides, transcripts, learning objectives) for the Bastyr ISF study decks. Use whenever generating a deck, adding cards for a lecture/week/subject, reviewing or repairing existing cards, or acting on cards tagged `wrong-*`.
---

# Anki cards — read the rulebook, then follow the process

Everything lives in **`classes/ISF/okf/`**. There is exactly one process; if you find a document
describing a different pipeline, it is stale — delete it rather than follow it.

**Read these before doing anything:**

1. **[`classes/ISF/okf/index.md`](../../../classes/ISF/okf/index.md)** — the governing principle
   (*faithful transcription, not synthesis*) and what the six files are.
2. **[`classes/ISF/okf/process.md`](../../../classes/ISF/okf/process.md)** — the step-by-step
   procedure for building a deck, with the driver command *and* the manual fallback for every step.
3. **[`classes/ISF/okf/style.md`](../../../classes/ISF/okf/style.md)** — the style in five lines
   (`<b>` subject, `<i>` answer, `<u>` facet), and the **reference corpus that settles every other
   shape question**. Shape is decided by looking at real cards in
   `ISF::Test 2::Biochemistry::Amino Acid Structures`, never by reading prose about them — nine
   prose files describing shape were deleted because they drifted and started generating defects.
4. **`classes/ISF/okf/rules/*.md`** — three judgment rules (yield, accuracy, no-duplicate).
   Read all three before authoring.
5. **[`classes/ISF/okf/review-checklist.md`](../../../classes/ISF/okf/review-checklist.md)** — the
   explicit per-card checks a review must run.

**Building a deck is one command:** `classes/ISF/build_deck.py run <deck_dir> --deck "<name>"
[--slug S] [--dry-run]`. It runs the whole pipeline as four steps over one status-tracked
`out/cards.jsonl` — **create → review → fix → re-review** — where the author (a read-only claude
sub-call) and the reviewer (a tool-less sub-call) do the judgment, and the driver is the only writer
to Anki. Render slides first (`build_deck slides <pdf> <deck>/out <slug>`). Ship the reviewed result
with `build_deck commit <deck>/out/cards.jsonl --deck "<name>"`.

**Every card is tracked, nothing is dropped.** Each card in `cards.jsonl` carries a `status`
(draft/approved/needs-fix/cut/held) + a `note`. After a run, read that file (`grep '"status"'`) to
see what landed where and why. Read the okf rulebook not to hand-author, but to understand and refine
the rules the author/reviewer follow — the rulebook IS their prompt.

**Two things that repeatedly go wrong:**
- **The deck folder's material is the only input.** Cards come from the slides, transcript and
  objectives in that directory. Never look at Anki to decide what to card — Anki is the destination,
  not an input. Other decks are irrelevant.
- **Any card you edit re-enters review**, and **read a note's current text before editing it**.

When the user flags a card `wrong-<defect>`: fix the card, and if the defect names a rule the book
lacks, add the rule.
