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

## The shape of it — one driver, four steps, nothing dropped

**You run a driver; the agent is only ever a constrained sub-call.** `build_deck run` is a script
*you* (or a scheduler) invoke; it orchestrates the whole pipeline and is the only thing that writes
to Anki. It works over **one status-tracked `cards.jsonl`** — every card carries a `status`
(`draft`/`approved`/`needs-fix`/`cut`/`held`) + a `note`, and **no card is ever deleted**: a card
that fails is *marked* with the reason, so you can follow any card through the steps by reading one
file.

```
you run:  build_deck run <deck_dir> --deck "<name>"
             │   the driver orchestrates; it is the ONLY writer to Anki
  1 create → 2 review → 3 fix → 4 re-review     (loop 2–3 until nothing is needs-fix)
  🧠 author    gate + 🧠 reviewer   🧠 author       then commit approved → Anki
  (read-only)  (tool-less)          (read-only)
```

- **create** — the author is a sub-process spawned with **read-only tools** (`Read Grep Glob`). It
  reads slides, images, and transcript and *returns card drafts* — the driver writes them. With no
  write/Bash/Anki tools it **cannot** edit a rule, touch Anki, or skip a step. "Fixed code the agent
  can't touch" holds *by construction*.
- **review** — the mechanical shape check (`strict_shape`) + verbatim-quote check (`check_cards`)
  **mark** a bad card `needs-fix` *with the reason* (never delete it); then a fresh **tool-less**
  reviewer flags each remaining card `approved` / `needs-fix` / `cut` + a note. The reviewer does not
  rewrite.
- **fix** — the author rewrites `needs-fix` cards from the notes, back to `draft`.
- **re-review** — loop until nothing is `needs-fix`; anything unresolved after the round budget
  becomes `held` (surfaced, in the file). `commit` then writes `approved` (tagged `src::reviewed`)
  and `held` (tagged `flag::held`, suspended) to Anki.

| Path | Role |
|---|---|
| [`classes/ISF/build_deck.py`](classes/ISF/build_deck.py) | **the driver** — `run` (the pipeline) + `commit` (write by status) + the deterministic steps `slides · sources · media · corpus · sync`. Holds the author/review sub-call logic. |
| [`classes/ISF/strict_shape.py`](classes/ISF/strict_shape.py) | **the shape gate** — hard pass/fail card shape (`classify_card`; image-recognition cards exempt). Shape-valid ≠ reviewed. |
| [`classes/ISF/check_cards.py`](classes/ISF/check_cards.py) | **mechanical checks** — verbatim `Source:` quotes, hints, cloze count, media (`check_card`) |
| `classes/ISF/reference/style_corpus.jsonl` | the **style authority** — owner-reviewed cards, pulled by `build_deck corpus`; `wrong-*` cards excluded. Loaded (as examples) into the author + reviewer prompts. |
| [`anki-mcp-server/`](anki-mcp-server/) | TypeScript AnkiConnect MCP server (note CRUD + review stats) |
| `tests/` | golden tests for `strict_shape` |

**Card style is settled by looking at real cards**, not by reading prose. The reference corpus is
the owner-reviewed deck `ISF::Test 2::Biochemistry::Amino Acid Structures`; `build_deck corpus`
pulls it to `classes/ISF/reference/style_corpus.jsonl`.

```bash
classes/ISF/.venv/bin/python classes/ISF/build_deck.py --help
```

## Review: mechanical checks + a fresh reviewer per card

The mechanical checks (`strict_shape` shape, `check_cards` verbatim quotes) run first and **mark**
what they catch. The reviewer is a fresh, **tool-less** Claude that sees only the card + the rules +
corpus examples — separate from the author, so it isn't grading its own work — and flags
`approved`/`needs-fix`/`cut`. It runs one call per small batch, not a per-axis fan-out (each agent
re-reading the whole rulebook to judge one card once turned a 20-card review into two hours). The
hard-won anti-patterns — grading your own output, tagging by negative query, deck-by-topic — are
written into the rulebook as prohibitions with the incident attached.

## The working loop

Review cards in Anki → tag anything wrong `wrong-<defect>` → each flagged card gets fixed **and**,
if it names a rule the book lacks, the defect becomes a rule. Every rule came from a real flagged
card. Inside `build_deck run` the same discipline is mechanical: a `needs-fix` card is re-authored
and **re-reviewed** before it can be `approved`; a card the reviewer can't confidently pass becomes
`held` (surfaced in the status file, and shipped to Anki suspended under `flag::held`), never a
silent pass.

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
