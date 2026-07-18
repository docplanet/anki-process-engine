---
name: anki-cards
description: Build or fix Anki flashcards from course material (slides, transcripts, learning objectives) for the Bastyr ISF study decks. Use whenever generating a deck, adding cards for a lecture/week/subject, reviewing or repairing existing cards, or acting on cards tagged `wrong-*`.
---

# Anki cards — read the rulebook, then follow the process

Everything lives in **`classes/ISF/okf/`**. There is exactly one process; if you find a document
describing a different pipeline, it is stale — delete it rather than follow it.

**Read these before doing anything:**

1. **[`classes/ISF/okf/index.md`](../../../classes/ISF/okf/index.md)** — the governing principle
   (*faithful transcription, not synthesis*), what the `src::` provenance tags mean, and the index of
   all rules.
2. **[`classes/ISF/okf/process.md`](../../../classes/ISF/okf/process.md)** — the step-by-step
   procedure for building a deck, with the driver command *and* the manual fallback for every step.
3. **[`classes/ISF/okf/mold.md`](../../../classes/ISF/okf/mold.md)** — the role/color system
   (`<b>` subject, `<i>` answer, `<u>` facet) and the three card shapes.
4. **`classes/ISF/okf/rules/*.md`** — the rules themselves. Read all of them before authoring.
5. **[`classes/ISF/okf/review-checklist.md`](../../../classes/ISF/okf/review-checklist.md)** — the
   explicit per-card checks a review must run.

**The driver:** `classes/ISF/build_deck.py` automates only the deterministic steps (render slides,
extract sources, gate, dedupe, media, insert, sync). **Scope, authoring, and review are your work**
— no script writes cards. Don't go looking for a generator; there isn't one.

**Two things that repeatedly go wrong:**
- **Card the lecture on its own terms.** Do not consult other decks to decide what to card — a
  lecture deck must contain what that lecture taught.
- **Any card you edit re-enters review**, and **read a note's current text before editing it**.

When the user flags a card `wrong-<defect>`: fix the card, and if the defect names a rule the book
lacks, add the rule.
