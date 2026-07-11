#!/usr/bin/env python3
"""Stage 5 (preview): sync the regenerated decks to a temp ISF::Regen Preview, uploading slide images as media.

Reads each deck's out/cards.reviewed.jsonl (or pass a filename arg, e.g. cards.final.jsonl), uploads every
referenced slide image via storeMediaFile, creates ISF::Regen Preview::<name>, and adds the cards (Custom Cloze).
Non-destructive — builds a disposable preview so a human can eyeball atomic cards + slide provenance.
Part of the regen pipeline — see classes/ISF/REGEN-PIPELINE.md.
"""
import json, os, re, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)  # classes/ISF
ANKI = "http://127.0.0.1:8765"
CLOZE = "Custom Cloze"
FNAME = sys.argv[1] if len(sys.argv) > 1 else "cards.reviewed.jsonl"

def invoke(action, **params):
    body = json.dumps({"action": action, "version": 6, "params": params}).encode()
    res = json.loads(urllib.request.urlopen(urllib.request.Request(ANKI, body, {"Content-Type": "application/json"}), timeout=120).read())
    if res.get("error"): raise RuntimeError(f"{action}: {res['error']}")
    return res["result"]

DECKS = [
 ("Week 1/Biochemistry/01-dietary-fuels", "ISF::Regen Preview::Dietary Fuels"),
 ("Week 1/Biochemistry/02-functional-groups", "ISF::Regen Preview::Functional Groups"),
 ("Week 1/Histology/01-methods-cytoplasm-nucleus", "ISF::Regen Preview::Histology Methods"),
 ("Week 2/Biochemistry/01-carbohydrate-structure", "ISF::Regen Preview::Carbohydrate Structure"),
 ("Week 2/Biochemistry/02-lipid-structure", "ISF::Regen Preview::Lipid Structure"),
 ("Week 2/Embryology/01-intro-embryo", "ISF::Regen Preview::Intro Embryology"),
 ("Week 2/Histology/01-epithelium", "ISF::Regen Preview::Epithelium"),
]
for deckdir, prev in DECKS:
    cards = [json.loads(l) for l in open(f"{BASE}/{deckdir}/out/{FNAME}", encoding="utf-8") if l.strip()]
    slidedir = f"{BASE}/{deckdir}/out/slides"
    imgs = {m.group(1) for c in cards if (m := re.search(r'<img src="([^"]+)"', c.get("extra", "")))}
    for img in sorted(imgs):
        p = os.path.join(slidedir, img)
        if os.path.exists(p): invoke("storeMediaFile", filename=img, path=os.path.abspath(p))
    invoke("createDeck", deck=prev)
    notes = [{"deckName": prev, "modelName": CLOZE,
              "fields": {"Text": c["text"], "Extra": c.get("extra", ""), "Source": c.get("source", "")},
              "tags": c.get("tags", []), "options": {"allowDuplicate": True}} for c in cards]
    added = sum(1 for x in invoke("addNotes", notes=notes) if x)
    print(f"{prev.split('::')[-1]:26} {len(imgs):3} images | {added}/{len(cards)} cards")
