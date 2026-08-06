---
name: anki-cards
description: Step 3 of 3. Write Anki cloze cards from a card plan and insert them into the Bastyr ISF study decks. Use after anki-organize, or on its own when repairing cards already in Anki.
---

# What a card is

A card makes the student **produce a key term from memory, inside a complete, true sentence.**
That term is the blank. Everything below serves that.

Check the sentence against that line before checking it against anything else. A card can parse,
carry every tag correctly, satisfy every rule below, and still fail it — that is the *common*
failure, not a rare one. Ask: is this sentence true standing alone, and is the blank a term worth
producing?

# The six cards that define the style

These are the whole style guide. Where a written rule below and these cards disagree, **the cards
win.** Put your draft beside the one with the same shape — pulled up, not from memory.

They are canonical, so keep them correct: if one of them is wrong, fix it here rather than working
around it. *ref-05 once read "'plate' visible and not bolded", which is the opposite of the rule
below, and 24 cards were written to match it before anyone compared the two.* And whenever you
build a check of any kind, **run these six through it first** — they are the regression test. A
check that fails ref-06 has not understood recognition cards; a check that passes a card these six
would reject is not checking the right thing.

```
ref-01  {{c1::<b>Osteoid</b>::which material?}} is {{c2::<i>unmineralized bone matrix</i>::what is it?}}

ref-02  {{c1::<b>Osteoclasts</b>::which bone cells?}} <u>function</u> to {{c2::<i>resorb bone matrix</i>::do what?}}

ref-03  {{c1::<b>Calcitonin</b>::which hormone?}} acts on bone to {{c2::<u>lower</u>::raise or lower?}} {{c3::<i>blood calcium levels</i>::which levels?}}

ref-04  <b>Connective tissue</b> is <u>classified</u> into {{c1::<i>embryonic, proper, and specialized types</i>::which three classes?}}

ref-05  The {{c1::<b>epiphyseal growth</b>::which?}} <b>plate</b> has five <u>zones</u>:<br><br>1. {{c2::<i>resting cartilage</i>::which five zones?}}<br>2. {{c2::<i>proliferating cartilage</i>}}<br>3. {{c2::<i>hypertrophic cartilage</i>}}<br>4. {{c2::<i>calcified cartilage</i>}}<br>5. {{c2::<i>ossification</i>}}

ref-06  {{c1::<img src="ref-osteon.jpg">}}<br><br>This is {{c2::<i>compact bone</i>::which tissue?}} that we can see
```

**ref-01** subject + answer, the workhorse. **ref-02** a *visible* facet. **ref-03** an either/or
choice wears `<u>`, the value wears `<i>`. **ref-04** the subject is the frame, so it stays visible.
**ref-05** a list — numbers **outside** the braces and unstyled, one item per line, every item on
**one** cloze number, and hint on item 1 only. The whole subject — "epiphyseal growth plate" —
is bolded &mdash; in two `<b>` runs, because a cloze boundary cuts through it; only "epiphyseal
growth" is clozed, so "plate" stays visible to make the hint read. **ref-06** a
recognition card — the picture is a cloze with **no hint**, there is **no `<b>` at all**, and it
closes on four unstyled words.

**And read what they have in common:** every subject is a **specific named entity** — Osteoid,
Osteoclasts, Calcitonin, the epiphyseal growth plate — and each card states **one property of it**.
Not one has a topic heading in the subject slot. Reading these six for their markup and not for
that is how a deck ends up with the same subject on three-quarters of its cards.

# From plan to card

`ENTITY → <b>` · `ASPECT → <u>` · `VALUE → <i>`

- `<i>` on every card; `<b>` on every card but an image card. **One subject, never two** —
  which is not the same as one `<b>` tag; see the nesting rule below.
- Left to right the roles run **`<b>` → `<u>` → `<i>`**, and the card **ends on its answer** —
  except a recognition card, which closes on a few unstyled words (ref-06).
- **The subject opens the sentence**, behind at most an article. A clause in front of it means
  either a facet standing in the wrong place — "In cross section, `<b>`skeletal muscle`</b>` fibers
  appear polygonal" wants to be "`<b>`Skeletal muscle`</b>` fibers in `<u>`cross section`</u>`
  appear polygonal" — or filler to cut.
