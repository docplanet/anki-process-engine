---
type: Card Authoring Rule
title: Cloze hints must read as natural English in the blank
description: A cloze hint is a read-in-place placeholder — specific, non-leaking, non-echoing — not a vague question.
tags: [anki, card-authoring, hint, cloze]
resource: anki://rule/hint
timestamp: 2026-07-13T00:00:00Z
enforcement: [judgment, mechanical]
source_defects: [wrong-first-hint, wrong-second-hint, wrong-undescriptive-hint]
---

# Rule

**Every cloze carries a hint by default.** House style requires a hint on each cloze unless there
is a clear, specific reason not to. (This is a deliberate override of the reference deck, which
hints only ~⅓ of clozes — the same way [card-structure](/rules/card-structure.md) requires the
subject clozed where the reference is looser. Our decks are stricter.)

Each `::hint`, when substituted into its blank, **must read as natural English** — as if the hidden
text were simply replaced by a placeholder. Beyond reading naturally, a hint must be **specific**,
must **not leak** the answer, and must **not echo** a visible neighboring word.

## When a hint may be omitted

**Almost never.** If nothing better fits, use a simple one — `::why?`, `::does what?`, `::how?` — rather
than none. A plain hint beats an absent one; do not reach for an exception because a good hint is
hard to find.

The single exception:

- **List items take no hints.** On a numbered-list card ([mold](/mold.md) shape 3) the items share
  one cloze number and reveal together — the header is the cue. Per-item hints would be identical or
  bare catch-alls. **Hint the header if it's clozed; leave the item clozes bare.**

Anything else needs a hint. In particular these are *not* excuses to omit one:
- the term is `distinguisher + head noun` (cloze the distinguisher — and still hint it)
- the stem "fully determines" the answer (it rarely does for the reviewer; `::why?` still helps)

This is the master principle. The rest of this file is how it applies and how to check it.

# How it applies by blank role

A cloze card has a subject and a predicate; the hint's shape depends on which the blank hides.

- **Term blank** (a *thing* — usually the subject, `<b>`): the hint is a **bare noun-phrase
  placeholder** that slots into the sentence as a noun.
  - "The {{c1::<b>cytotrophoblast</b>::trophoblast layer}} begins forming chorionic villi"
    → reads *"The [trophoblast layer] begins forming chorionic villi."*

- **Predicate blank** (an *action/value* — usually `<i>`): the hint is a short
  **verb-completing fragment** that finishes the clause grammatically.
  - "The syncytiotrophoblast {{c1::<i>establishes nutrient circulation</i>::does what?}}"
    → reads *"The syncytiotrophoblast [does what?]."*

# Requirements (both roles)

1. **Reads in place.** Substituted into the blank, the sentence is grammatical English.
2. **Specific category, not a catch-all.** Never `structure`, `cells`, `type`, `term`,
   `step`, `thing` on their own — name the actual kind of thing.
3. **No leak.** The hint must not contain the answer or an instance of it
   (`e.g. formalin`, `sperm/oocyte` are leaks).
4. **No echo.** The hint must not repeat a word already visible next to the blank
   (`…form the [forms what?]`).
5. **Name a real category; disambiguate only when siblings collide.** The baseline is a
   genuine category, not a vague catch-all — the reference deck reuses generic category hints
   freely (`brain part` across brain stem, cerebellum, diencephalon). Add extra specificity
   *only* when confusable siblings in the same material would otherwise share a hint — then
   disambiguate (male vs. female germ-cell precursors). Never go so specific that the hint
   describes the answer (that leaks).
6. **Signal count.** If the answer is a set of N items, the hint should say so
   (`two gestational structures`).
7. **The hint must match the whole answer — and the fix is ALWAYS to narrow the cloze, never to
   widen the hint.** If the answer is `randomly arranged large collagen bundles`, the hint
   `oriented how?` only addresses the arrangement, so hint and blank don't line up. Narrow the
   cloze to exactly what the hint asks:
   `{{c2::<i>randomly arranged</i>::arranged how?}} large collagen bundles`. Same defect: answer
   `about 90% of the tissue fluid` with hint `what fraction?` — cloze just `about 90%`.

   **ONE INTERROGATIVE PER HINT.** A hint asking two things (`which cells, arriving how?`,
   `which filaments, reaching where?`, `how many of which protein?`, `what cells, in what matrix?`)
   does not fix a bad answer — it disguises one, by making a clause look like a recallable unit.
   Two questions means two facts: split the card or drop the cloze.

   **Measured on the 368-card reference deck (288 hints):** only **4** hints contain more than one
   interrogative word; mean hint length is 1.8 words, max 6.

   **This is NOT a ban on commas.** Option-listing hints (requirement 9) are one question and are
   correct: the reference deck has **30** of them (`increased or decreased`, `5' or 3'`,
   `hyper or hypo`), and `merocrine, apocrine, or holocrine?` is a good hint. Count
   *interrogatives*, not punctuation.

   *An earlier version of this fix banned commas outright. That would have rejected the deck's best
   hints while still permitting `how many of which protein?` — banning the symptom, not the defect.*

   *This rule previously offered "widen the hint" as a co-equal remedy and gave
   `which fibres, arranged how?` as an approved example. A review used that example as a template
   and shipped a defective card — the rulebook supplied the defect. The branch is deleted.*
