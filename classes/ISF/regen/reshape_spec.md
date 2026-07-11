# RESHAPE — make each card match the real Neurogenetics reference deck

> Historical note: this spec drove the *reshape* pass (recast already-correct facts into the mold's
> shape). The final regen pipeline supersedes reshaping with atomic-first generation
> (`fill_spec.md` + the generate contract in REGEN-PIPELINE.md), but the shape rules below are the
> canonical statement of the mold and remain the reference for `strict_shape.py`.

You are given a deck of Anki cloze cards whose **facts are already correct** (they passed
accuracy review). They are shaped WRONG. Your only job is to **recast each card into the shape of
the real reference deck below.** Do not re-derive facts. Do not consult slides. Preserve the
meaning, and copy each card's `extra`, `source`, and `tags` UNCHANGED.

## The three roles → three colors (this is the whole system)
- `<b>bold</b>`  = **SUBJECT** — the named thing the card is about.
- `<i>italic</i>` = **ANSWER** — the value / description / consequence.
- `<u>underline</u>` = **FACET** — a scoping aspect/part/subdivision/condition of the subject.

**A role is not a position. ANY of the three can be the clozed blank OR left as plain context** —
you cloze whichever role the card is testing. Put markup INSIDE the braces: `{{c1::<b>term</b>}}`.
Connecting words ("is", "controls", "of the") stay PLAIN.

## The three reference shapes — COPY THESE (real cards from the ideal deck)

**1. TWO-SIDED (bold subject ↔ italic answer, 2 clozes, terse).** The default.
- `The {{c1::<b>brain stem</b>::brain part}} controls {{c2::<i>automatic behaviors necessary for survival (heart rate, breathing)</i>::what functions?}}`
- `The {{c1::<b>thalamus</b>::which structure?}} {{c2::<i>relays and processes sensory information</i>::does what?}}`

**2. FACET / UNDERLINE (`<u>` scopes the question — ~26% of real cards).** The facet may be plain
context OR itself be clozed:
- facet as CONTEXT: `The {{c1::<b>central sulcus</b>::which sulcus?}} of the <u>cerebral cortex</u> {{c2::<i>separates motor and sensory areas</i>::does what?}}`
- facet CLOZED (the blank IS the facet): `<b>Cerebral cortex</b> {{c1::<u>sensory areas</u>::which areas?}} {{c2::<i>control conscious awareness of sensation</i>::do what?}}`

**3. NUMBERED LIST ("counting things" — ~24% of real cards).** For a set recalled together.
- `The {{c2::<b>diencephalon</b>::which brain part?}} contains:<br><br>1. {{c1::<i>Pineal gland</i>}}<br>2. {{c1::<i>Thalamus</i>}}<br>3. {{c1::<i>Hypothalamus</i>}}`
Subject = one cloze (bold). EVERY item shares the OTHER cloze number, each ONE `<i>` span. Never
chop an item into italic-plus-underline pieces.

## HARD RULES
1. **EVERY cloze carries a short `::hint`** — a 1–4 word cue (`::which enzyme?`, `::does what?`,
   `::how much?`). Both the subject cloze and the answer cloze. No bare `{{c1::...}}`.
2. **ONE concept per card.** If a card defines TWO named things — "A is X; B is Y", "A…whereas B…",
   "…makes it a Z" — SPLIT into two atomic cards, one per concept. The second keeps the same `id`
   with a `b` suffix (`u_ab12` → `u_ab12` and `u_ab12b`). Each half keeps the original extra/source.
3. **Subject is CLOZED and bold** (two-sided: blank the subject AND its value) — not left exposed.
4. **Answer = exactly ONE `<i>` span.** Never split the answer across italic + underline.
5. **Terse:** ~10–14 words revealed. Long or 3+ facts → split.
6. `type` stays `"cloze"`. No terminal period.
7. **SUBJECT LEADS** — the `<b>` subject must appear before any `<u>` facet. Never open a card with a facet ("The <u>final step</u> of <b>X</b>…" is WRONG → "The <b>X</b> <u>final step</u>…").
8. **FACET CLOZING** — a `<u>` facet may be plain context OR clozed on its own c#. Cloze it when it's the distinguishing/testworthy term (which bonds? which areas?); leave it plain only for pure orientation (which region/organ).
9. **NO arrows** (→/->/&rarr;) and **no "term — examples" bundles** in a list item (each list item is one short `<i>` value).

## ATOMICITY — one fact per card (a GATED dimension, not advice)
- **ONE testable fact per card.** A card that tests two facts is two cards.
- **ONE item per blank** — the ONE exception is a genuine memorized SET recalled together
  (`{{c1::<i>mesencephalon, pons, and medulla</i>}}`), fine as a single cloze.
- **NEVER flatten a mapping** into two parallel multi-item blobs → hard reject `FLATTENED_MAPPING`.
  ❌ `{{c1::<b>cranial, caudal, ventral, dorsal</b>}} correspond to {{c2::<i>superior, inferior, anterior, posterior</i>}}`
  ✅ four atomic pairs: `The embryonic term {{c1::<b>cranial</b>}} corresponds to the adult {{c2::<i>superior</i>}}` … (one per pair)
- **NEVER append a dangling second fact** after the answer via a dash/`;`/`:` → hard reject `TRAILING_FACT`.
  ❌ `The {{c1::<b>carbonyl carbon</b>}} is {{c2::<i>the C=O carbon</i>}} — C1 in aldoses, C2 in ketoses`
  ✅ two cards: the definition, and a separate "located at C1 in aldoses / C2 in ketoses" card (or trim if covered elsewhere).

## VERIFY — required before you finish
Run this on your output and it MUST print `N/N conforming (0 rejected)`:
```
classes/ISF/.venv/bin/python classes/ISF/strict_shape.py <your cards.reshaped.jsonl>
```
Fix every reject and re-run until 0. Also confirm NO cloze is missing a `::hint`. The `facet worklist`
it prints is advisory (your judgment on rule 8), not a failure.

## Output
Write valid JSONL — one card per line, fields `id, type, text, extra, source, tags`. Copy
`extra`/`source`/`tags` verbatim from the source card (both halves of a split share them; the
`b` card copies from its parent). Do NOT modify the original file.
Also NOTE (do not delete) any cards that look like near-duplicates of each other — list their ids
for a human to dedup later. Dedup is a SEPARATE pass; this pass only reshapes.
