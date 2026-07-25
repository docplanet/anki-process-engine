---
type: Session Recap
title: Style authority moved into the prompt — plus deck repair, a learning loop, and the subject-cloze judgment
description: The review step was being governed by a script calibrated to a deprecated deck. This session put the corpus cards in the prompt as the style authority, retired the script gate, built a repair path for decks already in Anki (review-deck / insert / apply), added split + source-verify to the fixer, and started the continuity capture (baseline / wrap).
tags: [anki, card-authoring, pipeline, recap, harness, style, memory]
timestamp: 2026-07-23T23:30:00Z
resource: anki://recap/2026-07-23-style-authority-and-repair
git_commits: [6bb31d4]
---

# Style authority + deck repair — session recap (2026-07-23)

Handoff for the next chat. Read [`classes/ISF/okf/`](../classes/ISF/okf/) for the rules and
`memory/harness-barrier` + `memory/repair-existing-decks` for the live model; this recap is the *why*.

# Where this started

The opening question was about **memory**: could an agent watch card edits, learn what went wrong,
and keep that as continuity? And if so — *is that just more rules, and how does it differ from a
harness?*

The answer that held up: **memory belongs to the HARNESS, not to an agent.** A harness constrains
what the agent may *do* (it's a wall, its value is that it doesn't move); memory changes what the
agent *knows*. You don't pick — you keep the wall fixed and school the worker inside it. The
reference the owner raised — [`anneal-memory`](https://github.com/phillipclapham/anneal-memory) —
turns out to *confirm* this: it's a memory system that discovered it needed a harness (grounded
citations, graduation gates, audit chain) inside itself to stay trustworthy. Take its **discipline**
(episodes → grounded graduation → bounded rewrite → bless → decay), not its apparatus (no SQLite,
Hebbian graph, affective layer).

Key caveat for our case: anneal validates *internal* grounding, not *external* correctness. For
decks, correctness is the axis that matters — so lessons must be grounded in **the owner's fixes**
(a real oracle), not in the agent's own episode log.

# The main event: the style authority was a script from the wrong deck

Chasing "how did a card ship without the bold subject clozed" led to the real defect:

- Shape was gated by **`strict_shape.py`** — a template classifier (T1–T5) whose *own docstring*
  says it was **measured from the AnKing Neurogenetics deck, which is no longer the reference**.
- `okf/style.md` already recorded that the "always cloze the `<b>` subject" rule was a **prose
  invention the corpus contradicts** — but the **hardcoded prompt strings in `build_deck.py`** had
  re-introduced it, so the prompt was fighting `style.md` *inside the same prompt*.
- So: three sources of truth disagreed (prompts / gate / corpus), and the rules governing shape
  lived in a **script**, not in the prompt the agent reads. Owner, verbatim: *"the prompt needs this
  info, not a script."*

**Fixed (commit `6bb31d4`):** the corpus cards are now dropped into the author + reviewer prompts
**directly** (`examples_block`, ungrouped, no templates). `strict_shape` no longer governs
`run`/`insert` — `mechanical()` keeps **provenance only** (verbatim source); shape is judged by the
tool-less reviewer against the corpus cards. `strict_shape.py` survives only as the `review-deck`
diagnostic.

## The subject-cloze judgment (don't swing to either extreme)

The first fix **over-corrected** — it told the author "a visible subject is fine, don't force-cloze,"
and produced **32/32 approved cards with visible subjects** (e.g. `<b>Lacunae</b> in bone contain
{{c1::<i>osteocytes</i>}}` — a term the student must recall, left un-clozed). That's as wrong as the
mandate was.

**The rule is a JUDGMENT, now encoded in both prompts and `rules/card-structure.md`:**

> **Cloze the `<b>` subject when it is itself a term to recall** (*lacunae*, *canaliculi*, *osteon*).
> **Leave it visible when it is the general FRAME** of the question (*bone*, *amino acids*).
> Ask: **would the student need to produce this word?**

Measured on the same deck after the fix: **30 clozed / 7 visible** (was 32/32 visible). Verified live:
`{{c1::<b>Lacunae</b>::what structures?}} contain {{c2::<i>osteocytes</i>::what cells?}}`, while
*"The `<u>`functional unit`</u>` of `<b>`compact bone`</b>` is the {{c1::`<i>`osteon`</i>`}}"* keeps
the frame visible.

# Repair: decks that never went through `create`

