---
name: anki-cards
description: Generate Anki flashcards from course study materials (textbook chapters, slide decks, lecture notes) for the Bastyr ISF study pipeline — cloze-first JSONL, then validate and build to .apkg. Use whenever turning course material into review cards, adding a new week/chapter/subject, or rebuilding a deck.
---

# Anki card generation (ISF pipeline)

## Orientation — read this first

**What this is:** the pipeline that turns course materials into Anki decks. The pieces:
- **This skill (`SKILL.md`)** — the card-making METHOD (what/how); auto-triggers on card requests.
- **`MARKUP.md`** — the visual-cue / color spec, **measured** from the AnKing Neurogenetics deck.
- **`build-week` workflow** (`.claude/workflows/build-week.js`, run via `/build-week`) — the
  orchestrator: Prep → Generate → Review (grounding + style) → Build. Prefer it for a full subject.
- **Tools** (`classes/ISF/`): `extract_sources.py`, `slice_textbook.py`, `validate_cards.py`
  (well-formedness), **`lint_cards.py` + the `anki-style` MCP (the STYLE gate)**, `make_preview.py`,
  `build_apkg.py` (export), `sync_anki.py` (live update, keyed by `key::` tag), `dump_anki.py`
  (reverse pull from Anki).
- **Memory** — the decisions / why (auto-loaded each session).

**Principles that matter (hard-won — do not re-violate):**
1. **MEASURE, don't theorize.** The style guide is *derived from the real Neurogenetics deck*. When
   unsure how a card should look, go measure the deck (counts, markup, structure) — don't invent rules.
2. **Slide-anchored, not exhaustive.** Walk the lecture DECK, ~1 note per slide; NEVER mine the
   textbook for cards (textbook = precision only). Exhaustive textbook-mining ran 5× too dense.
3. **Canonical card** = `The {{c1::<b>subject</b>}} [plain] {{c2::<i>answer</i>}}` — one bold subject
   + one italic answer, **~2 clozes** (3 rare, 4+ never); underline is the exception; hints selective.
4. **Pull before you audit.** If the live Anki deck may be ahead of the JSONL (hand/MCP edits), run
   `dump_anki.py` FIRST — otherwise a sync clobbers those edits.
5. **The linter is a HARD gate.** `sync_anki.py` and `build_apkg.py` refuse on lint errors
   (`--no-lint` overrides). Cards cannot reach Anki dirty. Run `lint_cards.py` (or `anki_style_lint`) as you go.
6. **Regenerate legacy, don't patch card-by-card.** Fix the spec, then regenerate the file.
7. **Style ≠ content — the card must MAKE SENSE.** A canonical-shaped card can still be nonsense
   ("An amine nitrogen ionizes to a positive charge when it gains a fourth bond" — garbled). Every
   card must test a *real concept* in *clear, natural English* with a sensible subject/answer split.
   And a VISUAL/drawing task ("draw an amine ionized", "show all atoms") is NOT a cloze card — make
   it an image card or drop it. The linter checks shape, not sense; sense is on you.

---

Turn study materials into a high-yield Anki deck:

```
sources (PDF / pptx / notes)  →  reviewable JSONL cards  →  validate  →  review (accuracy)  →  build .apkg
```

Phase 1 is **card generation for review** — the crux. JSONL is the human-reviewable
hand-off; the .apkg is a mechanical build step on top of it.

**Core principle (read this first — it governs everything below): the pipeline is
SLIDE-ANCHORED and streamlined, not textbook-exhaustive.** Generation walks the lecture
**slide deck** slide by slide and makes **~1 note per slide (occasionally 2)** for the point(s)
the professor stresses in the **transcript**, checked against the **objectives**. The
**textbook is a precision reference only** — consulted to pin an exact number/spelling on a
card that already exists, never mined for new cards. Volume falls out of the deck (a 40-slide
lecture → ~40–50 notes), landing at AnKing-Neurogenetics density. Earlier weeks were built by
mining the textbook exhaustively and ran ~5× too dense; this flow replaces that.

The course "spine" is **`classes/ISF/course-map.yaml`** (syllabus → weeks, topics,
readings, assessments, per-topic objectives). Read it first to know what a week
covers, which exam it feeds, and what the learning objectives are — cards should
serve those objectives.

---

## Card-style contract (non-negotiable — this is the calibrated house style)

