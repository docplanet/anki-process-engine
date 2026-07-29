# Study → Anki

Turns a folder of course material (lecture slides, transcript, learning objectives) into reviewed
Anki flashcards — against a rulebook whose style rules are **measured from your own accepted cards**
rather than written down, with an independent review pass and a dedup pass, instead of a one-shot
"generate cards" prompt. Built on Claude Code + MCP.

> This repo is the **tooling only**. Course materials (copyrighted textbooks, lecture recordings,
> transcripts, objectives, personal decks) are gitignored and stay local.

## Start here

**[`classes/ISF/okf/`](classes/ISF/okf/)** is the single source of truth for card work — the process
*and* the rules, in [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)
(plain markdown + YAML frontmatter). Eight files, no more:

| Read | For |
|---|---|
| **[`okf/process.md`](classes/ISF/okf/process.md)** | **How to build a deck** — 12 numbered steps; most carry the driver command *and* the manual fallback |
| [`okf/index.md`](classes/ISF/okf/index.md) | The governing principle and the map of the rulebook |
| [`okf/style.md`](classes/ISF/okf/style.md) | The card style in five lines; every other shape question is answered by the reference **corpus**, not by prose |
| [`okf/review-checklist.md`](classes/ISF/okf/review-checklist.md) | The per-card review — the bar, the five axes, what counts as a finding |
| [`okf/rules/`](classes/ISF/okf/rules/) | The four judgment rules a corpus can't show — [yield](classes/ISF/okf/rules/yield.md), [accuracy](classes/ISF/okf/rules/accuracy.md), [no-duplicate](classes/ISF/okf/rules/no-duplicate.md), [card-structure](classes/ISF/okf/rules/card-structure.md) |

**There is exactly one process.** If a document describes a different pipeline, it is stale — delete
it rather than follow it. The [`anki-cards` skill](.claude/skills/anki-cards/SKILL.md) is the entry
trigger; it points a fresh session at these files.

## What a card is for, and the constraint on how

**A card exists to make the student produce a key term or phrase from memory, inside a complete
thought.** That is the purpose, and it decides every cloze: *what must the student produce for this
card to be doing its job?* That word is the blank.

**Faithful transcription, not synthesis** is the constraint on *how* to serve it. Render the source
into card shape — split into atomic cloze cards, apply markup and hints, tag provenance. **Add
nothing:** no outside knowledge, no synthesized framing, no coined terminology. If a fact or term
isn't in the source, it doesn't go on the card.

The purpose is stated first because its absence was not harmless. Without it, "should this subject
be clozed?" has no answer that can be wrong — a reviewer once called `Parathyroid hormone` a
"general FRAME (which hormone are we talking about)", writing down the exact recall question and
filing it as context. Four hormone cards shipped with the hormone visible.

## The shape of it — one driver, four steps, nothing dropped

**You run a driver; the agent is only ever a constrained sub-call.** `build_deck run` is a script
*you* (or a scheduler) invoke; it orchestrates the whole pipeline and is the only thing that writes
to Anki. It works over **one status-tracked `cards.jsonl`** — every card carries a `status`
(`draft`/`approved`/`needs-fix`/`cut`/`held`) + a `note`, and **no card is ever deleted**: a card
that fails is *marked* with the reason, so you can follow any card through the steps by reading one
file.

```
you run:  build_deck run <deck_dir> --deck "<name>" --sources "powerpoint,transcript,…"
             │   the driver orchestrates; it is the ONLY writer to Anki
  1 create+review → 1b dedup → 1c transcript → 2 review → 3 fix → 4 re-review
  🧠 per SOURCE FILE  🧠 agent    🧠 agent       gate+🧠      🧠 author   (loop until
  (author read-only)                            reviewer     (read-only)  none needs-fix)
                                                            then approved → Anki
```

- **you state the scope** — `--sources` names which extracted files must be carded. A source you
  name and don't have **stops the run**; scope is stated, never inferred from the folder.
- **create** — the author is a sub-process spawned with **read-only tools** (`Read Grep Glob`). It
  reads the named sources and *returns card drafts* — the driver writes them. With no write/Bash/Anki
  tools it **cannot** edit a rule, touch Anki, or skip a step.
- **dedup** — **an agent** reads the whole set and says which pairs teach one fact. It replaced a
  word-overlap score that matched sentence frames: it called *type IV collagen in the basal lamina*
  a duplicate of a type VII card. The later card is flagged `duplicate`, never deleted — and
  `duplicate` is a sixth status the rest of this README's vocabulary doesn't list, so grep for it.
- **transcript check** — a second agent reads the lecture recording and reports only what the
  lecturer SAID that no other source can settle: he **contradicted** the card (→ `needs-fix`), or he
  told the class **not to learn it** (→ `held`, for you). Absence from the transcript is not a
  finding — most sources are handouts he never read aloud.
- **review** — the verbatim-quote/media check (`check_cards`) plus the corpus-derived style
  invariants (`style_check`) **mark** a bad card `needs-fix` *with the reason*; then a reviewer flags
  each remaining card `approved` / `needs-fix` / `cut` + a note. **Every card carries its measured
  style report inlined**, so the reviewer reads a verdict rather than recalling a rule. It does not
  rewrite.
