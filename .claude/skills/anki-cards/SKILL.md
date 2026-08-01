---
name: anki-cards
description: Build Anki cloze flashcards from course material (slides, lecture transcript, textbook summary) for the Bastyr ISF study decks, or fix cards already in Anki. Use whenever generating a deck, adding cards for a lecture, or repairing existing cards.
---

# What a card is

A card makes the student **produce a key term from memory, inside a complete, true sentence.**
That word is the blank. Everything below serves that.

Three roles, marked with HTML:

| | | |
|---|---|---|
| `<b>` | **subject** — what the sentence is about | on every card except an image card |
| `<u>` | **facet** — the *aspect* being asked about (a role, direction, timing, pH) | when the sentence names one, ~half of cards |
| `<i>` | **answer** — the value being recalled | on **every** card |

**Every card has an `<i>` answer, and — unless it is an image card — a `<b>` subject.**
Most cards have **two clozes** — meaning two cloze *numbers*; ref-05's five spans all share `c2`,
so that is one. One is common and fine, three is the ceiling, never four. **One `<b>` per card,
never two.** Left to right the roles run **`<b>` → `<u>` → `<i>`**, and the card ends on its
answer — except a recognition card, which closes on a few unstyled words (ref-06).

*(Measured over 321 shipped cards: `<i>` 100%, `<b>` 98.8%, `<u>` 46%; two cloze numbers 69%,
one 24%, three 7%, zero never, four never. The 4 cards without a `<b>` are not image cards — they
are defects that shipped because no rule said a prose card needs a subject.)*

# The six cards that define the style

These are the whole style guide. Where a written rule below and these cards disagree, **the cards
win.** When you write a card, find the one below with the same shape and put them side by side.

```
ref-01  {{c1::<b>Osteoid</b>::which material?}} is {{c2::<i>unmineralized bone matrix</i>::what is it?}}

ref-02  {{c1::<b>Osteoclasts</b>::which bone cells?}} <u>function</u> to {{c2::<i>resorb bone matrix</i>::do what?}}

ref-03  {{c1::<b>Calcitonin</b>::which hormone?}} acts on bone to {{c2::<u>lower</u>::raise or lower?}} {{c3::<i>blood calcium levels</i>::which levels?}}

ref-04  <b>Connective tissue</b> is <u>classified</u> into {{c1::<i>embryonic, proper, and specialized types</i>::which three classes?}}

ref-05  The {{c1::<b>epiphyseal growth</b>::which structure?}} plate has five <u>zones</u>:<br><br>1. {{c2::<i>resting cartilage</i>::which five zones?}}<br>2. {{c2::<i>proliferating cartilage</i>}}<br>3. {{c2::<i>hypertrophic cartilage</i>}}<br>4. {{c2::<i>calcified cartilage</i>}}<br>5. {{c2::<i>ossification</i>}}

ref-06  {{c1::<img src="ref-osteon.jpg">}}<br><br>This is {{c2::<i>compact bone</i>::which tissue?}} that we can see
```

Read off them: **ref-01** subject + answer, the workhorse. **ref-02** a *visible* facet.
**ref-03** an either/or choice wears `<u>`, the value wears `<i>`. **ref-04** the subject is the
frame, so it stays visible. **ref-05** a list — numbers **outside** the braces and unstyled, one
item per line, every item on **one** cloze number, hint on item 1 only, and "plate" visible and
*not* bolded. **ref-06** a recognition card — the picture is a cloze with **no hint**, there is
**no `<b>` at all**, and it closes on four unstyled words.

# Building a deck

1. **The user states the scope** — the folder, and which files to card. Never infer it from what
   happens to be in the directory. The material in that folder is the only input; never open Anki
   to decide what to card.
2. **Read every named source end to end.**
3. **Draft cards one source at a time**, not one pass over all of them. Quality collapses inside a
   single long response.
4. **Coverage pass — this is the step that matters most.** Read each source back against the whole
   deck: what was taught that has no card? Weight by what the lecturer *stressed* — "I need you to
   know", spelling a term aloud, repeating himself, quizzing the class, minutes on one slide — not
   by word count. Draft those. Repeat until a source comes back with nothing. *Skipping this once
   produced a deck that carded the textbook thoroughly and skimmed the lecture, missing two-thirds
   of what the lecturer emphasised.*
5. **Review every card** against the same-shape card above, open side by side — not from memory.
6. **Write the deck to a file, show the user, then insert** with `anki_add_notes` once they say go.

Note type `Custom Cloze`; fields `Text` (the card), `Extra` (slide image + `Source:` quote),
`Source` (e.g. "Slide 12"). Deck by lecture — `ISF::Test N::<Subject>::<Lecture>` — and tag by
topic. **The folder says `Exam`, the deck says `Test`**; check `anki_find_notes` for the existing
deck before creating a sibling. Tag every card `isf::<subject>::<topic>`, `week::NN`, `test::N`,
`slide::<slug>-NN` — the slug is required, since two slide decks in one folder both number from 1.

# Shape

