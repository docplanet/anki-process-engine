# Study → Anki

Turns a folder of course material (lecture slides, transcript, learning objectives) into reviewed
Anki flashcards — against a written rulebook, with a hard shape gate and an independent review pass,
rather than a one-shot "generate cards" prompt. Built on Claude Code + MCP.

> This repo is the **tooling only**. Course materials (copyrighted textbooks, lecture recordings,
> transcripts, objectives, personal decks) are gitignored and stay local.

## Start here

**[`classes/ISF/okf/`](classes/ISF/okf/)** is the single source of truth for card work — the process
*and* the rules, in [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
(plain markdown + YAML frontmatter). Six files, no more:

| Read | For |
|---|---|
| **[`okf/process.md`](classes/ISF/okf/process.md)** | **How to build a deck** — 13 steps, each with the driver command *and* the manual fallback |
| [`okf/index.md`](classes/ISF/okf/index.md) | The governing principle and the map of the six files |
| [`okf/style.md`](classes/ISF/okf/style.md) | The card style in five lines; every other shape question is answered by the reference **corpus**, not by prose |
| [`okf/review-checklist.md`](classes/ISF/okf/review-checklist.md) | The per-card review — the bar, the five axes, what counts as a finding |
| [`okf/rules/`](classes/ISF/okf/rules/) | The three judgment rules a corpus can't show — [yield](classes/ISF/okf/rules/yield.md), [accuracy](classes/ISF/okf/rules/accuracy.md), [no-duplicate](classes/ISF/okf/rules/no-duplicate.md) |

**There is exactly one process.** If a document describes a different pipeline, it is stale — delete
it rather than follow it. The [`anki-cards` skill](.claude/skills/anki-cards/SKILL.md) is the entry
trigger; it points a fresh session at these files.

## The governing principle

**Faithful transcription, not synthesis.** Render the source into card shape — split into atomic
cloze cards, choose what to cloze, apply markup and hints, tag provenance. **Add nothing:** no
outside knowledge, no synthesized framing, no coined terminology. If a fact or term isn't in the
source, it doesn't go on the card.

## The shape of it

**Deterministic steps are scripted; judgment is agent work — and the two never blur.** No script
writes cards; there is no "generator." Scope, authoring, and the reading half of review are 🧠 steps.

```
materials → slides → sources → 🧠 scope → 🧠 author → gate → dedupe → 🧠 review → 🧠 fix → media → insert → sync
                                                        └── nothing unreviewed is ever inserted ──┘
```

| Path | Role |
|---|---|
| [`classes/ISF/build_deck.py`](classes/ISF/build_deck.py) | **the driver** — `slides · sources · gate · dedupe · media · insert · corpus · sync`. Deterministic only. Creates the note type, converts `.ppt`/`.docx`, tags reviewed cards, suspends flagged ones. |
| [`classes/ISF/strict_shape.py`](classes/ISF/strict_shape.py) | **the gate** — hard pass/fail card shape (image-recognition cards exempt). Shape-valid ≠ reviewed. |
| [`classes/ISF/check_cards.py`](classes/ISF/check_cards.py) | **mechanical review** — verbatim `Source:` quotes, hints, cloze count, media (~10s for a deck) |
| [`classes/ISF/content_check.py`](classes/ISF/content_check.py) | deck-level near-duplicate / over-carding detector |
| `classes/ISF/reference/style_corpus.jsonl` | the **style authority** — owner-reviewed cards, pulled by `build_deck corpus`; `wrong-*` cards excluded |
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
card. Any card edited after review re-enters review.

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
