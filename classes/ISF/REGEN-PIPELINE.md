# ISF Card Pipeline — Atomic-First Regeneration (as-run record)

This documents the pipeline that produced the **current `ISF::Test 1` decks (690 cards, 7 lectures)** —
a from-source *regeneration* that is **distinct from** the committed `process_engine` state machine
(see [PROCESS-ENGINE.md](PROCESS-ENGINE.md)). It ran as **parallel Claude subagents orchestrated by
hand**, gated at every card-producing step by **the mold** (`strict_shape.py`) — the hard pass/fail
shape classifier, built because the calibrated linter (`lint_cards.py`) was too permissive and let
malformed cards ship.

Because the original orchestration lived in an ephemeral scratchpad that was wiped, this file is the
**durable record**: the stage contracts (what each subagent is told), the artifact schemas, and the
supporting scripts (reconstructed in [`regen/`](regen/)). It is written so the pipeline is
**reproducible** — the reconstructed `regen/merge_gaps.py` re-derives every deck's `cards.final.jsonl`
byte-for-byte from the surviving stage outputs.

> All Python commands use the project venv: **`classes/ISF/.venv/bin/python`**.

---

## Why a separate pipeline

The engine generates well-shaped cards but its gate is *advisory-calibrated* (errors on <2% of the
reference deck by design). This session's bar was **100% stylistic consistency + one-fact atomicity +
full objective/source coverage** — so cards were **regenerated from source, atomic-first**, and every
card had to pass a *hard* template gate. The three quality axes, all hard-gated:

- **SHAPE** — matches one of the mold templates T1–T5/LIST (`strict_shape.py`).
- **ATOMICITY** — one testable fact per card; no flattened mappings, trailing facts, or bundled answers.
- **RELEVANCE** — every card traces to a slide, objective, Junqueira summary point, or transcript emphasis.

---

## The spine

```
slides.jsonl ─▶ facts.jsonl ─▶ cards.regen.jsonl ─▶ cards.reviewed.jsonl ─▶ cards.gaps2.jsonl ─▶ cards.final.jsonl ─▶ Anki
  (Stage 0)      (Stage 1 DB)    (Stage 2 generate)   (Stage 3 review+dedup)  (Stage 4 coverage)     (merge)          (Stage 5)
```

Per deck, all artifacts live under `<Week X/Subject/NN-deck>/out/`. **`cards.final.jsonl` is the
source of truth**; every earlier `*.jsonl` is a regenerable intermediate.

---

## Stage 0 — Slides & sources → raw material
- `regen/build_slides_db.py <slides.pdf> <out_dir> <deck-slug>` renders each slide to
  `out/slides/isf-<slug>-slide-NN.jpg` and writes **`slides.jsonl`** (`{slide, image, text}`).
- Zero-pad width follows `pdftoppm`: a >99-slide deck (histology, 108) → 3-digit `-004`; ≤99 → 2-digit
  `-04`. Downstream image refs depend on this exact convention.
- The three ground-truth sources (learning **objectives**, Junqueira chapter **summaries**, lecture
  **transcript**) are placed in the deck's `sources/`.

