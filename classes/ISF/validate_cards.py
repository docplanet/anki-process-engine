#!/usr/bin/env python3
"""Validate a folder of Anki card JSONL files before building.

Checks every *.jsonl in the given dir:
  - line parses as JSON
  - type in {cloze, basic, image} with its required fields present
  - cloze: balanced {{ }}, at least one {{c#::...}}, numbering starts at c1
  - image: referenced file exists under the cards dir
  - tags: non-empty list, no spaces inside a tag (Anki splits tags on spaces)
  - source present
Reports card counts, warns on orphan media, exits non-zero on any error.

Usage:  python validate_cards.py "Week 1/Histology/cards"
"""
import argparse, glob, json, os, re, sys

REQUIRED = {"cloze": ["text"], "basic": ["front", "back"],
            "image": ["front", "image", "back"]}
CLOZE_RE = re.compile(r"\{\{c(\d+)::.+?\}\}", re.S)


def validate(cards_dir):
    errors, warnings, counts, referenced = [], [], {"cloze": 0, "basic": 0, "image": 0}, set()
    jsonls = sorted(glob.glob(os.path.join(cards_dir, "*.jsonl")))
    if not jsonls:
        print(f"no .jsonl files in {cards_dir}")
        return 1
    for path in jsonls:
        fn = os.path.basename(path)
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            loc = f"{fn}:{i}"
            try:
                c = json.loads(line)
            except Exception as e:
                errors.append(f"{loc} invalid JSON: {e}")
                continue
            t = c.get("type")
            if t not in REQUIRED:
                errors.append(f"{loc} bad/missing type: {t!r}")
                continue
            counts[t] += 1
            if t == "basic":
                warnings.append(f"{loc} basic Q&A card — text facts must be cloze "
                                f"(two-sided for why/how/compare); only image cards may be non-cloze")
            for k in REQUIRED[t]:
                if not c.get(k):
                    errors.append(f"{loc} missing field {k!r}")
            tags = c.get("tags")
            if not isinstance(tags, list) or not tags:
                errors.append(f"{loc} tags missing/empty")
            else:
                for tg in tags:
                    if " " in tg:
                        errors.append(f"{loc} tag has a space (Anki splits on spaces): {tg!r}")
            if not c.get("source"):
                errors.append(f"{loc} missing source")
            if t == "cloze":
                txt = c.get("text", "")
                if txt.count("{{") != txt.count("}}"):
                    errors.append(f"{loc} unbalanced {{{{ }}}}")
                nums = [int(n) for n in CLOZE_RE.findall(txt)]
                if not nums:
                    errors.append(f"{loc} no {{{{c#::...}}}} cloze deletion")
                elif 1 not in nums:
                    errors.append(f"{loc} cloze numbering must start at c1 (found c{min(nums)})")
            if t == "image":
                rel = c.get("image", "")
                if rel:
                    referenced.add(os.path.basename(rel))
                    if not os.path.exists(os.path.join(cards_dir, rel)):
                        errors.append(f"{loc} image not found: {rel}")

    mdir = os.path.join(cards_dir, "media")
    orphans = ([f for f in os.listdir(mdir) if f not in referenced]
               if os.path.isdir(mdir) else [])
    print(f"cards: {sum(counts.values())} ({counts['cloze']} cloze, "
          f"{counts['basic']} basic, {counts['image']} image)")
    if orphans:
        print(f"WARN orphan media (in media/, used by no card): {sorted(orphans)}")
    if warnings:
        print(f"\n{len(warnings)} WARNING(S):")
        for w in warnings:
            print("  " + w)
    if errors:
        print(f"\n{len(errors)} ERROR(S):")
        for e in errors:
            print("  " + e)
        return 1
    print("OK — no errors")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cards", help="cards dir containing *.jsonl (and media/)")
    sys.exit(validate(ap.parse_args().cards))