- **fix** — the author rewrites `needs-fix` cards from the notes, back to `draft`. **Each returned
  fix is re-checked immediately**; one that still breaks an invariant goes straight back to a fresh
  fixer without spending a review call.
- **re-review** — loop until nothing is `needs-fix`; anything unresolved after the round budget
  becomes `held` (surfaced, in the file). `commit` then writes `approved` (tagged `src::reviewed`)
  and `held` (tagged `flag::held`, suspended) to Anki — and **refuses to write any card that breaks
  a corpus invariant**, as a backstop on the output.

| Path | Role |
|---|---|
| [`classes/ISF/build_deck.py`](classes/ISF/build_deck.py) | **the driver** — `run` (the pipeline) + `commit` (write by status) + the deterministic steps `slides · sources · media · corpus · sync`. Holds the author/review sub-call logic. |
| [`classes/ISF/style_check.py`](classes/ISF/style_check.py) | **the style rules — derived, never written.** Runs a predicate battery over the corpus on every call and tiers each by its measured rate: **BLOCKING** (0 corpus violations), **UNUSUAL** (≤5%), or silently allowed. Change the corpus and the rules change with it. `--derive` prints the table. |
| [`classes/ISF/style_mcp.py`](classes/ISF/style_mcp.py) | the same checker as an MCP tool, so the author/fixer can verify a *proposed* rewrite. (The per-card report is inlined into prompts rather than fetched — MCP tools are deferred in this CLI, so a tool the model must discover may simply never be called.) |
| [`classes/ISF/check_cards.py`](classes/ISF/check_cards.py) | **provenance checks** — verbatim `Source:` quotes, media, and the one shape rule the corpus never breaks (>3 clozes) |
| [`classes/ISF/reference_cards.py`](classes/ISF/reference_cards.py) | the **style authority** — six hand-built cards, one per shape. Edit this to change the style; `build_deck corpus` regenerates `reference_cards.jsonl` from it. Every rule is measured against those six, and the cards themselves go into the prompts. |
| [`anki-mcp-server/`](anki-mcp-server/) | TypeScript AnkiConnect MCP server (note CRUD + review stats) |
| `tests/` | `test_style_check.py` — the checker, dedup, and `--sources`. Its central assertion is that **every BLOCKING rule has zero corpus violations**, so a rule the corpus contradicts fails CI instead of shipping. |

**Card style is settled by looking at real cards**, not by reading prose — six of them, one per
shape, hand-built and tracked in git. It was a 37-card pull from a real deck; that deck's own habits
then became rules by measurement (it was 22% hintless, so the derived rule became "hint only the
clozes that need it", and the next deck came back 65% hintless). **An authority has to be right
before it is large.** `build_deck corpus` regenerates the JSONL from `reference_cards.py`; the
Anki-pull path now refuses to write over it.

```bash
classes/ISF/.venv/bin/python classes/ISF/build_deck.py --help
```

## Style rules are measured, not asserted

**No style rule in this repo is written down as a rule.** `style_check.py` runs its predicates over
the corpus on every call; a predicate the corpus violates **zero** times is BLOCKING, one it breaks
rarely is advisory, one it breaks often is not a rule at all and is never reported.

That design exists because authored rules failed four times — *"always cloze the `<b>` subject"*,
`strict_shape`'s templates (calibrated to a
deck the project had abandoned), and *"never force-cloze it"* (which caused four hormone cards to
ship with the hormone visible). Each was enforced for a while against cards that contradicted it.

So: **to change a style rule, change the corpus.** Adding a predicate that the corpus contradicts
fails the test suite.

What measurement can't settle is returned as explicit *questions* rather than guessed at — is this
`<b>` span a term to recall or the frame the sentence is scoped to; does the hint read like English
in its gap. Those are the reviewer's, and yours.

## Review: measured report + a fresh reviewer per card

The reviewer is a separate Claude from the author, so it isn't grading its own work, and it sees
each card with **its style report already inlined** — the corpus-measured findings, the four
structurally closest corpus cards, and the judgment questions. It flags
`approved`/`needs-fix`/`cut`. Batches run concurrently; sequential review over 46 cards once took 42
minutes for a single round.

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
classes/ISF/.venv/bin/pip install -r requirements.txt   # needs `mcp` — style_mcp.py imports it
```

Anki steps need **Anki running with the AnkiConnect add-on** (code `2055492159`); the driver creates
its `Custom Cloze` note type on first insert. Transcribing a recording into the transcript input is a
separate pre-step (mlx-whisper) — see [`okf/process.md`](classes/ISF/okf/process.md) §1 and
[`requirements.txt`](requirements.txt).

```bash
classes/ISF/.venv/bin/pip install pytest
classes/ISF/.venv/bin/python -m pytest tests/ -q
```

The reference cards are tracked in git, so the whole suite — including every derived-rule
assertion — runs on CI with no Anki and no local setup.

See the current derived rule table any time with:

```bash
classes/ISF/.venv/bin/python classes/ISF/style_check.py --derive
```

---

*Built collaboratively with Claude Code. Course materials are excluded for copyright; only the
tooling is published here.*