- **Every text card is a cloze — a rule, not a default. There is NO basic Q&A card
  for text facts.** A "why / how / compare" fact is NOT an exception: express it as a
  **two-sided cloze** where BOTH the subject/term AND its consequence are clozed, so
  each fact is actively *retrieved* from both directions — not a whole answer
  recognized once. E.g. don't write a Q "difference between apoptosis and necrosis?";
  write `In {{c1::<b>apoptosis</b>}} cells are cleared with {{c2::<i>no inflammation</i>}};
  in {{c3::<b>necrosis</b>}} they lyse and cause {{c4::<i>local inflammation</i>}}` The
  ONLY non-cloze card type is the **image** card (visual recognition). If you're
  tempted to write `type: basic` for a text fact, that's the signal to restructure it
  as a two-sided cloze instead.
- **Open with the card's SUBJECT — as the first cloze. Never open with circumstantial
  scene-setting that pushes the real subject and answer to the end.** The subject is the
  specific *thing the card is about* (the instrument, structure, process, term). It must be
  at the front AND be a cloze, so retrieval starts immediately. A card that opens with a
  circumstance — "For routine light microscopy,…", "Prior to oxidation,…", "In the process
  of…" — and only reveals its key term at the very end is a DEFECT: the whole sentence is a
  giveaway and you supply one buried word. Restructure to lead with the subject.
  - ❌ `For routine light microscopy, tissue is embedded in {{c2::paraffin}} and then cut
    into 3–10 µm sections with a {{c1::microtome}}` — opens with circumstance, buries both terms.
  - ✅ `{{c1::<b>Microtome</b>::which instrument?}} cuts {{c2::<i>paraffin</i>::which medium?}}-embedded
    tissue into {{c3::<i>3–10 µm</i>::what thickness?}} sections for routine light microscopy` — subject leads.
  - ❌ `Rapid sectioning of unfixed, frozen tissue uses a {{c2::cryostat}}` (process is the giveaway).
  - ✅ `{{c2::<b>Cryostat</b>::which instrument?}} allows {{c3::<i>rapid sectioning</i>::of what?}} of
    unfixed, frozen tissue as freezing does not {{c1::<i>inactivate enzymes</i>::do what?}}`.
  - **Litmus test:** if the FIRST word of the card is not (or does not immediately introduce)
    a cloze on the key term, and the answer is a single term the exposed sentence basically
    forces, it's buried — restructure. (A short *scoping* phrase that names the topic —
    "In a {{c1::case-control study}}, …" — is fine, because the subject IS the opening.)
- **Definition→term cards MUST be two-sided — never leave the definition exposed as a
  permanent giveaway.** A single-blank `The <definition…> is called {{c1::term}}` card is a
  DEFECT: it only ever tests one direction (given the definition, recall the name) and the
  definition itself is never retrieved. Restructure it subject-first with the term leading as
  one cloze AND its definition as a *separate* cloze, so the fact splits into two cards that
  test both directions. Defect: `The diffusion of water across a selectively permeable
  membrane is called {{c1::osmosis}}`. Fixed: `{{c1::<b>Osmosis</b>::which process?}} is the
  {{c2::<i>diffusion of water across a selectively permeable membrane</i>::defined as?}}`
  (c1 card = recall the term; c2 card = recall the definition). This is the same two-sided
  principle as the top bullet, applied to the most common single-blank offender. (A term
  with NO definition to recall — a bare label — can stay one-sided.)
