---
type: Card Authoring Rule
title: Recognition & attribute cards (a distinct genre)
description: Image-recognition and compact attribute cards (e.g. the 20 amino acids) are their own genre, exempt from the sentence mold's one-answer rule.
tags: [anki, card-authoring, recognition, image, attributes, genre]
resource: anki://rule/recognition-and-attribute-cards
timestamp: 2026-07-13T00:00:00Z
enforcement: [judgment]
---

# Why this exists

The [mold](../strict_shape.py) and the sentence-cloze rules ([hint](/rules/hint.md),
[card-structure](/rules/card-structure.md)) were derived entirely from the prose-sentence cloze
cards in the Neurogenetics reference deck. Some material is not prose facts — it is **visual
recognition** (identify a structure) or a **compact attribute lookup** (a term and its fixed
attributes). Forcing those through the sentence mold is the wrong tool: it flags them for
`NO_ITALIC_ANSWER` (an image has no italic text answer) or `TWO_ANSWER_CLOZES` (an entity
legitimately has two attributes worth testing together). This file defines that genre so those
cards are a **documented type, not an exception**.

Note: `TWO_ANSWER_CLOZES` is NOT a blanket "one cloze" ban — it only fires on **prose** cards
(`not is_list`). List/process cards (numbered items sharing a cloze number) are already allowed by
the mold. This genre covers the remaining case: recognition + small fixed-attribute sets.

# The two shapes

## Recognition card — image ⇄ name

Test identification in both directions from one note: the image is one cloze, the name the other.

```
{{c2::<img src="Glycine.png">}}<br><br>This amino acid is {{c1::<b>glycine</b>::which AA?}}
```

- Renders two review cards: image shown → recall the name; name shown → recall/draw the structure.
- The name is the `<b>` subject; the image is a bare cloze (no `<i>` answer — that's expected here).
- Reference image lives in Anki media.

## Attribute card — entity → its fixed attributes

Give the entity; recall its small set of defining attributes (which genuinely belong together).

```
<b>Glycine</b>: {{c1::<u>Gly, G</u>::abbreviations?}}, {{c2::<i>nonpolar (aliphatic)</i>::classification?}}
```

- The entity leads as the visible `<b>` subject; each attribute is its own cloze.
- **Distinct attributes get distinct styling** ([card-structure](/rules/card-structure.md) rule 8) —
  don't make both attribute clozes `<i>` (they'd read identically). Convention: **abbreviations `<u>`,
  classification `<i>`**. Three distinct roles, three stylings (`<b>` entity, `<u>` abbrev, `<i>` class).
- Two (or three) attribute clozes are allowed here — this is the deliberate exemption. Keep it to
  the genuinely-paired attributes; overflow detail goes in `Extra`.

# Still applies (the parts that carry over)

- **Hints still read as natural English** and name a specific category ([hint](/rules/hint.md)).
- **Provenance / supporting detail in `Extra`** (the structure image + key distinguishing property).
- **Yield still governs inclusion** ([yield](/rules/yield.md)) — only card attributes worth testing.

# Enforcement

- **Not gated by the sentence mold.** These cards are expected to fail `strict_shape.py` and that
  is correct; do not "fix" them to satisfy it.
- Judgment only: keep recognition cards to image⇄name, keep attribute cards to the genuinely-paired
  attributes, push everything else to `Extra`.

# Example in the wild

The 20 amino-acid cards in `ISF::Test 2::Biochemistry::Amino Acid Structures` (two notes per AA:
a recognition card and an attribute card).