8. **No invented terminology in a hint** — a hint is card text and is bound by
   [accuracy](/rules/accuracy.md): use real field language. `which developmental class?`,
   `which class of organ-forming tissues?`, `which compartment beneath the epithelium?` are coined
   categories nobody says. If you can't name the category in real terms, do **not** fall back to a
   bare `::what?` — the blocklist below rejects it. Use one of these instead, in order:
   1. a **verb-carrying** minimal hint that reads as a natural blank — `does what?`, `forms what?`,
      `found where?`, `made of what?`;
   2. an **options-listing** hint when the fact is a discrimination — `regular or irregular?`,
      `hydrostatic or colloid osmotic?`;
   3. a **broader but real** category — the lecturer's own adjective often works
      (`which biomechanical junction?` where "musculoskeletal junction" would have been coined).

   Real case: the myotendinous-junction card had the coined category "musculoskeletal junction".
   `::what?` was blocked, so option 3 supplied *biomechanical* — the lecturer's own word.
9. **Binary / small-set answer → list the options.** When the answer is one of a small, known set
   (especially two), the hint gives the *options*, not a vague category. `protonated or deprotonated?`
   beats `what form?`; `cis or trans?` beats `which geometry?`. This is the hint doing its job — the
   purpose of a hint is to make recall *fast* (assemble known pieces, don't struggle to decode what's
   being asked). Listing both options is **not a leak** — you still have to recall *which* one.

# Examples

Before → after, taken from real flagged cards.

## Term blanks (noun-placeholder)

| answer | ❌ before | ✅ after | reads as |
|--------|----------|---------|----------|
| Chemical fixatives | `what agent, e.g. formalin?` (leak) | `preservation agents` | "[preservation agents] preserve tissue by cross-linking proteins" |
| Gametes | `sperm/oocyte` (leak) | `reproductive cells` | "[reproductive cells] are haploid, 23 chromosomes" |
| Oogonia | `which cells?` (vague) | `female germ-cell precursors` | "[female germ-cell precursors] are diploid (46,XX)…" |
| spermatogonium | `which cell?` (vague) | `male germ-cell precursor` | "A [male germ-cell precursor] is a diploid (46,XY) germ cell" |
| cytotrophoblast | `which structure?` (vague) | `trophoblast layer` | "The [trophoblast layer] begins forming chorionic villi" |
| connecting stalk | `forms what?` (echo) | `umbilical-cord primordium` | "…mesoderm to form the [umbilical-cord primordium]" |

Note oogonia vs. spermatogonium: the shared vague `which cell?` failed because it could not
tell them apart; `female` / `male germ-cell precursor` disambiguates (requirement 5).

## Predicate blanks (verb-completion)

| answer | ❌ before | ✅ after | reads as |
|--------|----------|---------|----------|
| the uterine decidua and corpus luteum | `maintains what?` (echo) | `two gestational structures` | "hCG maintains [two gestational structures]" |
| zona pellucida | `within what?` (echo) | `outer egg coat` | "…within the confines of the [outer egg coat]" |

# Enforcement

Split the rule into what code can check vs. what needs reading comprehension.

## Mechanical (hard-gate candidates)

- **Missing hint** — flag any cloze with no `::hint` for review (house style requires one). It
  clears only if a stated exception applies (no non-leaking hint exists, or the stem fully
  determines the answer). Not a silent pass.

Checks applied to hints that ARE present:

- **Vague blocklist** — reject a hint whose whole text is a bare catch-all:
  `which structure?`, `which cells?`, `which type?`, `which term?`, `which step?`, `what?`, etc.
  Note the bare `what?` here is deliberate and consistent with rule 8 above: a hint must carry
  either a verb, an option list, or a real category. `does what?` passes; `what?` does not.
- **Leak** — reject when the hint's significant tokens appear inside the answer text.
- **Echo** — reject when a hint word repeats a word immediately adjacent to the blank in the
  visible sentence.

Validate every mechanical check against the Neurogenetics reference deck before gating, so it
does not over-reject genuine house-style cards.

## Judgment (generator instructions + these examples)

- noun-placeholder vs. verb-completion by role
- reads-as-natural-English
- disambiguation-calibrated specificity
- count signaling
