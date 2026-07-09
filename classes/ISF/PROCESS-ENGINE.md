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
  accuracy → style → done
run-level (after all cards done):
  coverage → ship
```

- **scaffold** — capture the unit's content for the answer-side reveal (`extra`)
- **emphasis** — read the transcript: what did the teacher stress?
- **spec_propose / spec_verify** — TWO agents decide how many cards the unit earns (0–4), grounded
  in `HIGH-YIELD.md`. They must agree; disagreement **escalates to you**. 0 is a first-class,
  auditable outcome (title slides, animation-duplicates).
- **generate** — author the cards (canonical shape). Agents RETURN card data; the engine writes it.
- **accuracy** — verify every fact against the assigned source (lecture wins over textbook)
- **style** — shape, markup roles, no self-answering / derivation leaks
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
| `process_engine_mcp.py` | MCP server wrapping it (7 tools + a submit-lock for parallel safety) |
| `../../.claude/workflows/run-process.js` | the driver (parallel chunk-workers per stage) |
| `../../.claude/skills/anki-cards/SKILL.md` | card style + method |
| `../../.claude/skills/anki-cards/MARKUP.md` | card shapes + color roles |
| `../../.claude/skills/anki-cards/HIGH-YIELD.md` | the yield rubric (how many cards) |
| `review_ledger.py` | per-card review verdicts + the ship gate |
| `lint_cards.py` | mechanical style linter + gate |
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
Runs the whole pipeline in parallel chunk-rounds (~15 min/deck), then builds the `.apkg`. Requires
the `process-engine` MCP loaded — **restart Claude Code once after any engine code change** (the CLI
always uses current code; the MCP server is loaded at startup). Tune parallelism with `args.chunk` (default 8).

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
- **Run too slow:** heavy stages (generate/accuracy/style) parallelize via chunking; spec/coverage stay
  single-agent by design (whole-deck view for dedup). Adjust `args.chunk`.
- **Cloze count changed on already-synced cards:** prefer a clean rebuild (delete the deck's notes,
  then re-sync) to avoid orphaned empty cards in Anki.

---

## Status (2026-07-08)

- **Done:** Biochem Wk1 — Functional Groups (30 cards, 24/24 obj) + Dietary Fuels (42 cards, 17/17 obj).
- **Ready now:** any slide-anchored deck — a `job.yaml` + `/run-process`.
- **Needs a small build:** histology `summary_section` enumerator (chapter summaries instead of slides).
- After that, every deck (histology, embryology, RDM, Week 2+) is a `job.yaml` + one command.

*The reviewed pre-engine baselines live in `cards-slideanchored/` (see their READMEs). The older
textbook-mined decks were retired 2026-07-08.*
