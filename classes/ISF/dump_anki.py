#!/usr/bin/env python3
"""Reconstruct card JSONL files FROM the live Anki collection (inverse of sync_anki.py).

Uses the `key::<deckslug>::<filestem>::<ordinal>` identity tags to rebuild each source
file exactly, in order. Handy for recovering the JSONL source of truth from Anki (so the
collection doubles as a backup), or undoing an accidental local overwrite.

  python dump_anki.py --deck "ISF::Week 1::Biochemistry" --out "<cards dir>"

Needs Anki open with AnkiConnect (127.0.0.1:8765).
"""
import argparse, json, os, re, sys, urllib.request

ANKI = "http://127.0.0.1:8765"


def invoke(action, **params):
    body = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKI, body, {"Content-Type": "application/json"})
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=30).read())
    except Exception as e:
        sys.exit(f"Can't reach AnkiConnect at {ANKI} — is Anki open with the add-on? ({e})")
    if res.get("error"):
        raise RuntimeError(f"{action}: {res['error']}")
    return res["result"]


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def to_card(model, fields, tags):
    """Rebuild the JSONL dict for one note (fields/tags from notesInfo)."""
    f = {k: v["value"] for k, v in fields.items()}
    src = f.get("Source", "")
    extra = f.get("Extra", "")
    if model == "Custom Cloze":
        card = {"type": "cloze", "text": f.get("Text", "")}
    else:  # Custom Basic — image if the Front carries an <img>
        front = f.get("Front", "")
        m = re.match(r'<img src="([^"]+)">(?:<br>)?(.*)$', front, re.S)
        if m:
            card = {"type": "image", "front": m.group(2), "image": f"media/{m.group(1)}", "back": f.get("Back", "")}
        else:
            card = {"type": "basic", "front": front, "back": f.get("Back", "")}
    if extra:
        card["extra"] = extra
    card["tags"] = [t for t in tags if not t.startswith("key::")]
    card["source"] = src
    return card


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True)
    ap.add_argument("--out", required=True, help="cards dir to (over)write")
    a = ap.parse_args()

    ids = invoke("findNotes", query=f'deck:"{a.deck}"')
    if not ids:
        sys.exit(f"no notes in deck {a.deck!r}")
    dslug = slug(a.deck)
    files = {}   # filestem -> {ordinal: card}
    unkeyed = 0
    for n in invoke("notesInfo", notes=ids):
        key = next((t for t in n["tags"] if t.startswith(f"key::{dslug}::")), None)
        if not key:
            unkeyed += 1
            continue
        _, _, fstem, ordinal = key.split("::", 3)
        files.setdefault(fstem, {})[int(ordinal)] = to_card(n["modelName"], n["fields"], n["tags"])

    os.makedirs(a.out, exist_ok=True)
    total = 0
    for fstem, cards in sorted(files.items()):
        path = os.path.join(a.out, f"{fstem}.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            for ordinal in sorted(cards):
                fh.write(json.dumps(cards[ordinal], ensure_ascii=False) + "\n")
                total += 1
        print(f"wrote {fstem}.jsonl ({len(cards)} cards)")
    if unkeyed:
        print(f"NOTE: skipped {unkeyed} unkeyed note(s) (no key:: tag)")
    print(f"\n{total} cards reconstructed into {a.out}/")


if __name__ == "__main__":
    main()
