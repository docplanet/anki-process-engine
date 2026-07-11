# FILL — generate NEW atomic cards for coverage gaps

You are given a ranked GAP LIST for one deck. Produce ONE atomic Anki cloze card per gap
(occasionally two if a gap genuinely holds two atomic facts). These cards fill holes the
slide-anchored generation missed.

## Card shape — identical to the existing deck (READ 3-4 lines of the deck's cards.reviewed.jsonl first to match exactly)
Schema per line: `{"id","type":"cloze","text","extra","source","tags"}`.

Follow the MOLD (this is hard-gated — a non-conforming card is worthless):
- Roles: `<b>`=SUBJECT (the named thing), `<i>`=ANSWER (the value), `<u>`=FACET (a scoping aspect).
- Shapes allowed: **two-sided** `The {{c1::<b>subj</b>::hint}} {{c2::<i>value</i>::hint}}`; **facet** (`<u>` plain or clozed); **numbered list** (subject one cloze, every item shares the OTHER cloze number, each item one `<i>` span).
- **EVERY cloze carries a short `::hint`** (1–4 words). No bare `{{c1::...}}`.
- **ONE fact per card.** No "A is X; B is Y", no "whereas", no trailing dash-fact, no flattened mapping, no arrows (→), no "term — examples" list items, no terminal period.
- Subject leads (bold before any underline). Answer = exactly ONE `<i>` span. Terse (~10–14 words revealed).

## PROVENANCE — the Extra field (this is the whole point of the fill)
- **If the fact IS on a lecture slide:** `<img src="<slide-image-name>"><br><br><b>Source:</b> <verbatim source text>` — copy the EXACT `<img src=...>` filename pattern + slide-number scheme from existing cards in this deck (look at cards.reviewed.jsonl), pointing to the slide that carries the fact. Images live in `out/slides/`.
- **If the fact is ONLY from an objective / Junqueira summary / transcript (NOT on a slide — which is usually WHY it was missed):** NO image. Use `<b>Source:</b> <EXACT verbatim quote from the source>` — copy the wording character-for-character from the sources dir (the gap list quotes it; verify against the file). Keep the quote short but verbatim.
- `source` field = "Objective" | "Junqueira" | "Transcript" | "Slide" as appropriate.

## ids and tags
- `id` = `<same-prefix-as-deck>-gap-NN` (NN = 01, 02, …). Look at an existing id for the prefix.
- `tags` = copy the deck's base tags from an existing card (e.g. `isf::biochemistry::dietary-fuels`, `week::01`), add `src::gap`. For any gap marked **[beyond-scope]**, ALSO add `flag::beyond-scope`.

## VERIFY before returning (required)
Run: `classes/ISF/.venv/bin/python classes/ISF/strict_shape.py <out>/cards.gaps2.jsonl --json`
It MUST print `N/N conforming (0 rejected)`. Fix every reject and re-run until 0. Confirm no cloze lacks a `::hint`.

## Output
Write ONLY the new cards as JSONL to `<out>/cards.gaps2.jsonl` (one card per line). Report: count written + mold result + how many carry a slide image vs verbatim-source-only.
