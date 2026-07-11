#!/usr/bin/env python3
"""Audit a Stage-1 fact DB: field completeness, real image, slide range, non-atomic smell.

Usage: audit_facts.py "<Week X/Subject/NN-deck>" <n_slides>
Reads <deck>/out/facts.jsonl; images expected under <deck>/out/slides/.
Part of the regen pipeline — see classes/ISF/REGEN-PIPELINE.md.
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)  # classes/ISF
deck, nsl = sys.argv[1], int(sys.argv[2])
f = f"{BASE}/{deck}/out/facts.jsonl"
imgs = set(os.listdir(f"{BASE}/{deck}/out/slides"))
rows = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
REQ = ("id", "slide", "image", "fact", "source_type", "source_exact")
bad_field = [r.get("id") for r in rows if not all(k in r and r[k] not in ("", None) for k in REQ)]
bad_img = [r["id"] for r in rows if r.get("image") not in imgs]
bad_slide = [r["id"] for r in rows if not (isinstance(r.get("slide"), int) and 1 <= r["slide"] <= nsl)]
# non-atomic smell: a semicolon, or a contrast/reason connective joining two clauses
# (.get so a row missing "fact" — already reported in bad_field — doesn't crash the audit)
smell = [r for r in rows if re.search(r";|\bwhile\b|\bwhereas\b|\bbut\b", r.get("fact", ""))]
print(f"{deck.split('/')[-1]:34} facts={len(rows):3} | fields:{'ok' if not bad_field else bad_field} "
      f"img:{'ok' if not bad_img else bad_img} slide:{'ok' if not bad_slide else bad_slide} | smell={len(smell)}")
for r in smell:
    print(f"     ~ {r['id']}: {r['fact']}")
