# Markup & Visual Cues — the color system (standalone, load-bearing)

**The color of every phrase encodes its ROLE, so a card is readable at a glance.** Apply this
**while authoring**, never as an afterthought. These rules are *measured from* the AnKing
Neurogenetics deck (368 cards), not invented.

### The canonical card — copy this shape
```
The {{c1::<b>subject</b>}}  [plain connecting words]  {{c2::<i>answer</i>}}
```
**ONE bold subject + ONE italic answer + plain scaffold. Two clozes.** That's the overwhelming
majority of cards. Measured: `<b>` in 98%, `<i>` in 98% (usually exactly **one** of each), `<u>`
in only 42% (usually **zero or one**). Real cards:
- `The {{c1::<b>Pineal gland</b>}} secretes {{c2::<i>melatonin</i>::what?}}`
- `The {{c1::<b>brain stem</b>::brain part}} controls {{c2::<i>automatic behaviors necessary for survival (heart rate, breathing)</i>::what functions?}}`

Note what stays **plain**: "secretes", "controls", "is the" — the connective scaffold is never
colored. And the answer is **one italic span**, even when long — never chopped into several
colored blanks (that's the "italics all over" defect).

---

## The four roles → four colors

| Wrap in | Renders | ROLE — use it for |
|---|---|---|
| `<b>…</b>` | **mauve** `#C695C6` | **SUBJECT** — the main named term the card is *about* (the organelle, instrument, process, disease). |
| `<u>…</u>` | **teal** `#5EB3B3` | **FACET** — the specific aspect/qualifier that *scopes* the question ("which part of the subject", "under what condition"). **The EXCEPTION, not the rule** — only 42% of cards use it, most use none. Skip it unless a phrase genuinely scopes; never add teal just to have a third color. |
| `<i>…</i>` | **red** `IndianRed` | **ANSWER** — the description / value / consequence — *what is true about the subject*. |
| *(none)* | **green** (base cloze) | a cloze with no role markup renders plain green. Fine for a bare term, but prefer marking the role. |

Non-cloze context text stays the default body color — but **every phrase that carries a
role should be wrapped**, whether or not it's inside a cloze.

---

## Decision guide — for each phrase, ask:

1. **Is this the thing the card is ABOUT?** → `<b>` (subject, mauve). Usually leads the card and is `c1`.
2. **Does this SCOPE the question** — narrow it to a specific part/aspect/condition of the subject? → `<u>` (facet, teal).
3. **Is this the ANSWER** — the value, description, function, or consequence being recalled? → `<i>` (answer, red).
4. **Is it none of these** (a connective, an article, filler)? → leave it plain.

A well-built card often shows all three: **`<b>`subject** → **`<u>`facet** → **`<i>`answer**.

---

## Rules

- **Wrap the content INSIDE the cloze braces:** `{{c1::<b>anaphase</b>::which phase?}}`, not
  `<b>{{c1::anaphase::which phase?}}</b>`. This keeps a term colored even on sibling cards where
  it's an inactive cloze.
- **Every role-bearing phrase gets its color** — including ones that are NOT clozed (a bold
  subject sitting as context on a list card is still `<b>`).
- **Multi-part answer → numbered list**, each item on its own line, ALL items sharing ONE cloze
  number, each wrapped `<i>`. Subject stays `<b>` context (not clozed on list cards):
  `The <b>plasma membrane</b> has:<br>1. {{c1::<i>phospholipids</i>}}<br>2. {{c1::<i>cholesterol</i>}}<br>3. {{c1::<i>proteins</i>}}`
- **Balance your tags** — every `<b>`/`<i>`/`<u>` needs its close tag (the linter enforces this).

---

## Real measured examples (copy these shapes)

**The default — 2 clozes, one bold + one italic, plain scaffold:**
- `The {{c1::<b>Pineal gland</b>}} secretes {{c2::<i>melatonin</i>::what?}}`
- `The {{c1::<b>thalamus</b>}} {{c2::<i>relays and processes sensory information</i>::does what?}}`

**Three clozes + underline — the RARE case (~5%), only when a phrase genuinely scopes:**
- `{{c1::<b>DSCAM</b>}} is {{c2::<u>an IG cell-adhesion protein</u>::what type?}} indicated in {{c3::<i>Down syndrome</i>::which disease?}}`
- **TRANSFORMATION / reaction cards are a natural 3-role case** — test substrate + PROCESS + product, the process (a genuine facet) underlined:
  `A {{c1::<b>substrate</b>}} undergoes {{c3::<u>process</u>::what process?}} to become {{c2::<i>product</i>::what product?}}`
  e.g. `An {{c1::<b>alcohol</b>}} undergoes {{c3::<u>dehydration</u>::what process?}} to become {{c2::<i>an alkene</i>}}` — bold substrate, teal process, red product. (The three blanks aren't mutually-inferable, so it's a legit 3-cloze card, not self-answering.)
  — subject (bold) + facet "what type" (teal) + answer "which disease" (red). Don't force this shape; most cards don't have a facet.

**Memorized list — all items share ONE cloze number, recalled together:**
- `The {{c2::<b>diencephalon</b>::which brain part?}} contains:<br><br>1. {{c1::<i>Pineal gland</i>}}<br>2. {{c1::<i>Thalamus</i>}}<br>3. {{c1::<i>Hypothalamus</i>}}`
  — the three items are ALL `c1`, so one card blanks the whole set (you produce all three; the numbers say how many). The subject *diencephalon* is a separate cloze (`c2`) tested on its own sibling card. Each item is `<i>` (answer); the subject stays `<b>`.

## The eosin card, fixed to the canonical shape

The eosin card kept failing because it crammed one concept into a 3-cloze card with two italic
answers and mutually-inferable blanks (eosin ⟺ acidic ⟺ acidophilic ⟺ pink — four names for one
fact, so every blank gives the others away):

❌ `{{c1::<b>Eosin</b>}} is the {{c2::<i>acidic</i>}} H&E dye; it stains <u>cytoplasm and collagen</u> {{c3::<i>pink</i>}} — such structures are <u>acidophilic</u>`
  — 3 clozes, two italic answers ("italics all over"), underline forced, and c2's answer *acidic* is given away by *acidophilic* sitting right there.

✅ Split into **two canonical cards** — each `The <b>subject</b> [plain] <i>answer</i>`, one bold + one italic, 2 clozes:
  - `{{c1::<b>Eosin</b>::which dye?}} is the {{c2::<i>acidic (acidophilic) H&E dye</i>::which class?}}`
  - `{{c1::<b>Eosin</b>}} stains {{c2::<i>cytoplasm and collagen pink</i>::stains what?}}`
  — the answer is ONE italic span per card; no forced teal; the co-implied synonyms are folded into
  the single answer instead of being separate give-away blanks. This is the shape the real deck uses.

---

## Common mistakes (the linter can flag some; role choice is judgment)

- **Leaving role-bearing phrases plain** — the most common miss (the eosin card). If a phrase is
  a subject, facet, or answer, color it.
- **Demoting a key fact to teal "context" instead of clozing it as a red answer.** The facet (teal)
  role is ONLY for a phrase that genuinely *scopes* the question (which part / which condition) —
  never a dumping ground to "use the color." A key property or fact ("eosin is *acidic*"; "such
  structures are *acidophilic*") is an ANSWER (red) that must be **clozed and tested**, not shown as
  teal context that gives it away. **Do NOT force all three colors** — many good cards are just
  subject (mauve) + answer(s) (red), no facet at all. If you're making something teal just to have
  teal, it's almost certainly a red answer you forgot to cloze.
- **Wrong role** — coloring the answer `<b>` (mauve) instead of `<i>` (red), or the subject `<i>`.
- **Markup outside the braces** — `<i>{{c1::x}}</i>` loses the color on sibling cards.
- **Compressing grammar to fit clozes** — never break the sentence to save words; a card must
  read as coherent English.
