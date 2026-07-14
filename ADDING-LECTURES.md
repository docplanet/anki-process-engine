# Adding a lecture

Every lecture becomes one deck. The layout is **one folder per lecture**, split by role:

```
classes/<Course>/Week NN/<Strand>/NN-slug/
├─ job.yaml          # the run config (points at the sources below)
├─ slides.pdf        # the ANCHOR — the engine walks this slide-by-slide
├─ raw/              # untouched originals (slide .pptx, recording, objectives, textbook PDFs)
├─ sources/          # extracted .txt the engine reads (transcript, objectives, textbook)
└─ out/              # generated: cards.jsonl, deck.apkg, ledger, state  (= job.yaml `cards_dir`)
```

Each lecture is **self-contained**: a transcript or objectives file shared across a week is *copied*
into each lecture's `sources/` (no `../` references). Textbooks live once, centrally, in
`classes/ISF/textbooks/`; page ranges are sliced per-lecture with `slice_textbook.py`.

## The one-command prep

Drop a lecture's raw materials into a folder — the slide deck (`.pptx` or `.pdf`), a lecture
recording (`.vtt`/`.txt`), the learning objectives (`.pdf`/`.docx`), and any textbook chapter PDF —
then:

```bash
classes/ISF/.venv/bin/python classes/ISF/prep_lecture.py \
    "classes/ISF/Week 2/Biochemistry/03-amino-acids" \
    --deck "ISF::Week 2::Biochemistry (Engine)::Amino Acids" \
    --subject biochem
```

`prep_lecture.py` organizes originals into `raw/`, converts `.pptx → .pdf` (LibreOffice) and
`.docx → .txt` (textutil), extracts every source to `sources/*.txt` (reusing `extract_sources.py`),
copies the slide deck to `slides.pdf`, and scaffolds `job.yaml`. Review `sources/_manifest.txt` (the
role guesses) and the generated `job.yaml`, then run.

## The job.yaml

`prep_lecture.py` writes this; edit if a role was mis-guessed. Histology decks have no separate
objectives (they're embedded in slides/transcript) — just omit that line.

```yaml
run:
  deck: "ISF::Week 2::Biochemistry (Engine)::Amino Acids"
  subject: biochem
  cards_dir: out

sources:
  - { file: slides.pdf,                 role: slides,     anchor: true, extract: pdf_pages }
  - { file: sources/transcript.txt,     role: transcript, extract: text }
  - { file: sources/objectives.txt,     role: objectives, extract: text }   # omit for histology
  - { file: sources/textbook-ch7.txt,   role: textbook,   extract: text }

anchor:  { unit: slide, source_role: slides }
yield:   { max_cards_per_unit: 4, default: 1, allow_zero: true }
gates:   { spec: consensus, accuracy: hard, style: hard }
```

## Run it

The card-generation pipeline is the atomic-first, mold-gated regen flow. A one-command automated
driver is being rebuilt from scratch and is not yet dialed in; until then the pipeline is run as the
orchestrated subagent stages + `classes/ISF/regen/` scripts documented in
**`classes/ISF/REGEN-PIPELINE.md`** (start there for the per-stage contracts, the mold, and the gates).
