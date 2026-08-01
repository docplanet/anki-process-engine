# Anki cards for the Bastyr ISF decks

Files go in, cards come out.

You put a lecture's material in a folder — slides, the transcript, a textbook summary — say which
of them to card, and get reviewed Anki cloze cards in the deck you name.

**All of it is one file:** [`.claude/skills/anki-cards/SKILL.md`](.claude/skills/anki-cards/SKILL.md).
It holds the six cards that define the style, what a normal card looks like, and the rules that
don't fit in an example. There is no program to run.

> This repo is the **method only**. Course materials — textbooks, recordings, transcripts, your
> decks — are gitignored and stay local.

## How to use it

Put the material in a folder and say what to card:

> Make cards for this week's histology lecture. The folder is
> `classes/ISF/Exam 2/Histology/Week 5/Bone` — card the PowerPoint, the transcript, and the
> Junqueira summary. Deck is `ISF::Test 2::Histology::Bone`.

Then: sources get read one at a time, cards get drafted, **each source is read back against the
deck to find what was taught and never carded**, every card is reviewed against the six examples,
and you see the whole deck in a file before a single note reaches Anki.

Scope is stated, never inferred. Naming the files is how you say what must be carded.

## Why there is no code

There was: 2,924 lines of Python and 80,412 characters of rulebook, orchestrating sub-agents to
produce cards that look like 1,737 characters of examples — machinery fifty times the size of the
thing it was reproducing.

One day of debugging turned up nine bugs, every one in the plumbing and none in the model's ability
to write a flashcard: a provenance check that parked honest cards before the reviewer could see
them, a scope flag that silently defaulted to "everything", a step documented after the step that
needed it, a retry limit at more than double the documented policy, a sub-process that died with an
empty error whenever it ran detached, and — the one that explains the rest — **the six example
cards sitting at 97% of the way into a 57,000-character prompt**, under an opening line telling the
agent to compare each card against the reference cards *below*.

An independent pass over the rulebook kept 34 instructions out of roughly 140. The rest was
history, post-mortems, rules about not writing rules, and descriptions of scripts that no longer
exist.

The deepest gap wasn't in the 140 either. Every one of them was a *prohibition* — not one described
what a normal card looks like. Nothing said a card has a bold subject and an italic answer, or that
most cards carry two clozes. That is why an agent could break no rule and still be wrong, and it is
why the skill now opens with the measured shape of a card before it lists a single constraint.

## What's still here

| | |
|---|---|
| [`.claude/skills/anki-cards/SKILL.md`](.claude/skills/anki-cards/SKILL.md) | the whole thing — style, examples, procedure |
| `classes/ISF/reference_media/` | the image `ref-06` cites |
| `classes/ISF/<Exam>/<Subject>/<Week>/` | your course material and built decks (gitignored) |
| [`requirements.txt`](requirements.txt) | Anki, AnkiConnect, and the tools that turn slides and recordings into text |
| `recaps/` | session history |
