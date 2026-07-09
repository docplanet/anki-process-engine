#!/usr/bin/env python3
"""Sync a folder of card JSONL files INTO the live Anki collection via AnkiConnect.

The JSONL is the source of truth. Each note carries a stable identity tag
`key::<deckslug>::<filestem>::<ordinal>` that this script and build_apkg.py both compute,
so add / update / delete are idempotent by THAT key — not Anki's GUID, and with no
.apkg re-import. Edit cards -> run this -> the live deck matches, forever.

  python sync_anki.py --cards "Week 1/Histology/cards" --deck "ISF::Week 1::Histology"
  python sync_anki.py --cards ... --deck ... --dry-run          # preview only
  python sync_anki.py --cards ... --deck ... --reset-unkeyed    # one-time migration:
      # delete legacy (pre-key) notes in the deck first, then add everything keyed.

Needs Anki open with the AnkiConnect add-on (http://127.0.0.1:8765).
Updates preserve each note's id (and thus its review history); only genuine
adds/deletes create/remove scheduling.
"""
import argparse, glob, json, os, re, sys, urllib.request

ANKI = "http://127.0.0.1:8765"
CLOZE_MODEL, BASIC_MODEL = "Custom Cloze", "Custom Basic"


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


def render(c, cards_dir):
    """(model, fields, media) exactly as build_apkg.py would emit."""
    extra, source = c.get("extra", ""), c.get("source", "")
    t = c["type"]
    if t == "cloze":
        return CLOZE_MODEL, {"Text": c["text"], "Extra": extra, "Source": source}, None
    if t == "basic":
        return BASIC_MODEL, {"Front": c["front"], "Back": c["back"], "Extra": extra, "Source": source}, None
    if t == "image":
        base = os.path.basename(c["image"])
        front = f'<img src="{base}"><br>{c["front"]}'
        return BASIC_MODEL, {"Front": front, "Back": c["back"], "Extra": extra, "Source": source}, \
               (base, os.path.join(cards_dir, c["image"]))
    sys.exit(f"unknown card type {t!r}")


def load_jsonl(cards_dir, deck):
    want = {}
    for path in sorted(glob.glob(os.path.join(cards_dir, "*.jsonl"))):
        fstem = os.path.splitext(os.path.basename(path))[0]
        for i, line in enumerate(open(path, encoding="utf-8")):
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            k = f"key::{slug(deck)}::" + (c["id"] if c.get("id") else f"{fstem}::{i}")
            model, fields, media = render(c, cards_dir)
            want[k] = {"model": model, "fields": fields, "media": media,
                       "tags": list(c.get("tags", [])) + [k]}
    return want


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", required=True)
    ap.add_argument("--deck", required=True)
    ap.add_argument("--reset-unkeyed", action="store_true",
                    help="one-time migration: delete legacy notes in the deck that have no key:: tag")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-lint", action="store_true", help="skip the style-lint gate (sync even with lint errors)")
    ap.add_argument("--no-review", action="store_true", help="skip the per-card review gate (sync even if cards are unreviewed/stale/flagged)")
    a = ap.parse_args()
    import lint_cards; lint_cards.gate(a.cards, a.no_lint)          # SHAPE GATE — refuse on lint errors
    import review_ledger; review_ledger.gate(a.cards, a.no_review)  # JUDGMENT GATE — refuse on unreviewed/stale/flagged cards
    live = not a.dry_run

    models = set(invoke("modelNames"))
    for m in (CLOZE_MODEL, BASIC_MODEL):
        if m not in models:
            sys.exit(f"note type {m!r} not in Anki — import any built deck once so the note types exist, then re-run.")
    if a.deck not in set(invoke("deckNames")) and live:
        invoke("createDeck", deck=a.deck)

    want = load_jsonl(a.cards, a.deck)
    dslug = slug(a.deck)

    if a.reset_unkeyed:
        ids = invoke("findNotes", query=f'deck:"{a.deck}"')
        infos = invoke("notesInfo", notes=ids) if ids else []
        legacy = [n["noteId"] for n in infos if not any(t.startswith("key::") for t in n["tags"])]
        print(f"migration: deleting {len(legacy)} legacy unkeyed note(s) in {a.deck}")
        if legacy and live:
            invoke("deleteNotes", notes=legacy)

    # existing keyed notes in this deck  ->  key -> {id, fields, tags}
    have = {}
    ids = invoke("findNotes", query=f'deck:"{a.deck}" tag:key::*')
    for n in (invoke("notesInfo", notes=ids) if ids else []):
        k = next((t for t in n["tags"] if t.startswith(f"key::{dslug}::")), None)
        if k:
            have[k] = {"id": n["noteId"],
                       "fields": {f: v["value"] for f, v in n["fields"].items()},
                       "tags": set(n["tags"])}

    adds = [k for k in want if k not in have]
    dels = [k for k in have if k not in want]
    n_upd = 0

    if dels and live:
        invoke("deleteNotes", notes=[have[k]["id"] for k in dels])

    for k in adds:
        w = want[k]
        if live:
            if w["media"]:
                invoke("storeMediaFile", filename=w["media"][0], path=os.path.abspath(w["media"][1]))
            invoke("addNote", note={"deckName": a.deck, "modelName": w["model"], "fields": w["fields"],
                                    "tags": w["tags"], "options": {"allowDuplicate": True}})

    for k in (kk for kk in want if kk in have):
        w, h = want[k], have[k]
        changed = False
        if any(h["fields"].get(f, "") != v for f, v in w["fields"].items()):
            if live:
                invoke("updateNoteFields", note={"id": h["id"], "fields": w["fields"]})
            changed = True
        add_t, rem_t = set(w["tags"]) - h["tags"], h["tags"] - set(w["tags"])
        if add_t or rem_t:
            if live:
                if add_t:
                    invoke("addTags", notes=[h["id"]], tags=" ".join(sorted(add_t)))
                if rem_t:
                    invoke("removeTags", notes=[h["id"]], tags=" ".join(sorted(rem_t)))
            changed = True
        if w["media"] and live:
            invoke("storeMediaFile", filename=w["media"][0], path=os.path.abspath(w["media"][1]))
        n_upd += changed

    print(f"{'DRY-RUN ' if a.dry_run else ''}sync {a.deck}: "
          f"+{len(adds)} added, ~{n_upd} updated, -{len(dels)} deleted  (target {len(want)} notes)")


if __name__ == "__main__":
    main()
