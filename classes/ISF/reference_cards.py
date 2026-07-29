"""The canonical reference cards — the minimum set that shows every shape, hand-built.

Not pulled from a deck. The previous reference was the 37-card Bone deck, and picking exemplars
out of it surfaced defects in the reference itself: a subject left un-clozed, a hint that is not a
complete thought ("what three?"), and a card with two <b> spans that the style guide forbids. A
reference has to be right, and 37 cards is 31 more than the shapes require.

One card per SHAPE, SIX shapes:
  A  two clozes: subject + answer                       (the workhorse)
  B  two clozes: subject + answer, with a visible facet
  C  three clozes: subject + clozed facet + answer      (the either/or shape)
  D  one cloze:  answer only, subject and facet visible (the subject is the frame, not the answer)
  E  list card:  clozed subject, visible facet, numbered items sharing ONE cloze number
  F  image card: the picture is one cloze, the term the other

EVERY CARD OBEYS:
  · <b> subject, <u> facet, <i> answer — in that order, subject first
  · each hint reads as a complete question when substituted into its blank
  · no unstyled text inside the braces; no <b> nested in <i>; at most 3 cloze numbers

TRUE OF THE PROSE SHAPES (A–D), AND DELIBERATELY NOT OF E AND F:
  · every cloze carries a hint — EXCEPT the image cloze in F, which has nothing to disambiguate,
    and items 2..n of the list in E, which share their number (and therefore their hint) with item 1
  · exactly one <i> answer — E has five, all on one cloze number, which is what makes it one answer
  · the card ENDS on its answer — F closes with "that we can see", the recognition-card idiom
  · one <b> span per card — F has none; there is no subject to name, that is the question

Those four carve-outs are not sloppiness. They are why E and F exist: a prompt that states the
prose invariants as universals cannot produce a list card or a recognition card. A cold reader
given only the prose rules wrote the image card with the term in <b>, a hint on the picture, and
an invented frame — because the four lines above had been written as absolutes.
"""
import json

CARDS = [
    # A — two clozes, subject + answer, no facet
    {"id": "ref-01",
     "text": "{{c1::<b>Osteoid</b>::which material?}} is "
             "{{c2::<i>unmineralized bone matrix</i>::what is it?}}"},

    # B — two clozes with a VISIBLE facet naming the aspect asked about
    {"id": "ref-02",
     "text": "{{c1::<b>Osteoclasts</b>::which bone cells?}} <u>function</u> to "
             "{{c2::<i>resorb bone matrix</i>::do what?}}"},

    # C — three clozes: the either/or choice wears <u>, the value wears <i>
    {"id": "ref-03",
     "text": "{{c1::<b>Calcitonin</b>::which hormone?}} acts on bone to "
             "{{c2::<u>lower</u>::raise or lower?}} "
             "{{c3::<i>blood calcium levels</i>::which levels?}}"},

    # D — the subject is the FRAME: nobody is asked "which tissue is classified?", so it stays
    #     visible. This is the shape that must exist or the author over-clozes every subject.
    {"id": "ref-04",
     "text": "<b>Connective tissue</b> is <u>classified</u> into "
             "{{c1::<i>embryonic, proper, and specialized types</i>::which three classes?}}"},

    # E — list: clozed subject, visible facet, then ONE NUMBERED LINE PER ITEM. The numbers sit
    #     OUTSIDE the braces and are not italicised — they are scaffolding, not answers. Every
    #     item shares c2, so the whole list is one card view: you produce all five together.
    {"id": "ref-05",
     "text": "The {{c1::<b>epiphyseal growth</b>::which structure?}} plate has five <u>zones</u>:"
             "<br><br>"
             "1. {{c2::<i>resting cartilage</i>::which five zones?}}<br>"
             "2. {{c2::<i>proliferating cartilage</i>}}<br>"
             "3. {{c2::<i>hypertrophic cartilage</i>}}<br>"
             "4. {{c2::<i>calcified cartilage</i>}}<br>"
             "5. {{c2::<i>ossification</i>}}"},

    # F — image recognition. The IMAGE is one cloze and the term is the other, so the pair tests
    #     both directions: hide the picture and you recall what it looks like; hide the term and
    #     you name the tissue from the picture. The image cloze takes no hint — there is nothing
    #     to disambiguate about a picture.
    {"id": "ref-06",
     "text": '{{c1::<img src="ref-osteon.jpg">}}<br><br>'
             "This is {{c2::<i>compact bone</i>::which tissue?}} that we can see"},
]

for c in CARDS:
    c["extra"] = ""
    c["source"] = "reference card"
    c["tags"] = ["isf::reference", "src::reference-deck"]
    c["status"] = "approved"
    c["note"] = ""

def corpus_rows():
    """The cards in CORPUS format — the shape style_check.py and the prompt builders read.

    This must match what `build_deck corpus` used to pull out of Anki, because every consumer of
    reference_cards.jsonl was written against that shape.
    """
    return [{"note_id": c["id"], "model": "Custom Cloze",
             "fields": {"Text": c["text"], "Extra": c["extra"], "Source": c["source"]},
             "tags": ["isf::reference"]} for c in CARDS]


if __name__ == "__main__":
    import sys, os
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "reference_cards.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for r in corpus_rows():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(CARDS)} reference cards -> {out}")
