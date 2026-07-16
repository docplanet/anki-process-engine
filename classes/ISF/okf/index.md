---
type: Knowledge Bundle Index
title: ISF Card-Authoring Rules
description: The rules a generator must follow to produce good ISF Anki cloze cards, one rule per file.
tags: [anki, card-authoring, isf, rules]
timestamp: 2026-07-13T00:00:00Z
---

# ISF Card-Authoring Rules

## Governing principle: faithful transcription, not synthesis

Card creation is a **faithful rendering of the provided material into card shape — a robust
copy/paste, not a rewrite.** The generator's job is to take the facts *as the source states them*
and restructure them into atomic cloze cards: split into one-fact cards, choose what to cloze,
apply markup and hints, tag provenance. That is the entire transformation.

**Add nothing.** No outside knowledge, no synthesized framing, no coined or reframed terminology,
no editorializing. Editorializing is minimized to near-zero: if a fact, term, or qualifier is not
in the source, it does not go on the card. When a hint or label has no basis in the source's own
words, leave it out (hints are optional) rather than invent one. The facts are the source's; only
the *shape* is ours.

Every rule below serves this principle — the shape rules say how to restructure faithfully; the
[accuracy](/rules/accuracy.md) rule guards against anything creeping in that the source didn't say.

A vendor-neutral rulebook for generating ISF Anki cloze cards. Each rule is a separate
OKF file so it can be cited, reviewed, and enforced independently. Rules are derived from
real defects found in the shipped decks (tagged `wrong-*` in Anki) and stated as crisp,
testable contracts — the source of truth for any future card generation.

Rules split into two kinds:
- **judgment** — requires reading comprehension; belongs in the generator's instructions + worked examples.
- **mechanical** — checkable by code; can be enforced as a hard gate.

Most rules are partly both: as much as possible is pushed to mechanical enforcement, and the
irreducible taste is stated with worked examples.

# Rules

| Rule | Source defect tags | Status |
|------|--------------------|--------|
| [Hints](/rules/hint.md) | `wrong-first-hint`, `wrong-second-hint`, `wrong-undescriptive-hint` | drafted |
| [Subject leads the card](/rules/subject-first.md) | `wrong-style-off`, `wrong-sentence-structure` | drafted |
| [Card structure](/rules/card-structure.md) | `wrong-structure`, `wrong-missing-cloze`, `wrong-incorrect-clozes` | drafted |
| [Yield](/rules/yield.md) | `wrong-low-yield` | review-gated (no firm rule yet) |
| [Underline the facet](/rules/facet-underline.md) | `wrong-missing-underline` | drafted |
| [Accuracy](/rules/accuracy.md) | `wrong-information` | review-gated |
| [No near-duplicates](/rules/no-duplicate.md) | `wrong-duplicate` | drafted |
| [Recognition & attribute cards](/rules/recognition-and-attribute-cards.md) | (new genre — image⇄name, entity→attributes; mold-exempt) | drafted |
| [The answer is a complete span](/rules/complete-span.md) | `wrong-style-off` (fragmented answer) | drafted |

# Coverage

All 12 `wrong-*` defect classes from the current decks are now turned into rules:

| defect tag | rule |
|-----------|------|
| `wrong-first-hint`, `wrong-second-hint`, `wrong-undescriptive-hint` | [hint](/rules/hint.md) |
| `wrong-style-off` (partial), `wrong-sentence-structure` | [subject-first](/rules/subject-first.md) |
| `wrong-structure`, `wrong-missing-cloze`, `wrong-incorrect-clozes` | [card-structure](/rules/card-structure.md) |
| `wrong-low-yield`, `wrong-style-off` (scope-qualifier part) | [yield](/rules/yield.md) |
| `wrong-missing-underline` | [facet-underline](/rules/facet-underline.md) |
| `wrong-information` | [accuracy](/rules/accuracy.md) |
| `wrong-duplicate` | [no-duplicate](/rules/no-duplicate.md) |

The flagged set was not exhaustive (not all cards were reviewed), so new defect classes may still
appear; each becomes a new rule file here.
