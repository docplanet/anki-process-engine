#!/usr/bin/env python3
"""Build an Anki .apkg from a folder of card JSONL files.

Reads every *.jsonl in --cards, supports three card `type`s:
  - cloze : field `text` with {{c1::...}} markers
  - basic : fields `front`, `back`
  - image : fields `front` (prompt), `image` (path rel. to cards dir), `back`
All types also accept optional `extra` (hidden behind a tap-to-reveal button on
the answer) and `source` (small footer line).

Two note types (image reuses Basic), styled to match the AnKing look (dark card,
green clozes) with a self-contained, add-on-free tappable "extra" reveal. GUIDs
are deterministic (deck|file|ordinal) so re-importing a rebuilt deck UPDATES
cards in place instead of duplicating them.

Usage:
  python build_apkg.py --cards "Week 1/Histology/cards" \
      --deck "ISF::Week 1::Histology" --out "Week 1/Histology/ISF-Week1-Histology.apkg"
"""
import argparse, glob, json, os, re, sys
import genanki


def _slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def key_tag(deck_name, file_stem, ordinal):
    """Stable per-card identity tag, shared with sync_anki.py (identity we control, not Anki's GUID)."""
    return f"key::{_slug(deck_name)}::{file_stem}::{ordinal}"

# Fixed IDs so every rebuild targets the same models/deck (idempotent import).
CLOZE_MODEL_ID = 1607392301
BASIC_MODEL_ID = 1607392302
DECK_ID_BASE   = 1987000000

CSS = """
.card { font-family: Menlo, baskerville, sans;
        font-size: 19px; line-height: 1.5; max-width: 760px; margin: 0 auto; padding: 8px;
        text-align: center; color: #D7DEE9; background-color: #333B45; }
.nightMode.card, .night_mode .card { color: #D7DEE9 !important; background-color: #333B45 !important; }
.cloze { font-weight: bold; color: MediumSeaGreen; }
.nightMode .cloze, .night_mode .cloze { color: MediumSeaGreen !important; }
b { color: #C695C6 !important; }
i { color: IndianRed !important; }
u { color: #5EB3B3 !important; }
img { max-width: 100%; height: auto; border-radius: 6px; margin: 8px 0; }
hr { border: none; border-top: 1px solid #555; margin: 14px 0; }
.btn-reveal { display: inline-block; background: #3b4654; color: #D7DEE9;
              border: 1px solid #51606e; border-radius: 6px; padding: 5px 12px;
              font-size: 14px; cursor: pointer; margin: 12px 0 6px; }
.btn-reveal:hover { background: #45525f; }
.extra { text-align: center; background: #2c343d; border-radius: 8px;
         padding: 10px 14px; margin: 6px 0; }
.src { color: #839496; font-size: 13px; font-style: italic; margin-top: 10px; }
"""

# Shared answer footer: tap-to-reveal Extra (only if present) + a small source line.
REVEAL = (
    '{{#Extra}}<button class="btn-reveal" onclick="var d=this.nextElementSibling;'
    "d.style.display=(d.style.display=='none'?'block':'none');\">Show extra &#9656;</button>"
    '<div class="extra" style="display:none">{{Extra}}</div>{{/Extra}}'
    '{{#Source}}<div class="src">{{Source}}</div>{{/Source}}'
)

CLOZE_MODEL = genanki.Model(
    CLOZE_MODEL_ID, "Custom Cloze",
    fields=[{"name": "Text"}, {"name": "Extra"}, {"name": "Source"}],
    templates=[{
        "name": "Cloze",
        "qfmt": "{{cloze:Text}}",
        "afmt": "{{cloze:Text}}" + REVEAL,
    }],
    css=CSS, model_type=genanki.Model.CLOZE,
)

BASIC_MODEL = genanki.Model(
    BASIC_MODEL_ID, "Custom Basic",
    fields=[{"name": "Front"}, {"name": "Back"}, {"name": "Extra"}, {"name": "Source"}],
    templates=[{
        "name": "Card 1",
        "qfmt": "{{Front}}",
        "afmt": '{{FrontSide}}<hr id="answer">{{Back}}' + REVEAL,
    }],
    css=CSS,
)


def build(cards_dir, deck_name, out_path):
    deck = genanki.Deck(DECK_ID_BASE + (abs(hash(deck_name)) % 1000000), deck_name)
    media, counts = [], {"cloze": 0, "basic": 0, "image": 0}
    seen_guids = {}

    for path in sorted(glob.glob(os.path.join(cards_dir, "*.jsonl"))):
        fname = os.path.basename(path)
        fstem = os.path.splitext(fname)[0]
        for i, line in enumerate(open(path, encoding="utf-8")):
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            t = c["type"]
            cid = c.get("id")                        # stable identity when present, else positional ordinal
            tag = f"key::{_slug(deck_name)}::{cid}" if cid else key_tag(deck_name, fstem, i)
            tags = list(c.get("tags", [])) + [tag]
            extra = c.get("extra", "")
            source = c.get("source", "")
            guid = genanki.guid_for(cid if cid else f"{deck_name}|{fname}|{i}")
            if guid in seen_guids:
                sys.exit(f"GUID collision: {fname}:{i} vs {seen_guids[guid]}")
            seen_guids[guid] = f"{fname}:{i}"

            if t == "cloze":
                note = genanki.Note(CLOZE_MODEL, [c["text"], extra, source],
                                    tags=tags, guid=guid)
            elif t == "basic":
                note = genanki.Note(BASIC_MODEL, [c["front"], c["back"], extra, source],
                                    tags=tags, guid=guid)
            elif t == "image":
                rel = c["image"]
                full = os.path.join(cards_dir, rel)
                if not os.path.exists(full):
                    sys.exit(f"missing image: {full} ({fname}:{i})")
                media.append(full)
                base = os.path.basename(rel)
                front = f'<img src="{base}"><br>{c["front"]}'
                note = genanki.Note(BASIC_MODEL, [front, c["back"], extra, source],
                                    tags=tags, guid=guid)
            else:
                sys.exit(f"unknown type {t!r} at {fname}:{i}")

            deck.add_note(note)
            counts[t] += 1

    pkg = genanki.Package(deck)
    pkg.media_files = sorted(set(media))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    pkg.write_to_file(out_path)
    total = sum(counts.values())
    print(f"deck: {deck_name}")
    print(f"cards: {total}  ({counts['cloze']} cloze, {counts['basic']} basic, "
          f"{counts['image']} image)")
    print(f"media files: {len(set(media))}")
    print(f"wrote: {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", required=True)
    ap.add_argument("--deck", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-lint", action="store_true", help="skip the style-lint gate (build even with lint errors)")
    ap.add_argument("--no-review", action="store_true", help="skip the per-card review gate (build even if cards are unreviewed/stale/flagged)")
    a = ap.parse_args()
    import lint_cards; lint_cards.gate(a.cards, a.no_lint)          # SHAPE GATE — refuse on lint errors
    import review_ledger; review_ledger.gate(a.cards, a.no_review)  # JUDGMENT GATE — refuse on unreviewed/stale/flagged cards
    build(a.cards, a.deck, a.out)