- **The whole subject is bolded; only the key identifier is clozed.** That is the rule about
  *what*. The rule about *how* is separate, and getting it wrong silently breaks the card:

  **A role tag must sit directly on the text it styles — never wrap a cloze.** Anki renders a
  revealed cloze as its own `<span class="cloze">`, and that span sets colour on itself, so a
  colour merely *inherited* from an enclosing `<b>` is overridden and the role is lost on screen.
  A subject that a cloze boundary cuts through therefore takes **two `<b>` runs**, one inside the
  braces and one outside. It is still one subject.

  ```
  The {{c1::<b>A</b>::which?}} <b>band</b> is {{c2::<i>dark</i>::dark or light?}}
  {{c1::<b>Type IIb</b>::which?}} <b>muscle fibers</b> have the {{c2::<u>fewest</u>::most or fewest?}} {{c3::<i>mitochondria</i>::which organelle?}}
  {{c1::<b>sarcomere</b>::which unit?}} is {{c2::<i>the functional unit of contraction</i>::what is it?}}
  ```

  *Written as `<b>{{c1::A::which?}} band</b>` it reads correctly in the source and renders wrong:
  148 of 172 cards shipped with the subject showing in the cloze colour instead of the subject
  colour. Nothing in the markup looks amiss — only the rendered card shows it.*

  "muscle fibers" and "band" are part of the subject's name, so they are **inside the bold**; they
  are not what distinguishes it, so they are **outside the cloze**. Where the subject is a single
  term the bold and the cloze coincide. *Getting these two nested the wrong way round — cloze
  outside, bold inside — is what produced `<b>A band</b>` blanked whole and `{{Type IIb}} muscle
  fibers` with the name broken in half.*
- Nothing unstyled goes inside the braces; scoping words and articles stay outside. (An `<img>` is
  the one thing in a cloze wearing no role tag — ref-06.)
- **No possessives.** With the right entity there is nothing to possess, only to describe, so an
  apostrophe-s (or a "whose") means step 2 handed you the wrong entity — go back rather than patch.
- Assert only what the source states. No added qualifier, no inference, no invented comparison.

# Which spans get clozed

- **A card asks two questions, forward and backward.** Cloze the subject as well when the reverse
  question has a single right answer *that discriminates*; leave it visible when many terms answer
  it equally well (ref-04). Never apply a blanket rule either way — both blankets have shipped as
  defects.
- **Cloze the whole value**, never a fragment with the explanation left as prose. *"…because the
  thin and thick filaments never form {{sarcomeres}}" is a 1-word answer with 11 words of
  explanation visible; the six run 3-word answers with 0–3 words visible.*
- **The hint must be the question you meant to ask.** If you are writing a hint to fit a blank you
  already chose, you clozed by word-type instead of by answer — technical nouns *look* like answers
  and the eye lands on them.
- Cloze the facet only when it is a **value to produce**: ref-03 clozes `lower` because *raise or
  lower* is the recall; ref-02 leaves `function` visible because it only names the aspect. An
  either/or is ref-03 **only when a separate value survives it** — otherwise mark the aspect noun
  `<u>` and let the either/or be the `<i>` answer.
- One to three cloze numbers. Never four.

# Hints

- **Hint every cloze, except an image cloze and list items that share a number** (they inherit
  item 1's). Those two carve-outs are the whole exception list.
- Questions ending in `?`, one to three words, no commas, reading as natural English substituted
  into the blank.
- **The hint supplies exactly what the visible sentence does not, and fluency is the test.** Read
  the sentence with the blank in place; if it does not read as English, the hint is wrong.
  `The {{c1::<b>A</b>::which band?}} <b>band</b>` gives *"the [which band?] band is dark"* — the
  noun is said twice. Because "band" is already visible, the hint is simply `which?`.
- Where nothing visible names the category, the hint must: `{{c1::<b>sarcolemma</b>::which membrane?}}`, not a bare `what?`. **A hint that could sit in front of any answer is not a hint** —
  `what else?` is the clearest failure. Otherwise a hint names the category (`which organelle?`),
  prompts an action (`do what?`), offers an either/or (`raise or lower?`), asks for a definition
  (`what is it?`), or asks a cause (`why?`, whose answer is a whole clause). A two-option hint is
  *not* a leak; it makes recall fast.
- **Hide each cloze in turn.** Nothing visible — including the sibling answers — may give it away.

# Working

**Draft 10–15 cards per pass and re-read the six at the start of every pass.** Not from memory:
pull them up. Quality does not decay gently inside a long response, it collapses, because after the
first pass your nearest exemplar stops being ref-01 and becomes **your own previous card** — so
errors inherit instead of scattering. *One 228-card sitting used the facet role in half the cards in
its first block of 20 and in none at all by the seventh, with the six in context the whole time.*

**There is no target ratio.** Judge every card against the six and the rules. If a whole block
skips a role entirely, go and look at those cards — the finding is in the cards, never in a
percentage.

A review reports; fixing is a separate pass that gets reviewed again. A flag sends you back to the
source, not to the markup.

# Anki

Note type `Custom Cloze`; fields `Text` (the card), `Extra` (slide image + verbatim `Source:`
quote), `Source` (e.g. "Slide 12"). Deck by lecture, `ISF::Test N::<Subject>::<Lecture>` —
**the folder says `Exam`, the deck says `Test`**; check `anki_find_notes` for the existing deck
before creating a sibling. Tag every card `isf::<subject>::<topic>`, `week::NN`, `test::N`,
`slide::<slug>-NN` — the slug is required, since two slide decks in one folder both number from 1.
Slide images go into `collection.media` as `isf-<slug>-slide-NN.jpg`.

Write the deck to a file, show the user, then insert with `anki_add_notes` once they say go.
Re-read a live card's current text from Anki before editing it.
