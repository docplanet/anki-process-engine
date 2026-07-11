#!/usr/bin/env python3
"""Stage 4 tail: audit gap cards (mold + provenance), merge into cards.final.jsonl, push gap cards to preview decks.

Reads each deck's out/cards.reviewed.jsonl + out/cards.gaps2.jsonl → writes out/cards.final.jsonl,
normalizes gap tags to include src::gap, and (if Anki is open) adds the gap cards to the ISF::Regen Preview decks.
Part of the regen pipeline — see classes/ISF/REGEN-PIPELINE.md.
"""
import json, os, re, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)  # classes/ISF
sys.path.insert(0, BASE)
import strict_shape as s
from lint_cards import _is_list
ANKI = "http://127.0.0.1:8765"
CLOZE = "Custom Cloze"
PUSH_PREVIEW = "--no-anki" not in sys.argv  # skip Anki side-effects with --no-anki (merge-only)

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
grand_rej = 0
for deckdir, prev in DECKS:
    out = f"{BASE}/{deckdir}/out"
    slidedir = f"{out}/slides"
    imgs_on_disk = set(os.listdir(slidedir)) if os.path.isdir(slidedir) else set()
    reviewed = [json.loads(l) for l in open(f"{out}/cards.reviewed.jsonl", encoding="utf-8") if l.strip()]
    gaps_path = f"{out}/cards.gaps2.jsonl"
    gaps = [json.loads(l) for l in open(gaps_path, encoding="utf-8") if l.strip()] if os.path.exists(gaps_path) else []
    rej, no_src, bad_img, no_hint = [], [], [], []
    for c in gaps:
        r = s.classify_card(c)
        if not r.ok: rej.append((c["id"], r.reasons))
        if "MISSING_HINT" in r.soft and not _is_list(c["text"]): no_hint.append(c["id"])
        extra = c.get("extra", "")
        if "ource:" not in extra: no_src.append(c["id"])
        m = re.search(r'<img src="([^"]+)"', extra)
        if m and m.group(1) not in imgs_on_disk: bad_img.append((c["id"], m.group(1)))
        tags = c.get("tags", [])
        if "src::gap" not in tags: tags.append("src::gap")
        c["tags"] = [t for t in tags if t != "src::regen"]
    grand_rej += len(rej)
    clean = not (rej or no_src or bad_img or no_hint)
    name = prev.split("::")[-1]
    print(f"{name:24} gaps={len(gaps):2} {'✓ CLEAN' if clean else '✗'}"
          f"{'' if not rej else ' REJ='+str(rej)}"
          f"{'' if not no_src else ' NO-SRC='+str(no_src)}"
          f"{'' if not bad_img else ' BAD-IMG='+str(bad_img)}"
          f"{'' if not no_hint else ' NO-HINT='+str(no_hint)}")
    if not clean:
        continue
    with open(f"{out}/cards.final.jsonl", "w", encoding="utf-8") as f:
        for c in reviewed + gaps:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    if PUSH_PREVIEW and gaps:
        for c in gaps:
            m = re.search(r'<img src="([^"]+)"', c.get("extra", ""))
            if m:
                p = os.path.join(slidedir, m.group(1))
                if os.path.exists(p): invoke("storeMediaFile", filename=m.group(1), path=os.path.abspath(p))
        notes = [{"deckName": prev, "modelName": CLOZE,
                  "fields": {"Text": c["text"], "Extra": c.get("extra", ""), "Source": c.get("source", "")},
                  "tags": c.get("tags", []), "options": {"allowDuplicate": True}} for c in gaps]
        added = sum(1 for x in invoke("addNotes", notes=notes) if x)
        print(f"{'':24}   merged final={len(reviewed)+len(gaps):3} | +{added} gap cards → preview")
    else:
        print(f"{'':24}   merged final={len(reviewed)+len(gaps):3} (merge-only)")
print(f"\nTOTAL gap rejects across all decks: {grand_rej}")
