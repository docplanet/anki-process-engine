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

Every `::hint` inside a cloze, when substituted into its blank, **must read as natural
English** — as if the hidden text were simply replaced by a placeholder. Beyond reading
naturally, a hint must be **specific**, must **not leak** the answer, and must **not echo**
a visible neighboring word.

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

Applied only to hints that are present (a missing hint stays a soft advisory — the reference
deck hints only ~60% of cards, so requiring a hint everywhere would diverge from house style).

- **Vague blocklist** — reject a hint whose whole text is a bare catch-all:
  `which structure?`, `which cells?`, `which type?`, `which term?`, `which step?`, `what?`, etc.
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
