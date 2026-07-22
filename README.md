# Study → Anki

Turns a folder of course material (lecture slides, transcript, learning objectives) into reviewed
Anki flashcards — against a written rulebook, with a hard shape gate and an independent review pass,
rather than a one-shot "generate cards" prompt. Built on Claude Code + MCP.

> This repo is the **tooling only**. Course materials (copyrighted textbooks, lecture recordings,
> transcripts, objectives, personal decks) are gitignored and stay local.

## Start here

**[`classes/ISF/okf/`](classes/ISF/okf/)** is the single source of truth for card work — the process
*and* the rules, in [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
(plain markdown + YAML frontmatter). Seven files, no more:

| Read | For |
|---|---|
| **[`okf/process.md`](classes/ISF/okf/process.md)** | **How to build a deck** — 13 steps, each with the driver command *and* the manual fallback |
| [`okf/index.md`](classes/ISF/okf/index.md) | The governing principle and the map of the six files |
| [`okf/style.md`](classes/ISF/okf/style.md) | The card style in five lines; every other shape question is answered by the reference **corpus**, not by prose |
| [`okf/review-checklist.md`](classes/ISF/okf/review-checklist.md) | The per-card review — the bar, the five axes, what counts as a finding |
| [`okf/rules/`](classes/ISF/okf/rules/) | The four judgment rules a corpus can't show — [yield](classes/ISF/okf/rules/yield.md), [accuracy](classes/ISF/okf/rules/accuracy.md), [no-duplicate](classes/ISF/okf/rules/no-duplicate.md), [card-structure](classes/ISF/okf/rules/card-structure.md) |

**There is exactly one process.** If a document describes a different pipeline, it is stale — delete
it rather than follow it. The [`anki-cards` skill](.claude/skills/anki-cards/SKILL.md) is the entry
trigger; it points a fresh session at these files.

## The governing principle

**Faithful transcription, not synthesis.** Render the source into card shape — split into atomic
cloze cards, choose what to cloze, apply markup and hints, tag provenance. **Add nothing:** no
outside knowledge, no synthesized framing, no coined terminology. If a fact or term isn't in the
source, it doesn't go on the card.

## The shape of it — the harness inverts control

**You run a driver; the agent is only ever a constrained sub-call.** This is the difference between
a harness and a toolbox: the pipeline is not a set of scripts an agent decides to run in order — it
is a script (`build_deck run`) that *you* (or a scheduler) invoke, which orchestrates every step
itself and is the only thing that writes to Anki. Claude is called into the line for exactly two
jobs and cannot reach around them.

```
you run:  build_deck run <deck_dir> --deck "<name>"
             │   the driver orchestrates; it is the ONLY writer to Anki
  sources → 🧠 author → gate → dedupe → 🧠 review → commit → sync
            (read-only)                 (tool-less)    └ ships only signed passes ┘
```

- **author** is a sub-process spawned with **read-only tools** (`--allowedTools "Read Grep Glob"`).
  It reads the slides, images, and transcript and *returns card drafts* — the driver writes them. It
  has no write/Bash/Anki tools, so it **cannot** edit a rule, touch Anki, run `commit`, or skip a
  station. "Fixed code the agent can't touch" holds *by construction*, not by a lock.
- **review** is `review_loop.py` — a fresh, **tool-less** Claude per card returning
  `pass`/`fix`/`hold`/`cut`. A `fix` re-enters the full loop; nothing ships on the verdict that wrote
  it.
- **commit** is the barrier: it re-runs the gate + mechanical review, requires a signed `pass` for
  each card's exact content (a hash — edit a card after review and its pass is void), and refuses the
  whole batch if the rules changed since `bless` (checked against `manifest.lock`). It is the sole
  live-write path; `insert`'s un-gated write was removed.

| Path | Role |
|---|---|
| [`classes/ISF/build_deck.py`](classes/ISF/build_deck.py) | **the driver** — `run` (the harness) plus the deterministic steps `slides · sources · gate · dedupe · media · commit · bless · corpus · sync`. `run` orchestrates; `commit` is the barrier; `bless` re-records the ruleset hashes. |
| [`classes/ISF/strict_shape.py`](classes/ISF/strict_shape.py) | **the gate** — hard pass/fail card shape (image-recognition cards exempt). Shape-valid ≠ reviewed. |
| [`classes/ISF/check_cards.py`](classes/ISF/check_cards.py) | **mechanical review** — verbatim `Source:` quotes, hints, cloze count, media (~10s for a deck) |
| [`classes/ISF/review_loop.py`](classes/ISF/review_loop.py) | **the evaluator** — one model verdict per card (`pass`/`fix`/`hold`/`cut`) against the rules + corpus; writes the signed, hash-keyed verdict ledger `commit` reads |
| [`classes/ISF/_harness.py`](classes/ISF/_harness.py) | shared spine — the card content-hash and the `manifest.lock` integrity check, used by both `commit` and the evaluator |
| [`classes/ISF/content_check.py`](classes/ISF/content_check.py) | deck-level near-duplicate / over-carding detector |
| `classes/ISF/reference/style_corpus.jsonl` | the **style authority** — owner-reviewed cards, pulled by `build_deck corpus`; `wrong-*` cards excluded |
| `classes/ISF/manifest.lock` | blessed SHA-256 of every gate script, rule file, and the corpus — `commit` refuses if any drifted since `bless` |
| `classes/ISF/lint_cards.py` | parsing primitives the gate imports. **Not a style check** — its thresholds are the retired AnKing calibration; see its header. |
| [`anki-mcp-server/`](anki-mcp-server/) | TypeScript AnkiConnect MCP server (note CRUD + review stats) |
| `tests/` | golden tests for the gate; the fixture is the retired AnKing deck, kept only as a structural regression guard — **not** the style authority |

**Card style is settled by looking at real cards**, not by reading prose. The reference corpus is
the owner-reviewed deck `ISF::Test 2::Biochemistry::Amino Acid Structures`; `build_deck corpus`
pulls it to `classes/ISF/reference/style_corpus.jsonl`.

```bash
classes/ISF/.venv/bin/python classes/ISF/build_deck.py --help
```

## Review is a script plus a read — never a subagent fan-out

`check_cards.py` catches everything mechanical in ~10 seconds; the rest is reading each card against
the checklist, inline. Fanning review out across per-axis agents once turned a 20-card review into
two hours (each agent re-read the whole rulebook before judging one card). That anti-pattern, and
the others earned the hard way — insert-before-review, deck-by-topic, tagging by negative query,
grading your own output — are written into the docs as prohibitions with the incident attached.

## The working loop

Review cards in Anki → tag anything wrong `wrong-<defect>` → each flagged card gets fixed **and**,
if it names a rule the book lacks, the defect becomes a rule. Every rule came from a real flagged
card. Any card edited after review re-enters review — and because a verdict is bound to the card's
content hash, the tool enforces that automatically: an edited card no longer matches its old `pass`.
The evaluator (`review_loop.py`) returns `pass`/`fix`/`hold`/`cut`; a card it can't confidently
approve becomes **`hold`** (queued for a human in `out/holds.jsonl`), never a silent pass.

## Setup

**Python 3** + poppler; LibreOffice for `.ppt`/`.pptx`; `textutil` (macOS-native) handles `.docx`
objectives. On macOS:

```bash
brew install poppler                          # pdftoppm, pdftotext, pdfinfo
brew install --cask libreoffice               # soffice — .ppt/.pptx → .pdf
python3 -m venv classes/ISF/.venv
classes/ISF/.venv/bin/pip install -r requirements.txt   # (stdlib only; the venv makes the commands verbatim)
```

Anki steps need **Anki running with the AnkiConnect add-on** (code `2055492159`); the driver creates
its `Custom Cloze` note type on first insert. Transcribing a recording into the transcript input is a
separate pre-step (mlx-whisper) — see [`okf/process.md`](classes/ISF/okf/process.md) §1 and
[`requirements.txt`](requirements.txt).

```bash
classes/ISF/.venv/bin/python -m unittest discover tests
```

The reference fixture is copyright-private (gitignored), so CI skips it — regenerate locally with
`tests/extract_reference_fixture.py`.

---

*Built collaboratively with Claude Code. Course materials are excluded for copyright; only the
tooling is published here.*