## Stage 1 — Extract into the fact DB (`facts.jsonl`)
Extraction subagents read `slides.jsonl` + the three sources and emit one row per **atomic fact**:
```json
{"id","slide","image","fact","source_type":"slide|objective|junqueira","source_exact":"<verbatim>"}
```
**Agent contract:** one atomic fact per row; ground every fact in a slide *or* a verbatim source line;
capture `source_exact` character-for-character (this becomes the card's answer-side proof). Prioritize
what the objectives/transcript name as testable.
**Audit:** `regen/audit_facts.py "<deck>" <n_slides>` — field completeness, image refs resolve,
slide range valid, non-atomic "smell" (semicolons / whereas / but).

## Stage 2 — Generate cards from the DB (`cards.regen.jsonl`)
Card-writer subagents read **`facts.jsonl` only** (never the slides directly) and emit:
```json
{"id","type":"cloze","text":"<mold-shaped, full markup + ::hints>",
 "extra":"<img src=…><br><br><b>Source:</b> <verbatim>","source","tags"}
```
**Agent contract — the mold** (canonical statement in [`regen/reshape_spec.md`](regen/reshape_spec.md)):
- Roles → colors: `<b>` SUBJECT, `<i>` ANSWER, `<u>` FACET. Any role can be the clozed blank.
- Allowed shapes: **two-sided** (`{{c1::<b>subj</b>::hint}} {{c2::<i>val</i>::hint}}`), **facet**
  (`<u>` plain or clozed), **numbered list** (subject one cloze; every item shares the *other* cloze
  number, each item one `<i>` span). ≤3 clozes (usually 2), ~10–14 words revealed, no terminal period.
- **Every cloze carries a short `::hint`.** **One fact per card** — no "A is X; B is Y", no arrows,
  no flattened mappings, no trailing dash-facts, no "term — examples" list items.
- **Provenance rule (the point of the DB):** `extra` = `<img src="…slide-NN.jpg"><br><br><b>Source:</b>
  <verbatim>` when the fact is on a slide; else **verbatim source text only, no image** (an
  objective/Junqueira/transcript fact legitimately has no slide).
**Gate:** `regen/audit_regen.py "<deck>" cards.regen.jsonl` — runs the mold (0 rejects), checks a
`::hint` on every non-list cloze, a resolvable `<img>` (when present), and a `Source:` in every `extra`.

## Stage 3 — Content review + dedup (`cards.reviewed.jsonl`)
Review subagents verify each card is faithful to its `source_exact` and drop near-duplicates.
`regen/`-adjacent `content_check.py` flags near-dup pairs (SequenceMatcher ≥0.66, skipping
same-base-id siblings), over-carded subjects, and long tails for a human call.

## Stage 4 — Coverage cross-reference + gap-fill (`cards.gaps2.jsonl` → `cards.final.jsonl`)
The **relevance** gate. Per deck, coverage subagents walk the three sources **ranked by exam signal**
and emit a gap list — items with no card:
1. **Transcript emphasis** ("you'll be examined / I want you to know") — strongest signal.
2. **Learning objectives** — the written contract.
3. **Junqueira "Summary of Key Points"** — textbook high-yield.
Fill subagents (contract in [`regen/fill_spec.md`](regen/fill_spec.md)) generate the missing cards →
`cards.gaps2.jsonl`, same mold gate, same provenance rule (most gap cards are verbatim-source-only —
*not being on a slide is usually why they were missed*). Beyond-scope-but-correct facts are kept and
tagged `flag::beyond-scope`, never dropped.
**Merge:** `regen/merge_gaps.py` audits the gaps (mold + provenance), normalizes tags (`src::gap`),
writes `cards.final.jsonl = reviewed + gaps`, and (unless `--no-anki`) pushes the gap cards to the
`ISF::Regen Preview` decks.

## Stage 5 — Into Anki
- **Preview (non-destructive):** `regen/sync_regen_preview.py [cards.final.jsonl]` — `storeMediaFile`
  uploads slide images, builds `ISF::Regen Preview::<name>` for human review before touching real decks.
- **Ship (destructive):** `regen/replace_real.py --yes` — deletes each real `ISF::Test 1::…` leaf
  deck's notes (and review history), then adds `cards.final.jsonl` tagged `key::<slug>::<id>`. That key
  makes future edits idempotent via `sync_anki.py` — no more wholesale replacement.

---

## Relationship to `process_engine` (the reconciliation)

The two pipelines are conceptually the same shape; they differ in **gate** and **orchestration**:

| regen stage | process_engine analogue | gate |
|---|---|---|
| Stage 1 facts.jsonl DB | `scaffold` + `emphasis` (extra capture) | — |
| Stage 2 generate (mold) | `generate` + `markup` | **mold** vs `lint_cards` |
| Stage 3 review + dedup | `accuracy` + `style` | mold vs review-ledger |
| Stage 4 coverage + fill | `coverage` stage | tiered gap-list vs objective-map |
| Stage 5 sync | `build_apkg` / `sync_anki` | shared |

**Open reconciliation (task #4):** fold the mold (`strict_shape.py`), the provenance rule, and the
tiered coverage pass into `process_engine` so future decks generate this way **natively** — instead of
the manual subagent orchestration this session ran. Until then, this pipeline is driven by hand +
[`regen/`](regen/) scripts, and the engine remains the lint-gated path.

---

## Files

| Path | Role |
|---|---|
| `strict_shape.py` | **the mold** — hard pass/fail shape classifier (T1–T5/LIST); CLI `strict_shape.py <file> [--json]` |
| `content_check.py` | deck-level content detectors (near-dupes, over-carding, tails); imports the mold |
| `../tests/test_strict_shape.py` | mold self-test — 100% accept / 100% reject fixtures + reference-fidelity ≥90% |
| `regen/build_slides_db.py` | Stage 0 — render slides + build `slides.jsonl` (reconstructed) |
| `regen/audit_facts.py` | Stage 1 audit |
| `regen/audit_regen.py` | Stage 2/4 audit (mold + hints + provenance) |
| `regen/merge_gaps.py` | Stage 4 merge → `cards.final.jsonl` |
| `regen/sync_regen_preview.py` | Stage 5 preview |
| `regen/replace_real.py` | Stage 5 ship (destructive; needs `--yes`) |
| `regen/fill_spec.md` | the gap-fill agent contract |
| `regen/reshape_spec.md` | the mold, stated in full (canonical shape reference) |

**Verify anytime:** `classes/ISF/.venv/bin/python -m unittest tests.test_strict_shape` (mold self-test)
and `classes/ISF/.venv/bin/python classes/ISF/regen/audit_regen.py "<deck>" cards.final.jsonl` (deck vs mold).