- **Write down the question the card asks. If the subject is that question's answer, cloze it; if
  it only scopes the sentence, leave it visible.** "Which hormone raises blood calcium?" makes PTH
  the answer — cloze it. "Amino acids have (S) configuration" asks nothing about amino acids —
  leave it visible. Never apply a blanket rule either way; both blankets have shipped as defects.
- Cloze every term the student must produce, **including the condition a fact hinges on** ("at
  physiological pH"). Never leave a testable term as visible prose.
- **One fact per card.** Split a chain (A does B, which does C) into linked cards rather than
  adding a second `<i>` answer. ref-05's five items share one cloze number, so they are one answer.
- **`<u>` is what the question is ABOUT; `<i>` is what the student produces.** Not a parts-of-speech
  test — `<u>function</u>` and `<u>zones</u>` are both nouns and both correct. Ask which one the
  card is asking you to recall. If the underlined span is a second thing being recalled, it is an
  answer: cloze it and demote the other, or split the card. *Eight cards shipped with the second
  answer hidden in a `<u>`, because the author had two answers and nowhere to put the second.*
- Cloze the facet only when it is a **value to produce**: ref-03 clozes `lower` because
  *raise or lower* is the recall; ref-02 leaves `function` visible because it only names the aspect.
- **Cloze the whole answer.** No fragment clozes with the rest trailing as prose.
- Cloze the distinguishing word and leave a generic head noun visible **and unstyled** —
  ref-05's "plate". Never bold it too.
- Nothing unstyled goes inside the braces; scoping words and articles stay outside. (An `<img>` is
  the one thing that goes in a cloze wearing no role tag — ref-06.)
- Cut a parenthetical you are not testing rather than leaving it dangling.

# Hints

- **Hint every cloze, except an image cloze and list items that share a number** (they inherit the
  hint from item 1). Those two carve-outs are the whole exception list — stating the rule as
  "no exceptions" is what once made a reader put a hint on a picture.
- Hints are **questions ending in `?`**, one to three words, no commas, and must read as natural
  English substituted into the blank: `{{c1::<i>osteocytes</i>::what cells?}}` reads
  *"Lacunae contain [what cells?]"*.
- Bare `what?` / `which?` are house style. So are two-option hints — `raise or lower?`,
  `regular or irregular?`. **A two-option hint is not a leak**; it makes recall fast. Do not flag it.
- **Hide each cloze in turn.** Nothing visible — including the *sibling answers* — may give it
  away. `{{c2::<i>phosphates</i>}} … a high concentration of phosphate ions` is self-answering.
- Every answer must be recallable **as a unit**. A clause with its own subject and verb is a
  sentence, not an answer.

# What earns a card

- The bar is not "is it true" but **"did the teacher signal this as need-to-know."** Slides are the
  signal; the transcript is the emphasis.
- One card per stressed slide, occasionally two. **Zero for a slide is fine; zero for a taught
  topic is a failure.** When unsure, card it.
- Precedence: **objectives** (the coverage contract) ▸ **slides** (the anchor) ▸ **transcript**
  (emphasis) ▸ **textbook** (precision).
- An objective-backed fact always gets a card, even if the lecture deferred it.
- If the instructor says a value will be given, or says not to memorise something, **do not card it.**
- Where sources contradict on fact, card what the slides and textbook agree on and raise the
  conflict. Never ship both sides.
- Two cards teaching one fact are one card. **A shared sentence frame is not a shared fact** —
  parallel cards on contrasting terms are correct and wanted.
- **Scope by session, not by topic.** Card everything taught in the recording, including material
  carrying over from last week. Slides the lecture never reached belong to the next deck.

# Fidelity

- Assert only what the source states. No added qualifier, no inference, no outside knowledge.
- **Cite or omit, never coin.** Established terminology only; prefer the source's own words.
- `Extra` carries the slide image plus a **verbatim** `Source:` quote. A card with no resolvable
  source does not ship.
- Quote verbatim. Never tidy a quote, and **never splice two separate cues into one sentence.**
  Eliding rambling with `…` is fine as long as each fragment is word-for-word and in order.
- For a spoken fact, quote the **transcript** and label it as such, even if you also show the slide.
  Never cite a slide that does not state the fact.
- Transcripts mangle technical terms. Quote the garble with the correction in `[brackets]`, put the
  correct term on the card face, and cite the slide instead when the correction would be a guess.
- A paraphrase is not a quote: the lecturer's "in your 20s" written as "in your twenties" is altered.

# Reviewing

- **The six cards define an acceptable card.** If a construction appears in them, it is not a
  finding. Say nothing.
- Grade each card beside the same-shape card above, pulled up — not from memory.
- **A review reports; fixing is a separate pass that gets reviewed again.** Never approve a rewrite
  in the pass that flagged it.
- **A flag sends you back to the source, not to the markup.** If you are editing markup and the
  fact hasn't changed, stop.
- **Two fixing attempts, then stop** and put the original and both attempts in front of the user.
  Escalate at once if the fact is disputed, or if cutting the card leaves its topic uncovered.
- Nothing is dropped silently. A card you cut or hold stays in the file with the reason.
- Re-read a live card's current text from Anki before editing it.
