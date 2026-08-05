---
name: anki-organize
description: Step 2 of 3. Turn an extracted fact inventory into a card plan — decide what earns a card, and name the entity, aspect and value for each. Use after anki-extract and before anki-cards.
---

# What this produces

A **card plan**. One line per card:

```
ENTITY  |  ASPECT  |  VALUE  |  source
T tubules   where found   skeletal and cardiac muscle   Slide 31
Calmodulin  binds         calcium                       Transcript
```

No markup. The entity will become the `<b>` subject, the aspect the `<u>` facet, the value the
`<i>` answer — but that is step 3's problem. Here you decide only **what each card is about** and
**which facts deserve one**.

This step exists because both of those decisions are ruined by having markup in front of you. Once
a sentence exists you start editing the sentence.

# The entity is what the SENTENCE is about — never the lecture topic

This is the most damaging error in the pipeline and it is invisible from inside a card.

Working under a heading called "smooth muscle" makes that phrase the most available noun in your
head, and it lands in the subject slot on card after card. *One deck ran 24 of 31 cards as
"Smooth muscle …" with the identical hint `which muscle?`. That is not 24 cards; it is one card
asked 24 ways, in a section where "which muscle?" is already answered by context.*

"Smooth muscle has no T-tubules" is **about T tubules**:

```
ENTITY: T tubules   ASPECT: where absent   VALUE: smooth muscle
```

The entity is a real thing rather than a heading, and one source sentence still proves it —
*"There are no tubule systems at all."* **Do not upgrade this into a distribution summary**
("T tubules are found in skeletal and cardiac muscle") unless a single source states it: that
sentence is true but appears nowhere, and a card built on it has no verbatim quote to carry.

**Check before handing the plan on: if a single entity appears in more than a quarter of the lines,
the entities are wrong.** Go back through fact by fact and ask what the sentence is about.

The wrong entity is also the source of nearly every deformed card, because filler is needed to bolt
a fact onto a subject that is not its subject:

| written | real entity | what the wrong entity forced |
|---|---|---|
| "A **muscle fiber**'s plasma membrane is called the sarcolemma" | sarcolemma | a possessive |
| "In cross section, **skeletal muscle** fibers appear polygonal" | the cross-section appearance | a preamble |
| "Of the three fiber types, **Type IIb** has the fewest…" | mitochondria content | a premise |
| "**Smooth muscle** differs from striated muscle in having no tubule system" | T tubules | an invented — and untrue — comparison |

# What earns a card

- The bar is not "is it true" but **"did the teacher signal this as need-to-know."**
- **A slide bullet is not a fact.** A ten-bullet slide is one or two cards, not ten. Ask what an
  exam question on that slide looks like and plan *that* — usually a few parallel cards on the axes
  that discriminate. *Three fiber-type slides once produced 25 cards this way; the exam-shaped
  version is about 15.*
- **Discrimination is an inclusion gate and it runs first.** If a fact is true of its subject and of
  everything else in the course, there is no card. *"Cells cut through cytoplasm show no nucleus"
  is a sectioning artifact true of every tissue.* Keep a fact whose **forward** direction
  discriminates even when the reverse does not — "each smooth muscle cell has one nucleus" is
  specific against skeletal's multinucleate fibers.
- Cut vague values — "generate high peak muscle tension", "provides support and protection". If the
  value is not a term, a number, or a definite phrase, there is nothing to produce.
- Cut anecdotes, slide furniture, and restatements of a card you already planned.
- **Zero cards for a slide is fine. Zero for a taught topic is a failure.**
- If the instructor said not to memorise it, or that a value will be given, it does not get a card.
- **Nothing is dropped silently.** A cut fact stays in the plan with its reason.
- **A cut reason must be a checkable claim, not a label.** If the reason is "covered elsewhere",
  name the card that covers it; if it is "slide furniture", the slide element must genuinely be
  structure — a header or an agenda — and not content that happens to be laid out as an outline.
  *"Calcium is found in the SR and the cytosol" was cut as furniture whose mechanism cards carried
  it. The slide was an outline but the line was a fact, and no card in the plan contained the word
  cytosol at all — the storage half was covered three times and the destination not once.*

# Two facts or one

Two independent properties are two cards, however the slide punctuated them — "many mitochondria
and abundant myoglobin" is a bullet, not a fact. **The punctuation is not evidence about the fact
count.** A multi-item value is one card only when the *set* is what is recalled: the three classes,
the five zones.

Two cards teaching one fact are one card. A shared sentence frame is not a shared fact — parallel
cards on contrasting terms are correct and wanted.

# Using what you know

Your knowledge of the field **selects, structures, audits and finds gaps**; the sources supply the
words. It tells you which five of fifty true statements matter, that a fiber-type slide is one
comparison matrix rather than ten bullets, that "H zone" and "H band" are the same thing — and,
most valuably, what an objective demands that the lecture never said, so you know where to look.
*A lecture skipped smooth-muscle innervation entirely; knowing the topic exists is what sent the
search to the textbook, which had it verbatim.*

What it must never do is put a fact in the plan that no source states. If nothing in the sources
covers an objective, that is a gap to report to the user, not one to fill from memory.

**Where your knowledge and the instructor disagree, the instructor wins** — he writes the exam —
**and the disagreement is raised, not silently corrected.**

# Precedence and scope

**objectives** (the coverage contract) ▸ **slides** (the anchor) ▸ **transcript** (emphasis) ▸
**textbook** (precision). Where sources conflict on fact, plan what the slides and textbook agree
on and raise the conflict. Never ship both sides.

Scope by **session**, not topic: everything taught in the recording, including material carrying
over from last week. Slides the lecture never reached belong to the next deck.
