---
name: anki-cards
description: Build or fix Anki flashcards from course material (slides, transcripts, learning objectives) for the Bastyr ISF study decks. Use whenever generating a deck, adding cards for a lecture/week/subject, reviewing or repairing existing cards, or acting on cards tagged `wrong-*`.
---

# Anki cards — read the rulebook, then follow the process

Everything lives in **`classes/ISF/okf/`**. There is exactly one process; if you find a document
describing a different pipeline, it is stale — delete it rather than follow it.

**Read these before doing anything:**

1. **[`classes/ISF/okf/index.md`](../../../classes/ISF/okf/index.md)** — **what a card is FOR**
   (*make the student produce a key term from memory, inside a complete thought*), the governing
   principle that constrains how (*faithful transcription, not synthesis*), and the file map.
   The purpose decides every cloze: *what must the student produce for this card to do its job?*
2. **[`classes/ISF/okf/process.md`](../../../classes/ISF/okf/process.md)** — the step-by-step
   procedure for building a deck, with the driver command *and* the manual fallback for every step.
3. **[`classes/ISF/okf/style.md`](../../../classes/ISF/okf/style.md)** — the style in five lines
   (`<b>` subject, `<i>` answer, `<u>` facet), and the **reference corpus that settles every other
   shape question**. Shape is decided by looking at the six real cards in
   `classes/ISF/reference_cards.jsonl`, never by reading prose about them — nine
   prose files describing shape were deleted because they drifted and started generating defects.
4. **`classes/ISF/okf/rules/*.md`** — **four** judgment rules: yield, accuracy, no-duplicate, and
   **card-structure** — the one that decides WHAT GETS CLOZED. It was dropped from this list once
   and a fresh session skipped it; it is the most load-bearing authoring file in the repo.
   Read all three before authoring.
5. **[`classes/ISF/okf/review-checklist.md`](../../../classes/ISF/okf/review-checklist.md)** — the
   explicit per-card checks a review must run.

**Building a deck is one command:** `classes/ISF/build_deck.py run <deck_dir> --deck "<name>"
[--sources "powerpoint,transcript,…"] [--slug S] [--dry-run]`. It runs the pipeline over one
status-tracked `out/cards.jsonl` — **create → dedup → review → fix → re-review** — where the author
(a read-only claude sub-call) and the reviewer do the judgment, and the driver is the only writer to
Anki. Render slides first (`build_deck slides <pdf> <deck>/out <slug>`). Ship with
`build_deck commit <deck>/out/cards.jsonl --deck "<name>"`.

**`--sources` states what must be carded** — the user tells you which materials to turn into cards;
a named source that isn't in `out/sources/` stops the run. Never infer scope from what happens to be
in the folder.

**Style rules are MEASURED, not written.** `classes/ISF/style_check.py` derives them from the six
reference cards on every call — BLOCKING means zero counterexamples among them. **To change a style
rule, edit `classes/ISF/reference_cards.py`, then `build_deck corpus`.** Never add a style rule to prose or a prompt: that is how four
separate style bugs shipped. `style_check.py --derive` shows the live table;
`style_check.py --deck <cards.jsonl>` audits a deck.

**Every card is tracked, nothing is dropped.** Each card in `cards.jsonl` carries a `status`
(draft/approved/needs-fix/cut/held, **plus `duplicate`** from the dedup agent) + a `note`. After a
run, read that file (`grep '"status"'`) to
see what landed where and why. Read the okf rulebook not to hand-author, but to understand and refine
the rules the author/reviewer follow — the rulebook IS their prompt.

**Two things that repeatedly go wrong:**
- **The deck folder's material is the only input.** Cards come from the slides, transcript and
  objectives in that directory. Never look at Anki to decide what to card — Anki is the destination,
  not an input. Other decks are irrelevant.
- **Any card you edit re-enters review**, and **read a note's current text before editing it**.

When the user flags a card `wrong-<defect>`: fix the card, and if the defect names a rule the book
lacks, add the rule.
