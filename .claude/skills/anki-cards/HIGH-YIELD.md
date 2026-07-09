# High-Yield Rubric — how many cards a unit earns (standalone, load-bearing)

**This decides YIELD, not shape.** For ONE anchor unit (usually one lecture slide; a chapter-
summary bullet where there's no deck) it answers a single question: **how many cards does this
unit earn (0–4), and of what type?** Card SHAPES live in [`MARKUP.md`](MARKUP.md); the STYLE/SENSE
contract lives in [`SKILL.md`](SKILL.md). This file never redefines a shape — it points at one.

**Two agents ground on this file:** a **proposer** proposes a yield, an independent **verifier**
re-derives it. They must reach the same number for the same reason, or escalate. See §6.

---

## The governing principle — RESTRAINT

**Teachers are clear about what needs to be known.** The anchor document (slides, or a chapter
summary) IS the teacher's signal; the transcript reveals what was **stressed**. The old flow
"threw too much at the system" — mining every fact — and minted low-yield cards. So the bar is
not "is this true / is this in the textbook" but **"did the teacher signal this as need-to-know?"**

- **Default is 1.** Most stressed slides earn exactly one card.
- **0 is normal and legitimate** (§3) — not a failure.
- **Density reference = AnKing Neurogenetics:** ~1 card per stressed slide, occasionally 2; a
  whole SEMESTER ≈ 670 cards. If a lecture is trending past ~1 card/slide, you're mining, not measuring.

### The precedence rule — objectives are the CONTRACT (RESTRAINT has a floor)

A learning **objective** is a promise the teacher made about what must be known — it outranks
slide-emphasis. RESTRAINT governs *slides*, never *objectives*: **an objective-backed fact is never
dropped to 0.** If the transcript DEFERRED it ("*not on Exam 1*"), it is still carded — but tagged
`flag::beyond-scope` (suspendable), never deleted. So "not stressed → 0" (§3) applies only to
*un-objectived* slide content; every objective earns **≥1 card**. The run-level **COVERAGE** stage
enforces this after generation: it maps each objective to its card(s) and drafts a (beyond-scope,
if deferred) card for any objective the slide-walk missed. The ship gate blocks on any *uncovered*
objective. Document precedence overall: **objectives = the coverage contract** ▸ **slides = the
anchor** ▸ **transcript = emphasis/priority** ▸ **textbook = precision**.

---

## §1 · The yield question — n_cards ∈ 0..4

Pick one number per unit.

| n | When |
|---|---|
| **0** | Teacher waved past it · title/agenda/transition slide · already carded by a sibling · un-testable narrative (§3) |
| **1** | **DEFAULT.** One discrete stressed fact (one definition, one value, one mechanism, one association) |
| **2** | Two *independent* stressed facts on the unit, OR a term whose definition is genuinely worth both directions on separate notes (§5) |
| **3** | Rare. Three independent stressed facts, or a stepwise process with three distinct tested steps (§5) |
| **4** | **Hard cap. Almost never right.** Only a unit the teacher dwelt on that carries four genuinely independent stressed facts |

- **4 is the ceiling, not a target.** Reaching for 4 is the signature of the old exhaustive
  flow. If a unit "needs" 5+, you are mining the textbook, not reading the teacher — recount
  against emphasis, or the unit spans two anchors and should be split.
- **A single multi-cloze note ≠ multiple cards here.** n_cards counts NOTES (anchor-unit yield),
  not the sibling review-cards a multi-cloze note spawns. Consolidate a unit's facets into one
  note per the style contract; n is how many *notes* the unit earns.
- **A memorized list is n=1.** One list under one shared cloze number is ONE note (one card
  here), however many items it holds.

---

## §2 · What EARNS a card

A card is earned by a **testable, discrete, high-yield fact the teacher signaled** — tie it to
**emphasis (slide + transcript)**, never to textbook exhaustiveness. Earners:

- **Definition** of a key term the teacher named.
- **Mechanism / process** the teacher walked through (a reaction, a pathway step, a "how").
- **Value / number the prof stressed** — a size, %, count, threshold, ratio they called out
  (not every incidental figure on the slide).
- **Classification / category** the teacher drew (type A vs B, the members of a class).
- **Board-relevant association** the teacher flagged (structure→function, dye→what it stains,
  gene→disease, marker→cell).

**Litmus (must pass BOTH):**
1. **Signaled?** — did the professor stress it (transcript) and/or is it on an objective? If
   neither, it does not earn a card, however true it is.
2. **Testable & discrete?** — can it be a clean subject→answer retrieval? If it's mush ("X is
   important", "we'll discuss Y"), it does not earn one.

> Precision ≠ yield. Once a fact earns its card, KEEP its board-style specifics (exact nm, %,
> counts) per the style contract. Emphasis decides *whether* and *how many*; precision decides
> *the wording*. Don't confuse "keep the number on the card" with "the number earns its own card."

---

## §3 · What earns 0 — first-class outcomes

**0 is a considered decision with a stated reason, NEVER a silent drop.** Legitimate zeros:

- **Waved-past slide** — shown but not stressed; the teacher moved on. Reason: `not-stressed`.
- **Title / agenda / transition / roadmap slide** — no testable content. Reason: `no-testable-content`.
- **Already carded by a sibling unit** — the fact is covered by an earlier slide's note; carding
  it again is a duplicate. Reason: `dup::<where>`. (Dedup is a yield decision, not a style one.)
- **Un-testable narrative** — motivation, anecdote, "why this matters" framing with no discrete
  recallable fact. Reason: `narrative`.
- **Beyond-scope aside** — correct but the prof explicitly deferred it. If you card it anyway
  (borderline), it's `flag::beyond-scope` per [`SKILL.md`](SKILL.md); usually it's a 0.

Record the reason in the proposal. A 0 with a reason is a *pass*, not a gap.

---

## §4 · Card-type selection — per earned fact

For each fact you kept, pick the shape by its SHAPE. **Shapes are defined in
[`MARKUP.md`](MARKUP.md) — this is only the chooser.**

| The fact is… | Use | (MARKUP shape) |
|---|---|---|
| a term + its definition / function / a single association / a stressed value | **canonical cloze** | `The {{c1::<b>subject</b>}} [plain] {{c2::<i>answer</i>}}` |
| a "why / how / compare" on ONE axis | **two-sided cloze** (both sides clozed) | canonical, both term & consequence blanked |
| substrate → process → product (a reaction/conversion) | **transformation** | the 3-role substrate/process/product card |
| a set that must be **produced whole** (members of a class, components) | **memorized list** | items sharing ONE cloze number |
| recognition of a structure/image by sight | **image / visual-ID** | the `image` card |

Rules of thumb:
- **Text fact → always a cloze.** There is no basic Q&A card for text (style contract). A
  "compare" is not an exception — it's a two-sided cloze.
- **A "draw it / show all atoms" task is not a card** — it's an image card or a 0. Never a cloze.
- **Two distinct concepts → two cards, not one contrast.** If each side stands alone as its own
  definition, that's n≥2 with two canonical cards — not a single crammed note (style contract).
- **Don't upgrade a shape to fit more in.** The shape follows the fact; it never justifies a
  higher n.

---

## §5 · When a unit legitimately needs 2–4

Raise n ONLY on these crisp triggers — each must be a fact the teacher stressed:

- **Multiple independent stressed facts** — two/three facts on the unit that do NOT share a
  subject and can't consolidate into one note's facets. (Facets of the SAME thing = still n=1,
  one multi-cloze note.)
- **A list that must be produced** — earns its ONE list note (n=1); if the teacher ALSO stressed
  a fact about the list's subject, that's a second note (n=2).
- **A process with distinct tested steps** — the teacher walked step-by-step and each step is
  independently testable. Card the steps the teacher dwelt on, not every arrow.

**Worked — n=1 (biochem).** Slide: "Hexokinase phosphorylates glucose → glucose-6-phosphate
(first step of glycolysis)." One stressed mechanism, one subject. → **n=1**, transformation:
`{{c1::<b>Hexokinase</b>}} phosphorylates {{c2::<i>glucose</i>}} to {{c3::<u>glucose-6-phosphate</u>}}`
(shape per MARKUP). The "first step of glycolysis" is context, not a second card.

**Worked — n=2 (histology).** Slide: "H&E — hematoxylin stains acidic structures blue
(basophilic); eosin stains basic structures pink (acidophilic)." Two independent dye facts,
different subjects, can't consolidate without a self-answering cram. → **n=2**, two canonical
clozes (one per dye). NOT one 4-cloze contrast (that's the eosin defect in MARKUP).

**Worked — n=3 (biochem).** Slide the prof dwelt on: "Glycogen store ≈ 100 g liver / 400 g
muscle; liver glycogen buffers **blood glucose**, muscle glycogen fuels **muscle only**." Three
stressed, independent facts: the two values (one list/value note) + liver's role + muscle's role.
→ **n=3** (or n=2 if the two values consolidate into one note and the two roles are one contrast
axis — proposer/verifier adjudicate). This is the top of the normal range; a fourth card here
would be mining.

---

## §6 · The consensus contract

Two agents ground on THIS file and must converge.

**Proposer** emits, per anchor unit:
```
unit: <slide N / summary bullet>
n_cards: <0–4>
reason: <the rubric clause that sets n — §2 earner(s), or §3 zero-reason>
cards:
  - concept: <the one fact this card tests, in a phrase>
    type:    <canonical | two-sided | transformation | list | image>  (§4)
    rationale: <which §2 earner + why THIS type per §4>
  … (one per card; empty when n=0, with the §3 reason)
```

**Verifier** independently re-derives n_cards from the SAME rubric — does NOT anchor on the
proposer's number — then returns **AGREE** or **DISAGREE**:
```
verdict: AGREE | DISAGREE
n_cards: <verifier's own count>
reason: <rubric clause>            # on DISAGREE, name the specific clause and the delta
```

**A valid rationale** cites a rubric clause and ties it to the teacher's signal — e.g. "§2
mechanism, stressed in transcript ~12:30; §4 transformation." Not valid: "seems useful," "the
textbook covers it," "could be on the exam" with no emphasis cite.

**A valid disagreement** names the clause and the specific delta — e.g. "proposer's card 3 is
§3 `dup::slide-14`, so n=2 not 3," or "the two facts share a subject → one §1 multi-cloze note,
n=1 not 2." Not valid: a bare different number, or a style/wording complaint (that's SKILL.md's
axis, not this one).

**Resolution:**
- **AGREE (same n, compatible reasons)** → the yield is fixed; generation proceeds.
- **DISAGREE they can reconcile** (one cites a clause the other missed — a dup, a shared subject,
  a not-stressed slide) → adopt the clause-backed count; record the corrected reason.
- **Genuine disagreement** (both cite the rubric, neither clause dominates — e.g. "is this ONE
  process or THREE steps the prof stressed?") → **escalate to the human** with both counts and
  both clause citations. Do not average, do not default to the higher number. When in doubt the
  rubric's thumb is on RESTRAINT — but a true tie is the human's call, not a silent pick.