`run` builds *from sources*; it had no path for cards already in Anki (Embryology Week 4 was
hand-made). Added three commands — all reusing the existing reviewer/author:

| command | what it does |
|---|---|
| `review-deck --deck "<name>"` | read-only audit → punch-list (`out/review-<slug>.jsonl`) |
| `insert --deck "<name>" [--source F]` | seeds existing cards as drafts into the **same** loop (`review_fix_loop`, now extracted and shared with `run` — one loop, not two). Anki untouched |
| `apply <cards.jsonl> --deck "<name>"` | writeback: `updateNoteFields` in place (`src::harness-fixed`), add split-offs, **leave held** (tagged `flag::needs-human`) |

## Two upgrades to the shared fixer (so `run` gets them too)

1. **SPLIT** — `author_fix` can return SEVERAL cards for one (ids `<id>-b`, `<id>-c`). Fixes the
   "compound/buried-answer cards expire to `held`" failure: `author_fix` could only ever do
   1→1, so a reviewer note saying *"split into two cards"* was un-actionable by construction.
2. **SOURCE-VERIFY** — before deleting a fact flagged "not in source," the author greps the lecture;
   if supported, it **keeps the fact** and replaces the `extra` quote with a real line. This fixed
   **fix-by-deletion**: the loop's cheapest way to satisfy a shape gate was to delete the flagged
   content — it deleted chordoma's *correct* "tumor" because the pasted quote lacked the word.

# Calibration lesson (important, and measured)

**A `needs-fix` flag ≠ wrong content.** The tool-less reviewer only sees the card + the quote pasted
into its own `Extra` — so "not in source" means *the card outruns its own quote*, **not** *the fact is
false*. Audited every accuracy-flavored flag on Embryology against the actual lecture transcript:
**~zero flagged facts were actually wrong.** Chordoma *is* a tumor (L870); "laterality" is the right
term for the lecturer's "left sidedness" (L331). The deck's real problems were **shape** and
**provenance**, not bad facts.

# Continuity capture (built, half the loop)

- `build_deck baseline [--root ISF]` → snapshots every card to `reference/anki_baseline.jsonl`
  (git-ignored, regenerable). 339 cards across 5 decks at seed.
- `build_deck wrap [--dry-run]` → re-pulls, diffs each field, appends before/after to
  **`classes/ISF/corrections.jsonl` (git-TRACKED** — the one artifact Anki can't regenerate, since
  advancing the baseline destroys the "before"), then advances the baseline so each edit logs once.
- Replaces `wrong-*` tagging as the correction signal (too slow). Scoped in code to **Custom-Cloze
  pipeline cards** — imported AnKing/Pixorize decks are skipped (not our content, and copyrighted).

**Still open:** consolidation/graduation (recurring corrections → blessed lessons) and injecting
those lessons into the author/reviewer prompts. Edits are captured but not yet fed back.

# What shipped / state

- **`ISF::Test 2::Embryology::Week 4` — repaired in Anki.** 68 notes, all `src::harness-fixed`,
  **0 held**. (66 → `insert` → `apply` → 63 fixed + 1 split; then the last 4 hand-fixed with the
  subject clozed, and the sirenomelia card split off.)
- **Bone Histology is a TEST BED, not shipped.** `classes/ISF/Exam 2/Embryology/Week 5` — 82 slides
  rendered, media pushed, last dry run **37 approved / 8 held** in
  `out/cards.jsonl`. **Nothing written to Anki.** Deck name would be `ISF::Test 2::Histology::Bone`.
- Commit **`6bb31d4`** on `main` (code only — course material stays gitignored). **Not pushed yet.**

# Where to pick up

1. **Bone Histology** — read `out/cards.jsonl` by status, look at the 8 held, then
   `build_deck commit <…>/out/cards.jsonl --deck "ISF::Test 2::Histology::Bone"` when it's good.
2. **Fixer reliability** — the real remaining defect. `author_fix` has run-to-run variance and
   still whiffs *trivial* fixes (it dropped a subject cloze while fixing something else; two
   "split into two" notes went unresolved in 2 rounds). Holds should be *rare* and never the
   result of a one-line fix the author failed to make.
3. **`apply` keeps the worse card** — when a card is `held`, `apply` leaves the ORIGINAL in Anki,
   even when the held attempt was strictly better (fixed the main defect, tripped a minor one).
   Should keep the better version or keep looping.
4. **Consolidation half of the learning loop** (see above).
5. **`okf/process.md`** — still documents the pre-rebuild model, and now also predates this session.
