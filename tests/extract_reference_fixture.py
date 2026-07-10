#!/usr/bin/env python3
"""Regenerate the golden-test fixture from the reference deck.

The fixture (tests/fixtures/neurogenetics_ref.jsonl) is the 368 cloze notes of the AnKing
Neurogenetics deck — the MEASURED source of truth the style linter is calibrated against
(test_reference_deck.py). It is COPYRIGHTED third-party content, so it is gitignored and NOT
committed to this public repo. Run this once locally to (re)create it from your own copy of
Neurogenetics.apkg (placed at the repo root).

Usage:  python tests/extract_reference_fixture.py [path/to/Neurogenetics.apkg]
"""
import json, os, sqlite3, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_APKG = os.path.join(HERE, "..", "Neurogenetics.apkg")
OUT = os.path.join(HERE, "fixtures", "neurogenetics_ref.jsonl")


def main(apkg):
    if not os.path.exists(apkg):
        sys.exit(f"reference deck not found: {apkg}\n"
                 f"Place Neurogenetics.apkg at the repo root, or pass its path as an argument.")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(apkg) as z:
        tmp = tempfile.mkdtemp()
        # collection.anki21 holds the real notes; collection.anki2 is a legacy stub.
        member = "collection.anki21" if "collection.anki21" in z.namelist() else "collection.anki2"
        z.extract(member, tmp)
    db = sqlite3.connect(os.path.join(tmp, member))
    n = 0
    with open(OUT, "w", encoding="utf-8") as f:
        for flds, tags in db.execute("select flds, tags from notes"):
            text = next((fld for fld in flds.split("\x1f") if "{{c" in fld), None)
            if not text:
                continue
            taglist = [t for t in (tags or "").split() if t] or ["ref"]
            f.write(json.dumps({"type": "cloze", "text": text, "tags": taglist, "source": "ref"},
                               ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} reference cloze cards -> {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_APKG)
