#!/usr/bin/env python3
"""Stage 5 (ship): replace the real ISF::Test 1 leaf decks with cards.final.jsonl.

DESTRUCTIVE: deletes each target deck's existing notes (and their review history), then adds the finalized
cards tagged key::<slug>::<id> so future edits re-sync idempotently (see sync_anki.py). Ensures every
referenced slide image is in the media collection first. Run only after the preview is approved.
Part of the regen pipeline — see classes/ISF/REGEN-PIPELINE.md.
"""
import json, os, re, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)  # classes/ISF
ANKI = "http://127.0.0.1:8765"
CLOZE = "Custom Cloze"

def invoke(action, **params):
    body = json.dumps({"action": action, "version": 6, "params": params}).encode()
    res = json.loads(urllib.request.urlopen(urllib.request.Request(ANKI, body, {"Content-Type": "application/json"}), timeout=180).read())
    if res.get("error"): raise RuntimeError(f"{action}: {res['error']}")
    return res["result"]

# (deck source dir, real Anki deck name, key slug)
MAP = [
 ("Week 1/Biochemistry/01-dietary-fuels", "ISF::Test 1::Week 1::Biochemistry (Engine)::Dietary Fuels", "dietary-fuels"),
 ("Week 1/Biochemistry/02-functional-groups", "ISF::Test 1::Week 1::Biochemistry (Engine)::Functional Groups", "functional-groups"),
 ("Week 1/Histology/01-methods-cytoplasm-nucleus", "ISF::Test 1::Week 1::Histology (Engine)::Methods, Cytoplasm & Nucleus", "histology-methods"),
 ("Week 2/Biochemistry/01-carbohydrate-structure", "ISF::Test 1::Week 2::Biochemistry (Engine)::Carbohydrate Structure", "carbohydrate-structure"),
 ("Week 2/Biochemistry/02-lipid-structure", "ISF::Test 1::Week 2::Biochemistry (Engine)::Lipid Structure", "lipid-structure"),
 ("Week 2/Embryology/01-intro-embryo", "ISF::Test 1::Week 2::Embryology (Engine)::Intro to Embryology", "intro-embryo"),
 ("Week 2/Histology/01-epithelium", "ISF::Test 1::Week 2::Histology (Engine)::Epithelium", "epithelium"),
]
if "--yes" not in sys.argv:
    sys.exit("Refusing to run without --yes (this deletes the real decks' notes + review history).")
total_del = total_add = 0
for deckdir, real, slug in MAP:
    out = f"{BASE}/{deckdir}/out"; slidedir = f"{out}/slides"
    cards = [json.loads(l) for l in open(f"{out}/cards.final.jsonl", encoding="utf-8") if l.strip()]
    imgs = {m.group(1) for c in cards if (m := re.search(r'<img src="([^"]+)"', c.get("extra", "")))}
    for img in sorted(imgs):
        p = os.path.join(slidedir, img)
        if os.path.exists(p): invoke("storeMediaFile", filename=img, path=os.path.abspath(p))
    old = invoke("findNotes", query=f'deck:"{real}"')
    if old: invoke("deleteNotes", notes=old)
    invoke("createDeck", deck=real)
    notes = [{"deckName": real, "modelName": CLOZE,
              "fields": {"Text": c["text"], "Extra": c.get("extra", ""), "Source": c.get("source", "")},
              "tags": c.get("tags", []) + [f"key::{slug}::{c['id']}"],
              "options": {"allowDuplicate": True}} for c in cards]
    added = sum(1 for x in invoke("addNotes", notes=notes) if x)
    total_del += len(old); total_add += added
    warn = "  ⚠️ PARTIAL ADD — old notes already deleted; investigate before re-running" if added < len(cards) else ""
    print(f"{real.split('::')[-1]:34} -{len(old):3} old | +{added}/{len(cards)} new | {len(imgs)} imgs{warn}")
print(f"\nTOTAL: deleted {total_del} old, added {total_add} finalized cards")
