# Study → Anki — a defined-process card generation engine

Turns a folder of course documents (lecture slides, transcript, learning objectives, textbook)
into **reviewed, objective-complete Anki flashcards** — through a *defined, un-skippable process*
rather than a one-shot "generate cards" prompt. Built on Claude Code + MCP.

> This repo is the **engine only**. Course materials (copyrighted textbooks, lecture
> recordings/transcripts, learning objectives, personal decks) are intentionally excluded.

## Why

A single "make me cards" agent call is a black box: it can skip work, over-generate, write
self-answering cards, and silently miss what the syllabus says to know. This engine makes card
generation an **atomic-first, mold-gated pipeline** — slides become a fact DB, each fact becomes one
atomic card, every card is independently reviewed for facts and style and must pass a hard shape
**mold**, and **every learning objective must be covered before a deck can ship.**

## The pipeline

The current `ISF::Test 1` decks were built by an **atomic-first regeneration** — run as orchestrated
subagents, gated at every step by the hard **mold** (`strict_shape.py`):

```
slides → fact DB → cards → review → coverage-fill → sync
  build_slides_db  audit_facts  generate  audit_regen  merge_gaps  sync_anki
```

`cards.final.jsonl` is the source of truth; `merge_gaps.py` re-derives it byte-for-byte.

Hard gates block shipping: the **mold** (`strict_shape.py`, pass/fail shape templates), the **review
ledger** (every card reviewed, content-hash fresh — edit a card and its verdict voids), and
**coverage** (every objective covered or deferred).

Document precedence: **objectives** are the contract ▸ **slides** the anchor ▸ **transcript**
emphasis ▸ **textbook** precision. An objective the transcript defers is still carded (tagged
`flag::beyond-scope`), never dropped.

> **Automation status.** The pipeline is run as orchestrated subagents; a one-command driver is being
> rebuilt from scratch and is not yet dialed in. See
> **[`classes/ISF/REGEN-PIPELINE.md`](classes/ISF/REGEN-PIPELINE.md)** for the as-run method.

## What's here

| Path | Role |
|---|---|
| `classes/ISF/okf/` | **the card-authoring rulebook — what makes a good card.** Start here for card quality |
| `classes/ISF/REGEN-PIPELINE.md` + `regen/` | **the atomic-first, mold-gated pipeline (as-run) — start here for how decks get built** |
| `classes/ISF/strict_shape.py` | **the mold** — hard pass/fail shape gate |
| `.claude/skills/anki-cards/*.md` | the card method — style, card shapes, yield rubric |
| `classes/ISF/review_ledger.py` | per-card review verdicts + the ship gate |
| `classes/ISF/lint_cards.py` | mechanical style linter (calibrated to the reference deck) |
| `classes/ISF/content_check.py` | deck-level content detectors (near-dupes, over-carding) |
| `classes/ISF/build_apkg.py` / `sync_anki.py` | build a `.apkg` / push live via AnkiConnect |
| `anki-mcp-server/` | a TypeScript AnkiConnect MCP server (note CRUD + review stats) |

## Setup

Requires **Python 3** and a couple of system tools. On macOS:

```bash
# system deps
brew install poppler                 # pdftotext + pdftoppm (text + slide-image extraction)
brew install --cask libreoffice      # soffice — .pptx → .pdf, used by prep_lecture.py

# python deps, in the venv the MCP config expects
python3 -m venv classes/ISF/.venv
classes/ISF/.venv/bin/pip install -r requirements.txt
```

The MCP server is wired in **[`.mcp.json`](.mcp.json)** (`anki-style`), launched
via `classes/ISF/.venv/bin/python` — so create the venv at exactly that path. Opening this repo in
Claude Code picks it up automatically. Live Anki sync (`sync_anki.py`) additionally needs Anki
running with the **AnkiConnect** add-on (and the optional `anki-mcp-server/` for note CRUD / review
stats). Card style/method lives in `.claude/skills/anki-cards/{SKILL,MARKUP,HIGH-YIELD}.md`.

To add a new lecture, see **[`ADDING-LECTURES.md`](ADDING-LECTURES.md)** — `prep_lecture.py` turns a
folder of raw materials into a ready-to-run job.

**Tests.** The linter is calibrated to a reference deck via a golden test
(`tests/test_reference_deck.py`): it must error on <2% of the 368 reference cards. Run it locally with
`classes/ISF/.venv/bin/python -m unittest tests.test_reference_deck`. The reference fixture is
copyright-private (gitignored), so CI **skips** it — regenerate locally with
`tests/extract_reference_fixture.py`.

## The rulebook — what makes a good card

**[`classes/ISF/okf/`](classes/ISF/okf/)** is the source of truth for card *quality*, in
[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
(plain markdown + YAML frontmatter, one rule per file). Read
**[`okf/index.md`](classes/ISF/okf/index.md)** first — it opens with the governing principle
(*faithful transcription, not synthesis*) and indexes every rule.

Rules cover hints, subject-first, card structure, complete spans, yield, facet underlining,
accuracy/no-editorializing, duplicates, and the recognition/attribute card genre.
**[`okf/review-checklist.md`](classes/ISF/okf/review-checklist.md)** is the explicit per-card check
a review pass must run.

**How the rulebook grows** (the working loop): review cards in Anki → tag anything wrong with a
`wrong-<defect>` tag → those flagged cards get fixed *and* the defect becomes a rule (or sharpens an
existing one), so the same class is caught mechanically next time. Every rule in the book came from a
real flagged card. Any card *edited* after review re-enters review.

## Getting started

Read **[`classes/ISF/REGEN-PIPELINE.md`](classes/ISF/REGEN-PIPELINE.md)** — the as-run method: how the
slides → fact DB → cards → review → coverage-fill → sync pipeline is orchestrated, the per-stage agent
contracts, the mold, the provenance rule, and coverage-tier ranking. `prep_lecture.py` turns a folder
of raw materials into a ready-to-run deck folder (see `ADDING-LECTURES.md`).

---

*Built collaboratively with Claude Code. Course materials are excluded for copyright; only the
generation engine is published here.*
