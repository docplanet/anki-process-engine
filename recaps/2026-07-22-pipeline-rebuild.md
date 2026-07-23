---
type: Session Recap
title: Deck pipeline — harness build, control inversion, status-model rebuild, cleanup
description: How the Anki card pipeline went from a script-toolbox the agent operated by hand to a single driver (`build_deck run`) that runs create → review → fix → re-review over one status-tracked file — plus the dead-code cleanup and the first real deck shipped.
tags: [anki, card-authoring, pipeline, recap, harness]
timestamp: 2026-07-22T22:17:00Z
resource: anki://recap/2026-07-22-pipeline-rebuild
git_commits: [2164bca, cc8fc37]
---

# Deck pipeline rebuild — session recap (2026-07-22)

Handoff for the next chat. Read [`classes/ISF/okf/`](../classes/ISF/okf/) for the current rules and
[`memory/harness-barrier`] for the live model; this recap is the *why* and the *arc*.

# Why this happened

The pipeline had a **loop but no harness**. A prior session confessed it: the working agent authored
cards, graded them, *and* could edit a check or a rule mid-task to force a card through — "a workshop
I operated myself, then kept calling a factory." Two problems drove the whole session:

1. **No real barrier.** Nothing mechanically stopped bad/unreviewed cards from reaching Anki.
2. **Card quality.** On real material the cards had chain facts, under-clozing, wordy answers, missing
   provenance, and — worst — cards were being *silently dropped* by a shape gate with no record.

# The arc (what we tried, in order)

| Phase | Move | Outcome |
|---|---|---|
| 1 | Built a "harness": `commit` barrier + `manifest.lock`/`bless` + content-hash verdict ledger + a repo-wide permission lock on the rule files | Real barrier, but it was **parts of a harness, not a harness** — the agent still *drove* the scripts, and the repo-wide lock **bled onto every session** |
| 2 | Removed the repo-wide lock; **inverted control** — `build_deck run` became a driver a human invokes; Claude became constrained sub-calls (author = read-only, reviewer = tool-less) | The agent can't touch the rules *by construction* (no write tools), not by a bolted-on lock |
| 3 | Generated the first real deck (Protein Modifications) and hit real quality issues; iterated: objectives-driven author, **OCR slides into sources**, calibrated reviewer, composed the shape gate *into* review | Yield + coverage climbed; chain facts stopped reaching "approved" |
| 4 | **Rebuilt around the owner's mental model**: create → review → fix → re-review over ONE status-tracked `cards.jsonl`; the gate *marks* `needs-fix` instead of deleting | Nothing is ever dropped; every card is grep-able by status |
| 5 | **Cleanup**: deleted the whole orphaned pre-rebuild layer; refreshed docs | Repo matches what runs |

# What the pipeline IS now

One command, four visible steps, over one status-tracked file. `build_deck run` is the driver a
human (or scheduler) invokes; it is the only writer to Anki.

```
build_deck run <deck_dir> --deck "<name>" [--slug S] [--dry-run]
  1 create   author (read-only claude sub-call) -> draft cards
  2 review   strict_shape + check_cards MARK needs-fix; tool-less reviewer flags approved/needs-fix/cut + note
  3 fix      author rewrites needs-fix cards from the note -> draft
  4 re-review loop 2-3 (bounded by --max-author-rounds, default 2); leftover -> held
build_deck commit <deck>/out/cards.jsonl --deck "<name>"   # ships by status
```

- **One file:** `out/cards.jsonl`, each card carries `status` (draft/approved/needs-fix/cut/held) +
  `note`. **Nothing is deleted** — a failing card is *marked* with the reason.
- **author** — `claude -p --allowedTools "Read Grep Glob" --strict-mcp-config`; reads
  slides/images/sources, returns drafts; the driver writes them. Full trace → `out/author.audit.jsonl`.
- **reviewer** — tool-less `claude -p`; sees only card + rules + corpus; flags a status + note; does
  **not** rewrite (the author fixes). The shape gate is *composed into* review — a reviewer "pass"
  that fails `strict_shape` is sent back to fix, then `cut` if unresolvable.
