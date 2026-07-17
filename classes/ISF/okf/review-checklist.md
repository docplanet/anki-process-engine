---
type: Review Procedure
title: Card review checklist
description: The explicit per-card checks a review pass must run — the loose "does it look right" pass misses defects the rules already forbid.
tags: [anki, card-authoring, review, process]
timestamp: 2026-07-13T00:00:00Z
---

# Why this exists

Cards were reviewed and defects still shipped, because the review checked rules *loosely* — it read
the card and asked "does it look right" instead of running each rule as a concrete check. This file
is the checklist a review (human or agent) MUST run per card. Reviewers should be given these as
explicit instructions, not left to apply the rules from memory.

# Run every check, per card

For EACH card, tested by hiding each cloze in turn:

1. **Self-answering** ([card-structure](/rules/card-structure.md) rule 7) — hide each cloze; does the
   visible text (including the *other* answers) contain or spell out the hidden answer? A structural
   form (–COO⁻, –NH₃⁺), synonym, or definition counts. If yes → defect.
2. **Hint leak** ([hint](/rules/hint.md)) — does any hint name the answer, an instance of it, or a
   property that identifies a small (2–3 member) set? ("acidic AAs" for aspartate/glutamate leaks.)
   Does a hint echo an adjacent visible word, or share the answer's root? → defect.
3. **Hint vagueness** — is any hint a bare catch-all (`what/which` + `type/structure/bond/thing…`)? → defect.
4. **Complete span** ([complete-span](/rules/complete-span.md)) — is the `<i>` answer the WHOLE tested
   value, or a fragment with the rest trailing as plain text? → defect.
5. **Every testable role clozed** ([card-structure](/rules/card-structure.md)) — is any word that the
   card clearly means to test left un-clozed (a condition, a downstream node)? → defect.
5b. **Whole insight clozed** ([whole-insight](/rules/whole-insight.md)) — on a "because/which/so that"
   clause, is only the tail clozed while the subject+verb of the explanation stay visible? Hide the
   cloze: does the stem still reveal the mechanism? If yes, the cloze is too small → defect.
6. **Facet underlined** ([facet-underline](/rules/facet-underline.md)) — is the aspect/category word
   (charge state, pH, pKa, the framing noun) marked `<u>`? Missing → defect.
7. **Cloze content/styling** ([card-structure](/rules/card-structure.md) rule 6) — does any cloze carry
   context beyond the term, or mix styled + unstyled text? → defect.
8. **No terminal punctuation** ([no-terminal-period](/rules/no-terminal-period.md)) — does the rendered
   card end in `.` or `,`? → defect.
9. **Faithful / no editorializing** ([accuracy](/rules/accuracy.md)) — is every term standard field
   language, and every fact/qualifier present in the source? Any coined term ("backbone amine"),
   hedge ("borderline", "most basic"), or added detail → defect.
10. **≤3 clozes; subject leads; one `<i>` answer** ([card-structure](/rules/card-structure.md),
    [subject-first](/rules/subject-first.md)).

# The edit rule

**Any edit re-enters review.** A card changed after its last review is an un-reviewed card — hand-edits
(styling, terminology, restructuring) must run this checklist again, not be trusted because the card
"was reviewed once." Several shipped defects came from edits that skipped re-review.
