# Study → Anki — a defined-process card generation engine

Turns a folder of course documents (lecture slides, transcript, learning objectives, textbook)
into **reviewed, objective-complete Anki flashcards** — through a *defined, un-skippable process*
rather than a one-shot "generate cards" prompt. Built on Claude Code + MCP.

> This repo is the **engine only**. Course materials (copyrighted textbooks, lecture
> recordings/transcripts, learning objectives, personal decks) are intentionally excluded.

## Why

A single "make me cards" agent call is a black box: it can skip work, over-generate, write
self-answering cards, and silently miss what the syllabus says to know. This engine makes the
process a **first-class state machine** — an agent is handed one step at a time keyed by a stable
id, skipping/reordering is structurally impossible, every card is independently reviewed for facts
and style, and **every learning objective must be covered before a deck can ship.**

## The pipeline

```
per anchor unit (e.g. one slide):
  scaffold → emphasis → spec_propose → spec_verify → generate
                                        │ two agents must AGREE on the card count (0–4);
                                        │ disagreement escalates to a human
per minted card:
  accuracy → markup → style → done
            │ generate writes the FACT (no markup); markup applies the <b>/<u>/<i>
            │ role colors; accuracy + style are the two independent reviewers
run-level:
  coverage (map every objective → a card; draft cards for gaps) → ship
```

Four hard gates block shipping: **lint** (mechanical shape), **review ledger** (every card reviewed,
content-hash fresh — edit a card and its verdict voids), **coverage** (every objective covered or
deferred), **process** (nothing escalated/blocked).

Document precedence: **objectives** are the contract ▸ **slides** the anchor ▸ **transcript**
emphasis ▸ **textbook** precision. An objective the transcript defers is still carded (tagged
`flag::beyond-scope`), never dropped.

## Two pipelines

There are two ways decks get built here. The **`process_engine`** (above) is the committed state
machine, gated by the calibrated linter (`lint_cards.py`) + review ledger. The current `ISF::Test 1`
decks were instead produced by an **atomic-first regeneration** — slides → fact DB → cards → review →
coverage-fill → sync — gated by the harder **mold** (`strict_shape.py`), run as manual subagent
orchestration. That pipeline is documented in
**[`classes/ISF/REGEN-PIPELINE.md`](classes/ISF/REGEN-PIPELINE.md)**; folding it into the engine is the
open reconciliation.

## What's here

| Path | Role |
|---|---|
| `classes/ISF/process_engine.py` | the state machine (stages, gates, JSON state store) + CLI |
| `classes/ISF/process_engine_mcp.py` | MCP server wrapping it — parallel-safe submit-lock |
| `.claude/workflows/run-process.js` | the driver: parallel chunk-workers per stage |
| `.claude/skills/anki-cards/*.md` | the card method — style, card shapes, yield rubric |
| `classes/ISF/review_ledger.py` | per-card review verdicts + the ship gate |
| `classes/ISF/lint_cards.py` | mechanical style linter + gate (calibrated to the reference deck) |
| `classes/ISF/strict_shape.py` | **the mold** — hard pass/fail shape gate (used by the regen pipeline) |
| `classes/ISF/build_apkg.py` / `sync_anki.py` | build a `.apkg` / push live via AnkiConnect |
| `classes/ISF/PROCESS-ENGINE.md` | **the engine operator's guide — start here** |
| `classes/ISF/REGEN-PIPELINE.md` + `regen/` | the atomic-first, mold-gated regeneration pipeline (as-run) |
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

The MCP servers are wired in **[`.mcp.json`](.mcp.json)** (`anki-style`, `process-engine`), launched
via `classes/ISF/.venv/bin/python` — so create the venv at exactly that path. Opening this repo in
Claude Code picks them up automatically. Live Anki sync (`sync_anki.py`) additionally needs Anki
running with the **AnkiConnect** add-on (and the optional `anki-mcp-server/` for note CRUD / review
stats). Card style/method lives in `.claude/skills/anki-cards/{SKILL,MARKUP,HIGH-YIELD}.md`.

To add a new lecture, see **[`ADDING-LECTURES.md`](ADDING-LECTURES.md)** — `prep_lecture.py` turns a
folder of raw materials into a ready-to-run job.

**Tests.** The linter is calibrated to a reference deck via a golden test
(`tests/test_reference_deck.py`): it must error on <2% of the 368 reference cards. Run it locally with
`classes/ISF/.venv/bin/python -m unittest tests.test_reference_deck`. The reference fixture is
copyright-private (gitignored), so CI **skips** it — regenerate locally with
`tests/extract_reference_fixture.py`.

## Getting started

Read **[`classes/ISF/PROCESS-ENGINE.md`](classes/ISF/PROCESS-ENGINE.md)** — the operator's guide:
how to *seed* a deck (one `job.yaml`), *run* it (`/run-process`), and troubleshoot.

---

*Built collaboratively with Claude Code. Course materials are excluded for copyright; only the
generation engine is published here.*