- **OCR** — `run` transcribes slide-image text into `out/sources/slides-ocr.txt` (cached) so quotes
  lifted from figures (which `pdftotext` misses) verify.
- **commit** — writes `approved` (tagged `src::reviewed`) + `held` (tagged `flag::held`, **suspended**
  so they're findable but out of study); `cut` is never written. `--approved-only` skips held.

# What changed (files)

**Live tooling (all that remains):** `build_deck.py` (the driver + author/review sub-call logic),
`strict_shape.py` (`classify_card`; absorbed the old lint primitives), `check_cards.py` (`check_card`),
`okf/` (the rulebook — the author/reviewer's prompt), `reference/style_corpus.jsonl` (style authority).

**Deleted in the cleanup (commit `cc8fc37`):**

| File / command | Why |
|---|---|
| `review_loop.py` | standalone reviewer orchestrator; replaced by `review_all()` in build_deck |
| `_harness.py`, `manifest.lock`, `bless` | manifest/ledger tamper-check — redundant (read-only author can't edit rules; every run re-reviews fresh) |
| `lint_cards.py` | "DO NOT RUN" legacy; its 5 parsing primitives moved into `strict_shape.py` |
| `content_check.py` + `dedupe` | dead — `run` dropped it. Dedup-as-a-review-check is a **follow-up** |
| `insert`, `gate` subcommands | superseded by `run`/`commit` |
| `tests/test_reference_deck.py` | tested the deleted linter |

**Live subcommands now:** `run · commit · slides · sources · media · corpus · sync`.

# Key decisions & why

- **Control inversion, not a permission wall.** The right separation is "a script drives, the agent is
  a constrained sub-call," not "lock the files against every session." The author simply has no write
  tools — "fixed code the agent can't touch" by construction.
- **Status file, nothing dropped.** The owner's model (create→review→fix→re-review) + a `status` field
  per card replaced a sprawl of files (`cards.reviewed.jsonl`/`holds.jsonl`/`review.jsonl`/ledger) and
  a gate that *silently deleted* failures. Every card is now traceable in one file.
- **Reviewer flags, author fixes.** Clean role split; the reviewer never approves a card it rewrote.
- **Manifest removed.** The read-only author + always-fresh review make the tamper-check pointless.

# What shipped

**Deck `ISF::Test 2::Biochemistry::Protein Modifications`** — 46 notes in Anki (41 `approved` tagged
`src::reviewed`; 5 `held` tagged `flag::held`, suspended). 13/13 learning objectives covered. Owner
graded it ~B+/A-. Source folder: `classes/ISF/Exam 2/Biochem/Week 4/Protein Mods & Regs/` (gitignored).

# Open follow-ups (queued)

1. **Hold-reason legibility** — the held cards' reasons weren't crisp; a hold should fire only on a
   genuine, plainly-explained reason (a factual doubt), not a vague one.
2. **Tighten wordy answers** — the reviewer should flag multi-clause run-on `<i>` answers as
   `needs-fix` (owner examples: the G-protein and activation-energy cards). The `<i>` answer should be
   one tight fact.
3. **Dedup** — re-add near-duplicate detection as a check inside the review step.
4. **Docs** — `okf/process.md` got the actively-wrong command sections fixed but deserves a fuller
   ground-up rewrite for the status model.

# Git / backup state

- Two commits on `main`, **pushed to GitHub** (`github.com/docplanet/anki-process-engine`):
  `2164bca` (rebuild) and `cc8fc37` (cleanup). Local and `origin/main` are in sync.
- Course material (`classes/**/out/`, recordings, PDFs) stays gitignored.

# Where to pick up

Start a new deck with: render slides (`build_deck slides <pdf> <deck>/out <slug>`), then
`build_deck run <deck> --deck "<name>" --slug <slug> --dry-run`, read `out/cards.jsonl` by status,
then `build_deck commit`. To improve quality, tune the author/reviewer prompts in `build_deck.py`
(`author_create` / `_review_system_prompt`) and the rules in `okf/` — the next `run` picks them up.
