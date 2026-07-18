# Study → Anki

Turns a folder of course material (lecture slides, transcript, learning objectives) into reviewed
Anki flashcards — against a written rulebook, with a hard shape gate, rather than a one-shot
"generate cards" prompt. Built on Claude Code + MCP.

> This repo is the **tooling only**. Course materials (copyrighted textbooks, lecture recordings,
> transcripts, learning objectives, personal decks) are gitignored and stay local.

## Start here

**[`classes/ISF/okf/`](classes/ISF/okf/)** is the single source of truth for card work — the process
*and* the rules, in [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
(plain markdown + YAML frontmatter).

| Read | For |
|---|---|
| **[`okf/process.md`](classes/ISF/okf/process.md)** | **How to build a deck** — every step, with the driver command *and* the manual fallback |
| [`okf/index.md`](classes/ISF/okf/index.md) | The governing principle, provenance tags, index of all rules |
| [`okf/mold.md`](classes/ISF/okf/mold.md) | The card shape — roles/colors (`<b>` subject, `<i>` answer, `<u>` facet), the three shapes, the hard rejects |
| [`okf/review-checklist.md`](classes/ISF/okf/review-checklist.md) | The explicit per-card checks a review must run |
| `okf/rules/*.md` | The rules — hints, subject-first, structure, complete-span, yield, facets, accuracy, duplicates, card genres |

**There is exactly one process.** If you find a document describing a different pipeline, it's stale
— delete it rather than follow it.

## The governing principle

**Faithful transcription, not synthesis.** Render the source into card shape — split into atomic
cloze cards, choose what to cloze, apply markup and hints, tag provenance. **Add nothing:** no
outside knowledge, no synthesized framing, no coined terminology. If a fact or term isn't in the
source, it doesn't go on the card.

## What's here

| Path | Role |
|---|---|
| `classes/ISF/okf/` | **the process + the rulebook** — start here |
| `classes/ISF/build_deck.py` | **the driver** — slides, sources, gate, dedupe, media, insert, sync |
| `classes/ISF/strict_shape.py` | **the mold** — hard pass/fail shape gate |
| `classes/ISF/lint_cards.py` | style-linter helpers the mold builds on (calibrated to the reference deck) |
| `classes/ISF/content_check.py` | deck-level near-duplicate / over-carding detector |
| `anki-mcp-server/` | TypeScript AnkiConnect MCP server (note CRUD + review stats) |
| `tests/` | golden tests for the mold and the linter calibration |

**The driver automates only the deterministic steps.** Scope, audit-and-reuse, authoring, and review
are agent work — *no script writes cards*. There is no "generator" to find.

```bash
classes/ISF/.venv/bin/python classes/ISF/build_deck.py --help
```

## The working loop

Review cards in Anki → tag anything wrong with a **`wrong-<defect>`** tag → each flagged card gets
fixed **and** the defect becomes a rule (or sharpens an existing one), so the same class is caught
mechanically next time. Every rule in the book came from a real flagged card. Any card *edited*
after review re-enters review.

## Setup

Requires **Python 3** and poppler. On macOS:

```bash
brew install poppler                       # pdftoppm, pdftotext, pdfinfo
python3 -m venv classes/ISF/.venv
classes/ISF/.venv/bin/pip install -r requirements.txt
```

Anki steps need **Anki running with the AnkiConnect add-on** (code `2055492159`). The `anki` MCP
server (`anki-mcp-server/`, registered at user scope) provides note CRUD and review stats.

**Tests.** The mold has a golden test (`tests/test_strict_shape.py`), and the linter is calibrated
against a reference deck (`tests/test_reference_deck.py` — must error on <2% of its 368 cards). Run:

```bash
classes/ISF/.venv/bin/python -m unittest tests.test_strict_shape tests.test_reference_deck
```

The reference fixture is copyright-private (gitignored), so CI skips it — regenerate locally with
`tests/extract_reference_fixture.py`.

---

*Built collaboratively with Claude Code. Course materials are excluded for copyright; only the
tooling is published here.*
