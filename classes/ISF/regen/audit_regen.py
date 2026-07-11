#!/usr/bin/env python3
"""Audit a Stage-2/4 regen card deck: mold pass, hints, and Extra provenance (real image + source).

Usage: audit_regen.py "<Week X/Subject/NN-deck>" [cards_filename]
  default cards_filename = cards.regen.jsonl (use cards.gaps2.jsonl / cards.reviewed.jsonl / cards.final.jsonl too)
Gate: strict_shape mold (0 rejects), every non-list cloze has a ::hint, Extra has a real <img> and a Source.
Part of the regen pipeline — see classes/ISF/REGEN-PIPELINE.md.
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)  # classes/ISF
sys.path.insert(0, BASE)
import strict_shape as s
from lint_cards import _is_list
deck = sys.argv[1]
fname = sys.argv[2] if len(sys.argv) > 2 else "cards.regen.jsonl"
imgs = set(os.listdir(f"{BASE}/{deck}/out/slides"))
rows = [json.loads(l) for l in open(f"{BASE}/{deck}/out/{fname}", encoding="utf-8") if l.strip()]
rej, softmiss, no_img, bad_img, no_src = [], [], [], [], []
for c in rows:
    r = s.classify_card(c)
    if not r.ok: rej.append((c["id"], r.reasons))
    if "MISSING_HINT" in r.soft and not _is_list(c["text"]): softmiss.append(c["id"])
    m = re.search(r'<img src="([^"]+)"', c.get("extra", ""))
    # a gap card sourced only from objective/Junqueira/transcript legitimately has NO image
    if m and m.group(1) not in imgs: bad_img.append((c["id"], m.group(1)))
    if "ource:" not in c.get("extra", ""): no_src.append(c["id"])
name = deck.split("/")[-1]
ok = not (rej or bad_img or no_src or softmiss)
print(f"{name:34} {len(rows):3} cards | {'✓ CLEAN' if ok else '✗'}"
      f"{'' if not rej else ' rej='+str(rej[:3])}"
      f"{'' if not bad_img else ' bad-img='+str(bad_img[:3])}"
      f"{'' if not no_src else ' no-src='+str(no_src[:3])}"
      f"{'' if not softmiss else ' no-hint='+str(len(softmiss))}")
