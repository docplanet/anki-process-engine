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
  accuracy → style → done
run-level:
  coverage (map every objective → a card; draft cards for gaps) → ship
```

Four hard gates block shipping: **lint** (mechanical shape), **review ledger** (every card reviewed,
content-hash fresh — edit a card and its verdict voids), **coverage** (every objective covered or
deferred), **process** (nothing escalated/blocked).

Document precedence: **objectives** are the contract ▸ **slides** the anchor ▸ **transcript**
emphasis ▸ **textbook** precision. An objective the transcript defers is still carded (tagged
`flag::beyond-scope`), never dropped.

## What's here

| Path | Role |
|---|---|
| `classes/ISF/process_engine.py` | the state machine (stages, gates, JSON state store) + CLI |
| `classes/ISF/process_engine_mcp.py` | MCP server wrapping it — parallel-safe submit-lock |
| `.claude/workflows/run-process.js` | the driver: parallel chunk-workers per stage |
| `.claude/skills/anki-cards/*.md` | the card method — style, card shapes, yield rubric |
| `classes/ISF/review_ledger.py` | per-card review verdicts + the ship gate |
| `classes/ISF/lint_cards.py` | mechanical style linter + gate |
| `classes/ISF/build_apkg.py` / `sync_anki.py` | build a `.apkg` / push live via AnkiConnect |
| `classes/ISF/PROCESS-ENGINE.md` | **the operator's guide — start here** |
| `anki-mcp-server/` | a TypeScript AnkiConnect MCP server (note CRUD + review stats) |

## Getting started

Read **[`classes/ISF/PROCESS-ENGINE.md`](classes/ISF/PROCESS-ENGINE.md)** — the operator's guide:
how to *seed* a deck (one `job.yaml`), *run* it (`/run-process`), and troubleshoot.

---

*Built collaboratively with Claude Code. Course materials are excluded for copyright; only the
generation engine is published here.*
