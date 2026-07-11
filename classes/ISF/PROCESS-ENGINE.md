# ISF Card Pipeline — Process Engine (Operator's Guide)

The single reference for generating study decks. The engine turns a folder of course documents
into reviewed, **objective-complete** Anki cards through a defined, un-skippable process. This doc:
what it is, how to seed a deck, how to run it, and how to fix a stuck run.

> All Python commands below use the project venv: **`classes/ISF/.venv/bin/python`**.

---

## What it is

A staged **state machine**, not a bypassable script. It hands one step to an agent at a time, keyed
by a stable card id; skipping or reordering is structurally impossible. Every card is independently
reviewed for facts and style, and **every learning objective must be covered before the deck ships**.

### Stages

```
per anchor unit (e.g. one slide):
  scaffold → emphasis → spec_propose → spec_verify → generate
                                        │ AGREE    → mint N cards (0–4)
                                        │ DISAGREE → escalate to human
per minted card:
  accuracy → markup → style → done
run-level (after all cards done):
  coverage → ship
```

- **scaffold** — capture the unit's content for the answer-side reveal (`extra`). For diagram/figure
  slides the agent **reads the slide image itself** as the primary source; the reveal keeps the slide
  image + verbatim source text so every answer is verifiable (the same provenance model the regen
  pipeline hard-enforces — see `REGEN-PIPELINE.md`).
- **emphasis** — read the transcript: what did the teacher stress?
- **spec_propose / spec_verify** — TWO agents decide how many cards the unit earns (0–4), grounded
  in `HIGH-YIELD.md`. They must agree; disagreement **escalates to you**. 0 is a first-class,
  auditable outcome (title slides, animation-duplicates).
- **generate** — author the FACT (canonical shape, two-sided, **no markup**). Agents RETURN card data;
  the engine writes it.
- **accuracy** — verify every fact against the assigned source (lecture wins over textbook) + structure
- **markup** — a separate agent applies the `<b>` subject / `<u>` facet / `<i>` answer role colors
  (content already fixed; markup only). Splitting content from color keeps each agent single-purpose.
- **style** — final review: markup roles, terseness, no self-answering / derivation leaks

### The canonical card shape (what generate/style target)

Measured from the AnKing reference deck (see `reference-deck-is-the-spec`): **two-sided** cloze —
`{{c1::<b>subject</b>}} [plain] {{c2::<i>answer</i>}}` — ~2 clozes, one italic answer, ~10–12 words.
**Comparison split:** an A-vs-B slide (tissue types, gland types, pathways) earns **two atomic cards**,
one per concept — *not* one "A…whereas B…" card (that pairs two full definitions and self-answers
across siblings). The only single-card comparison is a shared-cloze **single axis** where both sides
differ on one property and share a cloze number. This rule lives in the `spec_propose` + `generate`
prompts and is enforced by `lint_cards.py`, which is calibrated to the reference deck via the golden
test (`tests/test_reference_deck.py`).
- **coverage** — map every OBJECTIVE to a card; draft cards for gaps. A *deferred* objective is
  carded + tagged `flag::beyond-scope` (suspendable), **never dropped**.

### Gates (ship is blocked until all pass)

- **lint** (`lint_cards.py`) — mechanical shape errors
- **review ledger** (`review_ledger.py`) — every card reviewed *clean & current* (content-hash: edit
  a card and its verdict voids → must re-review)
- **coverage** — every objective covered or deferred (zero uncovered)
- **process** — every unit/card done, nothing escalated/blocked

---

## Document precedence

| Role | It is… | Drives |
|---|---|---|
| **objectives** | the CONTRACT | coverage — every objective maps to a card |
| **slides** | the ANCHOR | what to walk, ~1 card/stressed unit |
| **transcript** | EMPHASIS | what's stressed vs deferred (tunes yield) |
| **textbook** | PRECISION | exact numbers/definitions only |

An objective the transcript defers is still carded (tagged beyond-scope) — **objectives outrank
slide emphasis.**

---

## File map (under `classes/ISF/`)

| File | Role |
|---|---|
| `process_engine.py` | the state machine (stages, gates, `.process_state.json`); also a CLI |
| `process_engine_mcp.py` | MCP server wrapping it (7 tools; blocking work runs off-loop in threads, per-run locks for parallel safety) |
| `../../.claude/workflows/run-process.js` | the driver (bounded-parallel chunk-workers per stage) |
| `../../.claude/skills/anki-cards/SKILL.md` | card style + method |
| `../../.claude/skills/anki-cards/MARKUP.md` | card shapes + color roles |
| `../../.claude/skills/anki-cards/HIGH-YIELD.md` | the yield rubric (how many cards) |
| `review_ledger.py` | per-card review verdicts + the ship gate |
| `lint_cards.py` | mechanical style linter + gate (calibrated to the reference deck) |
| `strict_shape.py` | **the mold** — hard pass/fail shape classifier (T1–T5/LIST); the regen pipeline's gate, not yet wired into the engine (task #4) |
| `content_check.py` | deck-level content detectors (near-dupes, over-carding, suspicious extra) — the content axis above the mold |
| `REGEN-PIPELINE.md` + `regen/` | the atomic-first, mold-gated regeneration pipeline (what built the current `ISF::Test 1` decks) |
| `build_apkg.py` | build the `.apkg` (runs both gates) |
| `sync_anki.py` | push cards live to Anki via AnkiConnect (runs both gates) |
| `<subject>/job-<name>.yaml` | the per-deck SEED (documents + anchor + caps) |
| `<subject>/cards-<run>/` | the run's `cards.jsonl` + `.process_state.json` + `.review_ledger.json` |