- **A blank must span the COMPLETE answer concept — never clip it and spill the remainder
  onto the front.** If a trailing clause is part of the answer, include it *inside* the
  cloze; don't blank half and leave the rest showing. Defect:
  `{{c2::organic solvent such as xylene}} that is miscible with the paraffin embedding medium`
  (the miscibility clause IS the point of xylene, yet it's exposed). Fixed:
  `{{c2::an organic solvent such as xylene that is miscible with the paraffin embedding medium::what?}}`
  — one complete concept, one deletion. This is the complement of the "never blank incidental
  words" rule below: don't blank a *fragment*, but when something genuinely *is* the answer,
  blank ALL of it.
- **Cloze the verb phrase, not just its noun.** The fact is usually the *action*, not the
  bare object. `does not inactivate {{c1::enzymes}}` → `does not {{c1::inactivate enzymes}}`
  (freezing-doesn't-inactivate is the fact; "enzymes" alone leaves the verb as a giveaway).
- **No terminal period.** Don't end card sentences with a full stop.
- **Slide-anchored volume — the DECK sets the count, never "exhaustiveness."** The unit of
  generation is the **slide**, not the textbook chapter. Walk the slide deck; make **~1 note
  per slide (occasionally 2)** capturing the key point(s) the professor actually stresses.
  Target density = the AnKing Neurogenetics deck (~20–40 notes per lecture, high-yield only).
  A 40-slide deck → ~40–50 notes. Do NOT mine the textbook for every fact — that produced
  ~5× too many cards (Wk1: 2,043 cards for one week vs Neurogenetics' 670 for a whole semester).
- **THE CANONICAL CARD (measured from the AnKing Neurogenetics deck — copy this shape):**
  `The {{c1::<b>subject</b>}} [plain verb/connector] {{c2::<i>answer</i>}}`. **One bold subject,
  one italic answer, plain connecting words, TWO clozes.** e.g. `The {{c1::<b>Pineal gland</b>}}
  secretes {{c2::<i>melatonin</i>::what?}}`. This is the default for the overwhelming majority of
  cards; deviate only with reason.
- **~2 clozes per card is the norm — NOT 3–4.** Measured Neurogenetics distribution: 1 cloze 29%,
  **2 clozes 64%**, 3 clozes 5%, **4+ never**. So: default to 1–2 clozes; use 3 only when a card
  genuinely has three tight facets; **never 4+**. If you want more blanks, you're cramming — make
  a second card. (A numbered LIST sharing ONE cloze number counts as a single cloze — a 5-item
  list under one `c1` is fine; it's one card.)
- **The answer is ONE italic span, not chopped into pieces.** The whole descriptive phrase is a
  single `{{cN::<i>…</i>}}` — `{{c2::<i>automatic behaviors necessary for survival (heart rate and
  breathing rate)</i>}}`, NOT three separate italic clozes. Multiple italic answer-blanks on one
  card is the "italics all over the place" defect. Usually exactly ONE bold and ONE italic per card.
- **Don't cloze mutually-inferable terms on one card, and don't leave the answer visible in the
  context.** Two failure modes of the same defect — SELF-ANSWERING cards: (a) two blanks give each
  other away (eosin ⟺ acidic ⟺ acidophilic ⟺ pink); (b) the visible non-cloze text DEFINES or lets a
  knowledgeable student DERIVE the clozed term. The literal kind: clozing {{c3::<u>hydration</u>}} while
  "(adds water)" sits right there. The inference kind (subtler, easy to miss — a repeated-word scan
  won't catch it): a dangling explanatory clause the reader can reason from — clozing "quaternary
  ammonium ion" while "its nitrogen has four carbon–nitrogen bonds" is visible (four C–N bonds ≡
  quaternary), or "permanent positive charge" sitting beside "ammonium" (ammonium ≡ a cation). When you
  cloze a term, scan the rest of the sentence and ask: *could a student who knows the material derive
  this blank from what stays visible?* If yes, remove/relocate that phrase (or don't cloze that term). Test discriminating facts on
  separate cards; keep co-implied synonyms/definitions as plain context only if they're NOT the blank.
- **ONE CONCEPT per card — consolidate *aspects*, but SPLIT distinct concepts.** Consolidating
  is only for facets of the SAME thing (a mitochondrion's outer membrane + inner membrane +
  cristae = one concept "mitochondrion structure" → one note). Two *distinct* concepts, each
  with its own full definition, must be SEPARATE cards — do not merge them into a contrast.
  Defect (two concepts, one card): `{{c1::Direct}} ICC uses {{c2::a single labeled antibody}}
  whereas {{c3::indirect}} ICC uses {{c4::an unlabeled primary + labeled secondary}}`. Fix →
  TWO cards, each one concept, each two-sided: `{{c1::<b>Direct</b>}} immunocytochemistry uses
  {{c2::<i>a single antibody made against the antigen, tagged directly</i>}}` · `{{c1::<b>Indirect</b>}}
  immunocytochemistry uses {{c2::<i>an unlabeled primary antibody plus a labeled secondary against it</i>}}`.
  The "up-to-4-cloze two-sided contrast" exception above is ONLY for a single short contrastive
  *axis* (apoptosis vs necrosis on the *inflammation* axis: `no inflammation` / `inflammation`) —
  NOT for pairing two full definitions. If each side would stand alone as its own card, split it.
- **High-yield, not exhaustive.** Card the load-bearing backbone the teacher emphasizes — the
  key term, its definition/function, the critical contrast — not every incidental number or
  sub-detail. Litmus for "does this earn a note?": *did the professor stress it (transcript),
  and/or is it on an objective?* If neither, skip it.
- **Keep board-style specifics on the cards you DO make.** Don't dumb down a note that earns
  its place: keep the real numbers (sizes, nm, counts, %), precise vocabulary, and
  clinically/board-relevant detail. (This governs *precision within a card*, not *how many
  cards* — selectivity decides the count, precision decides the wording.)
- **Multi-blank cloze is the consolidation tool.** Use c1/c2/c3 to test several facts from
  ONE slide in ONE note (each blank becomes its own review card). Number from c1. This is how
  you cover a slide's 2–3 facts without minting 2–3 separate notes.
- **One idea per blank.** Don't bury two distinct facts in a single deletion.
- **Blank only what's worth recalling — never incidental words.** Every deletion must be
  a fact you'd want on its own card; the rest of the sentence is *context*. Do NOT blank a
  peripheral word just to fill the sentence. A blank that renders as "…miscible with the
  ___ medium" (answer = an incidental modifier like "embedding") is a defect — leave it as
  context, or restructure so the blank lands on the concept's **key term or what it does**.
  So "cloze every testable fact" (below) means every FACT worth a card, **not every word**;
  the two rules are read together. This is about a *fragment* — an incidental modifier
  standing alone. It does NOT license clipping a real answer: when the trailing clause is
  part of the concept being tested, blank the whole unit (see "a blank must span the
  COMPLETE answer concept" above). Fragment → leave as context; complete answer → blank all of it.
- **Cloze every testable fact in the sentence — including key terms in the
  subject/premise slot.** Don't leave a term exposed just because it's the
  grammatical subject. E.g. "Formaldehyde and glutaraldehyde fix tissue by reacting
  with the amine group" has TWO facts: cloze the amine (`c1`) AND the two fixatives —
  as a shared cloze recalled together (`{{c2::Formaldehyde}}` … `{{c2::glutaraldehyde}}`).
- **Cloze the answer AND what it does.** For "term + definition/function/process"
  cards, don't cloze only the term — also cloze the description (two-way), so the
  card tests the content both ways, not just the name.
- **Markup = color (visual cues) — see the dedicated spec: [`MARKUP.md`](MARKUP.md).** This is
  load-bearing and its own standalone reference; do NOT treat it as an afterthought. In short:
  color encodes ROLE — **`<b>` subject** (mauve), **`<u>` facet being asked about** (teal),
  **`<i>` answer/value** (red), plain cloze = green. Wrap the content *inside* the cloze braces;
  color every role-bearing phrase (even unclozed ones); multi-part answers → numbered `<br>` list
  sharing one cloze. **Read `MARKUP.md` before authoring or reviewing** — a card that leaves its
  key phrases plain is a defect. (Colors are defined in `build_apkg.py` CSS.)
- **Hint SELECTIVELY, not every cloze** (measured: only ~1/3 of Neurogenetics clozes carry a
  hint). Add a `::hint` only when the front would otherwise be ambiguous about *what* is asked —
  **typically the answer/italic cloze**; a **bold subject that leads the sentence usually needs
  none** (the sentence already frames it). The hint is a short category cue that does NOT reveal
  the answer (`37%`→`what concentration?`). Numbered-list items stay unhinted. Make hints
  *pointed*, not generic — and don't spray them on every blank.
- **Style reference (markup, cloze structure, hints):**
  `classes/ISF/Week 1/Histology/cards/chapter-1.jsonl`.
  Match its cloze *structure and markup* — but NOT its density: the Wk1 files were built
  textbook-exhaustive and are ~5× too dense. For **density**, the reference is the AnKing
  Neurogenetics deck (~1 note/slide, ~20–40 notes/lecture), per "Slide-anchored volume" above.

---

## JSONL schema

One card per line. Three `type`s:

```json
{"type":"cloze","text":"The {{c1::<b>subject/term</b>}} {{c2::<i>does X / is the answer</i>}}","tags":["isf::histology::cytoplasm::er","week::01","src::junqueira-ch2"],"source":"Junqueira Ch.2 — The Cytoplasm"}
{"type":"cloze","text":"The <b>plasma membrane</b> consists of:<br>1. {{c1::<i>phospholipids</i>}}<br>2. {{c1::<i>cholesterol</i>}}<br>3. {{c1::<i>proteins</i>}}","tags":["isf::histology::cytoplasm::plasma-membrane","week::01","src::junqueira-ch2"],"source":"Junqueira Ch.2 — The Cytoplasm"}
{"type":"basic","front":"Why is X true?","back":"Because Y.","tags":["isf::histology::nucleus::nucleolus","week::01","src::junqueira-ch3"],"source":"Junqueira Ch.3 — The Nucleus"}
{"type":"image","front":"Identify the structure (C = its sacs).","image":"media/vis-rer-em.jpeg","back":"<b>Rough ER</b> — cisternae studded with ribosomes; basophilic.","tags":["isf::histology::cytoplasm::er","visual","week::01","src::slide-set-1"],"source":"Slide Set 1 (slide 36)"}
```

Required fields: `cloze`→`text`; `basic`→`front`,`back`; `image`→`front`,`image`,`back`.
Every card also carries `tags` (list) and `source` (string).
`image` path is relative to the cards dir (always `media/<file>`).
Optional on any card: **`extra`** — a supplementary note (mnemonic, clarification,
board pearl) shown behind a tap-to-reveal button on the answer side.

Note types are styled AnKing-style, self-contained in `build_apkg.py` (no add-ons):
centered, dark `#333B45` card, `Menlo` font; `<b>`→mauve, `<i>`→red, `<u>`→teal,
plain cloze→green; tap-to-reveal `Extra`. Edit its `CSS` to restyle.

---

## Tag scheme (hierarchical — builds a browsable tree in Anki)

Every card gets:
- **Topic path:** `isf::<subject>::<chapter-topic>::<subtopic>`
  e.g. `isf::histology::cytoplasm::mitochondria`, `isf::histology::nucleus::meiosis`
- **Week:** `week::01` … `week::08` (zero-padded)
- **Source:** `src::junqueira-ch2`, `src::slide-set-1`, `src::marks-ch1`
- Image/recognition cards also get the bare tag **`visual`** (so you can study
  image-only).
- **Flags:** `flag::beyond-scope` for correct-but-not-taught facts (see the review
  section) — lets the learner filter/suspend them in Anki.

Rules: **no spaces inside a tag** (Anki splits tags on spaces — the validator
enforces this). Keep the subject/topic vocabulary consistent with existing files
and with `course-map.yaml`.

---

## Workflow

1. **Read the spine + objectives.** Open `course-map.yaml` and the week's learning-objectives
   file. The objectives are the coverage checklist.
2. **Locate sources** in the week's folder (e.g. `Week 1/Histology/`): the **slide deck**
   (.pptx/PDF — the anchor), the **transcript** (the selector), objectives, and the textbook
   (precision only). Extract the deck's slides as text/images (a .pptx is a zip — see the
   visual section for the unzip recipe).
3. **Walk the deck slide by slide.** For each slide, read its content AND what the transcript
   says about it. Ask: *did the professor stress this slide's point?* If yes, it earns **~1
   note (occasionally 2)**. If the teacher skipped/waved past a slide, skip it. This walk —
   not the textbook — determines what gets carded and how many cards there are.
4. **Author one note per key point**, consolidating that slide's 1–3 facts into a SINGLE note
   with c1/c2/c3 (don't spawn separate notes). Follow the style contract (subject-first,
   two-sided, markup, hints). Pull exact numbers/spellings from the **textbook only to pin a
   fact on a card you're already making** — never read the textbook to find new cards. Write
   to `…/<week>/<subject>/cards/<deck-or-topic>.jsonl`.
5. **Objective sweep (last).** Check every learning objective is covered by the notes you
   wrote; add a note ONLY where an objective is uncovered. Then optionally **visual cards**
   from the deck's figures → `…/cards/visual-<weekNN>.jsonl` + `media/` (see subworkflow).
6. **Generate previews:** `python classes/ISF/make_preview.py "<cards dir>"` renders
   every `*.jsonl` to a readable `*-preview.md` (cloze answers revealed, images
   inlined). Re-run after any edit so previews never go stale — don't hand-edit them.
7. **Validate** (mechanical), **review** for accuracy when it matters (see below),
   then **build**.

File layout per week/subject:
```
Week N/<Subject>/
  <source files…>
  cards/
    chapter-1.jsonl   chapter-1-preview.md
    visual-weekNN.jsonl   visual-weekNN-preview.md
    media/ vis-*.jpeg|png
  <Subject>-WeekN.apkg        ← build output
```

---

## Source hierarchy (what to build off of)

Not all sources are equal — use each by its ROLE. `extract_sources.py` ingests
`.pdf` + `.vtt` + `.txt`, writing greppable text and a heuristic role guess into
`sources/_manifest.txt`; confirm the roles by actually reading each file.

- **Slides — the ANCHOR and the card unit.** Generation *walks the deck slide by slide*; each
  stressed slide → ~1 note (occasionally 2). The deck decides WHAT gets carded and HOW MANY.
  This is the spine of the whole flow.
- **Transcript — the SELECTOR (+ emphasis).** What the teacher stressed on a slide is what
  earns a card and how much weight; slides they skipped don't need one. Closest proxy for
  "what will be tested." Walk it alongside the slides.
- **Objectives — the CHECKLIST.** Every learning objective must end up covered. Swept LAST, to
  fill any gap the slide walk missed — not used to generate in bulk.
- **Textbook — PRECISION ONLY.** Consulted to pin an exact number/definition/spelling onto a
  card that *already exists*. **NEVER read the textbook to find new cards** — mining it
  cover-to-cover is exactly what bloated the deck ~5×.

Two jobs, two authorities:
- **What to card / how many** → the SLIDE WALK (slides as anchor + transcript emphasis, then
  objective sweep). The count comes from the deck, not from how much the textbook contains.
- **Exact wording on those cards — numbers, definitions, spellings** → textbook/slides. A Zoom
  auto-caption is full of ASR errors ("glycogen"↔"glucagon", "about a hundred grams") — never
  lock a precise fact to transcript wording.

**Do not generate a subject until its ANCHOR sources are present.** Required: the **slide deck**
(anchor) + **transcript** (selector) + **objectives** (checklist). The textbook is *optional*
(precision only). Without the deck there is nothing to walk; without the transcript you can't
tell which slides were stressed; without objectives you can't verify coverage. Never
slides-only, never textbook-only. (Wk1 Biochem generated slides-only produced ungrounded
numbers; the Wk1 rebuild mined the textbook and ran 5× too dense — this rule prevents both.)

### The objectives PDF is the index

The learning-objectives PDF ties everything together: each objective cites its **slide(s)**
*and* its **textbook pages** (real example — Wk1 Biochem: *"Marks 6e pp 3-8, 475-482, 67-70,
7-8; figs 1.6, 5.1-5.8, 1.4, 26.2"* and *"(slide #5-12)"*). So the pipeline is
**objective-indexed**: cover every objective, and ground each on the sources it names. Record
the cited page ranges in the week's `readings:` in `course-map.yaml`.

### Textbooks — store once, slice by chapter

Textbooks are big; do NOT dump a copy into every week or fuzzy-grep the whole book. Keep ONE
copy per book in `classes/ISF/textbooks/` (filenames in course-map's `textbooks:` map).

Slice the relevant chapters into the subject's `sources/`. **Prefer content-anchored PDF
ranges** — many textbook PDFs are reflowed (e.g. Marks 6e extracts as 4330 PDF pages) so
printed page numbers don't extract, and objectives often cite an earlier edition's pagination.
Find each chapter's PDF bounds once (search the extracted text for the chapter opener and the
next chapter's opener), record them as `textbook_pdf_ranges` in course-map, and slice:

    python classes/ISF/slice_textbook.py classes/ISF/textbooks/marks-biochem-6e.pdf \
        "Week 1/Biochemistry/sources" --pdf-ranges 21-68 171-223 --label ch1-fuels ch5-functional-groups

(If a book really is one-page-per-printed-page, you may instead use `--ranges <printed>
--offset N`, offset = pdf − printed.) Sliced chapters are the precision authority for
numbers/definitions/spellings — **grep a known fact to confirm the slice landed** before use.

---

## Visual recognition cards (slide decks / atlases)

Hard-won rules — follow them:

- **Identify EVERY image BY SIGHT before writing its card.** Slide titles and the
  deck's own labels do NOT reliably describe the extracted image, and raw
  micrographs are ambiguous. View the image, confirm the structure from its actual
  features, *then* write the card. Never label from the slide title alone.
- **Crop multi-panel figures to single panels** so the answer isn't visible on the
  front. Use Pillow (fractional-box crop). Re-view crops to confirm content.
- The deck's own pointer labels (C, M, L, PD, EC, HC, NU, TW…) may stay on the
  image — they're pointers, not the answer text. Reference them in the prompt
  ("C = its sacs").
- If identity is genuinely ambiguous, frame the card around what's defensible
  (e.g. the *technique*) or drop the image. Never put a guess on a card.

Extracting images from a .pptx (it's a zip):
```python
import zipfile
z = zipfile.ZipFile("deck.pptx")
# images live in ppt/media/ ; slide text in ppt/slides/slideN.xml (<a:t> runs);
# slide→image mapping in ppt/slides/_rels/slideN.xml.rels
```
Triage many images with a contact sheet (Pillow), view it, then crop/keep.

---

## Validate & build

Validate (run before every build; exits non-zero on any error):
```bash
python classes/ISF/validate_cards.py "Week 1/Histology/cards"
```

Build the .apkg:
```bash
python classes/ISF/build_apkg.py \
  --cards "Week 1/Histology/cards" \
  --deck  "ISF::Week 1::Histology" \
  --out   "Week 1/Histology/ISF-Week1-Histology.apkg"
```

Both scripts take a cards dir, so they work for any week/subject. Card identity —
both the `.apkg` GUID and the sync `key::` tag — is **position-based
(`deck|file|ordinal`)**, so **append new cards at the end of a file** rather than
inserting mid-file, to keep identity (and review scheduling) stable.

**Dependencies:** a ready venv exists at **`classes/ISF/.venv`** (genanki + Pillow) —
use `classes/ISF/.venv/bin/python` to run `build_apkg.py` and image-crop scripts.
`extract_sources.py` needs `pdftotext` (`brew install poppler`). To recreate the venv:
```bash
python3 -m venv classes/ISF/.venv && classes/ISF/.venv/bin/pip install genanki Pillow
```

### Sync to the live Anki collection (primary update path)

The `.apkg` is for a fresh machine / sharing / backup. To update a collection you're
already studying, DON'T re-import (that duplicates note-type changes and needs manual
deletes) — run the sync:
```bash
python classes/ISF/sync_anki.py --cards "Week 1/Histology/cards" --deck "ISF::Week 1::Histology"
```
It diffs the JSONL against the live collection by the stable `key::<deckslug>::<file>::<ordinal>`
tag (which `build_apkg.py` also stamps) and applies adds / updates / deletes idempotently.
Identity is that key, **not** Anki's GUID (AnkiConnect can't set a GUID), so it works for
note-type changes too. Updates reuse the note id → **review history is preserved**. Needs
Anki open with AnkiConnect (127.0.0.1:8765). `--dry-run` previews; `--reset-unkeyed` is a
ONE-TIME migration that clears legacy pre-key notes before the first keyed sync. Loop:
edit JSONL → `validate` → `sync_anki.py`. (Rebuild the `.apkg` too if you want the export current.)

---

## Review for STYLE + SENSE (dedicated step — always run, after generation, before accuracy)

There are THREE review axes, all mandatory: **STYLE** (shape — this step + the linter), **SENSE**
(content clarity — this step), and **ACCURACY** (facts — the next section). `validate_cards.py`
checks well-formedness and `lint_cards.py` checks shape — but NEITHER checks whether a card *makes
sense*. Fan out one reviewer per card file (Sonnet or Opus), each reading (a) the Card-style
contract + `MARKUP.md` and (b) its card file, then **fixing in place** every violation:

- **CONTENT SENSE (the axis the linter can't see)** — each card must test a REAL concept in CLEAR,
  NATURAL English with a sensible subject/answer split. A canonical-shaped card can still be
  nonsense ("An amine nitrogen ionizes to a positive charge when it gains a fourth bond"). Rewrite
  garbled/awkward cards; DROP or convert-to-image any "draw a structure / show all atoms" visual
  task (not clozable). Remove near-duplicates across the file.
- **ONE concept per card** — SPLIT any card that crams two distinct concepts (e.g. direct vs
  indirect ICC → two cards). Consolidate only *aspects of one concept*.
- **Cloze cap** — 2 clozes is the norm (bold subject + one italic answer); 3 rare; 4+ = error. Merge chopped answers into ONE italic span; split into a second card for a genuinely distinct fact.
- **Subject-first** — open with the key term as a cloze; no circumstantial scene-setting that
  buries the answer at the end.
- **Complete-answer spans; verb-phrase blanks; no terminal period.**
- **Markup roles** (`<b>` subject / `<u>` facet / `<i>` answer); a pointed `::hint` on every
  standalone cloze; multi-part answers as numbered `<br>` lists sharing one cloze.

Splitting a card here changes card count — fine on a fresh deck (no review history yet). This is
SEPARATE from the accuracy review below: **style fixes wording/structure, accuracy fixes facts —
run both.** (In the `build-week` workflow this is the "Review B · quality" pass.)

**Lint tooling — confirm mechanically, don't eyeball.** Run the style linter and iterate until
`error_count == 0`, then reconcile the warnings by hand:

    python classes/ISF/lint_cards.py "<cards dir>"          # human summary (exit 1 on errors)
    python classes/ISF/lint_cards.py "<cards dir>" --json   # structured for agents

Or, via the **`anki-style` MCP server** (same logic, always available even to sandboxed
subagents): `anki_style_lint(path=…)` → `{errors[], warnings[]}`, and `anki_style_guide()` →
this contract. `errors` are hard mechanical rules (cloze cap, terminal period, markup balance,
tags, JSON) — fix all. `warnings` are heuristic suspects (subject-first, two-concept "whereas…",
missing hint, 4-cloze) — a human/model adjudicates each. The linter is the source of truth for
the *mechanical* rules; judgment rules it can only flag.

---

## Review cards for accuracy (the `review` step)

`validate_cards.py` checks that a card is well-formed — NOT that it is **true**.
Accuracy review is a separate, agent-driven step. The rule that makes it work:

> **Ground every claim in the assigned source, not in model knowledge.** A reviewer
> reasoning from training data will confidently "correct" facts that are verbatim
> from the textbook. (Real example, Wk1 audit: ungrounded reviewers flagged "37%
> formaldehyde", "~150 bp nucleosome", and "1000-fold EM resolution" as errors — all
> three are exact Junqueira quotes. The reviewer that actually read the source PDF
> flagged none of them.) A stronger model does NOT fix this — grounding does.

> **When taught sources conflict, the LECTURE wins — not the textbook.** The deck is
> slide-anchored: the student is examined on what the professor actually taught. If a slide
> or the lecture states a figure the textbook contradicts (Wk1: the slide's *100 g liver /
> 400 g muscle* glycogen vs the textbook's ~80/150), KEEP the slide/lecture value — you may
> note the textbook figure in `extra`, but never overwrite the taught number with it. The
> textbook is a *precision* reference for facts the lecture leaves imprecise, NOT an authority
> that overrides the lecture on facts it does teach.

Recipe — **find cheap, verify strong:**

1. **Cache sources as text** (greppable, so claims can be checked):
   `python classes/ISF/extract_sources.py "Week 1/Histology"` → writes
   `Week 1/Histology/sources/<slug>.txt`.
2. **Fan out one reviewer per card file** on **Sonnet 5** (`Agent` with
   `model: "sonnet"`). Each reviewer MUST read (a) this spec, (b) its card file, and
   (c) the matching source text, then judge every card for: cloze hygiene,
   ambiguous/answer-leaking fronts, non-atomic blanks, tag correctness,
   near-duplicates, and — grounded in the source — factual accuracy. Image-card
   reviewers must VIEW each image and confirm the ID matches.
   Finding format: `line | HIGH|MED|LOW | TYPE | quote | issue | fix`.
3. **One cross-file reviewer** (Sonnet 5): duplication across files, tag drift, and
   coverage vs the week's `objectives` in `course-map.yaml`.
4. **Verify pass — strong model (the main/Opus loop, NOT the cheap tier).** For every
   ACCURACY / HIGH flag, re-check it against the cached source text and classify:
   *source-faithful* → **keep** the card (the reviewer was wrong; record why);
   *real error* → **fix**. This is the step that must not be fooled — keep it strong.
5. **Synthesize** a report grouped as **fixes to apply | kept-as-faithful | coverage
   gaps**. Apply agreed fixes → re-`validate` → re-`build`.

Severity: HIGH = wrong/unanswerable/misleading; MED = ambiguous/leaky/non-atomic/
spec-drift; LOW = cosmetic. Be conservative — report real defects, not preferences.
Coverage gaps are *new content*: list them, don't silently add cards.

**Ungrounded-but-correct facts** (true general knowledge the week didn't actually teach —
e.g. a rationale the professor explicitly deferred to a later module): KEEP the card, tag it
`flag::beyond-scope`, and record it. The learner filters/suspends `flag::beyond-scope` in
Anki. Never keep such a fact untagged, and never delete it. (A fact *contradicted* by the
source is different — fix that.)

---

## Definition of done

- [ ] Anchor sources present + used: slide deck (anchor) + transcript (selector) + objectives (checklist); textbook precision-only — never slides-only, never textbook-mined
- [ ] Slide-anchored volume: ~1 note per stressed slide (occasionally 2); each a SINGLE note with 1–3 clozes (facts consolidated, not spawned as separate notes); density ≈ Neurogenetics (~20–40 notes/lecture), NOT textbook-exhaustive
- [ ] Objective sweep done — every objective covered; ungrounded-but-correct facts tagged flag::beyond-scope (kept, not deleted, not silent)
- [ ] Cloze-first; cloze STRUCTURE + markup match `chapter-1.jsonl` (match its style, NOT its density)
- [ ] Structure: every card opens subject-first with a deletion (no buried subject); each blank spans the complete answer concept (no clipped answers with the tail exposed); verb phrases clozed whole; no terminal period
- [ ] Markup/color convention applied: subject `<b>`, answer `<i>`, multi-part answers as numbered lists
- [ ] Tags follow the hierarchy; no spaces in tags
- [ ] Every image identified by sight; multi-panel figures cropped
- [ ] Preview .md written for human review
- [ ] `validate_cards.py` passes (0 errors)
- [ ] For accuracy-critical batches: source-grounded `review` run; every accuracy flag reconciled against the source (faithful → keep, real → fix)
- [ ] `.apkg` built (only when the user wants it importable)