Card identity is a stable **`id`** field (`<unit>::c<k>`), not line position — so cards can be
inserted/duplicated without breaking sync or the ledger.

---

## SEED a deck — write one `job.yaml`

Drop the documents in the subject folder, then:

```yaml
run:    { deck: "ISF::Week N::<Subject> (Engine)", week: "0N", subject: <s>, cards_dir: cards-engine }
sources:
  - { file: "<slides>.pdf",     role: slides,     anchor: true }   # the anchor
  - { file: "<transcript>.txt", role: transcript }
  - { file: "<objectives>.txt", role: objectives }                 # the coverage contract
  - { file: "<textbook>.txt",   role: textbook }
anchor: { unit: slide, source_role: slides }   # slide | summary_section (histology)
yield:  { max_cards_per_unit: 4, default: 1, allow_zero: true }
gates:  { spec: consensus, accuracy: hard, style: hard }
```

- `cards_dir` is per run; multiple lectures can feed one deck name (ids are unique, no clash).
- See `Week 1/Biochemistry/job-functional-groups.yaml` and `job-dietary-fuels.yaml` for worked examples.

---

## RUN a deck

**Workflow (autonomous — recommended):**
```
/run-process  { jobPath: ".../job-<name>.yaml", force: true }
```
Runs the whole pipeline in bounded-parallel chunk-rounds (~15 min/deck), then builds the `.apkg`. Requires
the `process-engine` MCP loaded — **restart Claude Code once after any engine code change** (the CLI
always uses current code; the MCP server is loaded at startup). Tune with `args.chunk` (items per worker,
default 8) and `args.maxParallel` (concurrent workers per workflow, default 4).

> **Batch ceiling: run at most 2 decks at once.** The engine now offloads its blocking work
> (pdftoppm render, file rewrites) off the stdio event loop, so heavy runs no longer starve the
> transport and sever the MCP session — but the safe operator ceiling is still **2 concurrent
> `/run-process` workflows**. Each workflow already self-limits to `maxParallel` workers; two of them
> is comfortable, four is not.

**CLI (manual / debugging):**
```
process_engine.py init <job.yaml> [--force]         # enumerate anchor units
process_engine.py status <cards_dir>                # where is everything
process_engine.py next-batch <cards_dir>            # peek the frontier
process_engine.py submit-batch <cards_dir> <json>   # advance a stage
process_engine.py gate <cards_dir>                  # run-completeness (advisory)
build_apkg.py --cards <cards_dir> --deck "<deck>" --out <file>.apkg   # ship (runs both gates)
sync_anki.py --cards <cards_dir> --deck "<deck>"    # push live (Anki open + AnkiConnect)
```

---

## TROUBLESHOOT

- **HALTED — escalated units:** spec proposer & verifier disagreed on a unit's card count.
  `process_status` lists them; pick the count and submit its `spec_verify`.
- **HALTED — blocked card:** a card was `flagged` (a real defect the agent couldn't fix). Read it,
  fix it, submit its verdict `clean`. *(A beyond-scope tag is `clean`, not a block.)*
- **Ship gate fails:** run `lint_cards.py <dir>` + `review_ledger.py gate <dir>`; the message names
  the card. **STALE** = a card was edited after its verdict → re-review it.
- **Engine code changed but the run doesn't see it:** the MCP server has the old code → restart Claude Code.
- **MCP session drops mid-batch (processes survive, the pipe dies):** was event-loop starvation — a
  long blocking tool call (a big `process_init` render can block ~25 s) stalled the stdio transport
  until the client's heartbeat gave up. Fixed: every tool now runs its blocking body in a worker
  thread and the protocol stream is isolated from stray stdout. If it recurs, drop to ≤2 concurrent
  workflows and/or lower `args.maxParallel`.
- **Run too slow:** heavy stages (generate/accuracy/style) parallelize via chunking; spec/coverage stay
  single-agent by design (whole-deck view for dedup). Adjust `args.chunk`.
- **Cloze count changed on already-synced cards:** prefer a clean rebuild (delete the deck's notes,
  then re-sync) to avoid orphaned empty cards in Anki.
- **Moved a lecture/`cards_dir` folder:** the `.process_state.json` stores absolute paths, so a moved
  run can't be *re-run* as-is — just `process_engine.py init` its `job.yaml` again (cheap; regenerates
  fresh). `sync_anki.py`/`build_apkg.py` read `cards.jsonl` directly, so **syncing/building a moved
  deck works from anywhere** without a re-init.

---

## Status (2026-07-11)

- **Shipped:** all 7 Test-1 lectures (690 cards) live in `ISF::Test 1`, built via the **atomic-first
  regen pipeline** (`REGEN-PIPELINE.md`), mold-gated + objective/Junqueira/transcript coverage-complete,
  each card tagged `key::<deck>::<id>` for idempotent re-sync. Deck source of truth: `<deck>/out/cards.final.jsonl`.
- **Engine status:** the `process_engine` path (this guide) still gates on `lint_cards.py` + the review
  ledger. **Open (task #4):** wire the mold (`strict_shape.py`) + provenance + tiered coverage into the
  engine so future decks generate this way natively, retiring the manual regen orchestration.
- **Ready now:** any slide-anchored deck — a `job.yaml` + `/run-process`.

*The older textbook-mined decks were retired 2026-07-08.*
