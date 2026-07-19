#!/usr/bin/env python3
"""CONTENT / quality detectors — the second axis, above shape (strict_shape.py).

Shape asks "is the card the right FORM?"; this asks "does the card EARN ITS PLACE?".
It is DECK-LEVEL and advisory — it surfaces a worklist of candidates for a human (or a judge
pass) to resolve (merge / cut / trim / fix). It never edits or rejects.

Detectors:
  - near-duplicate pairs   (revealed-text similarity >= RATIO)
  - over-carded subjects   (one <b> subject term appears in >= SUBJECT_REPEAT cards)
  - suspicious extra       (the card's subject term never appears in its own `extra`)

(Dangling trailing facts are NOT a soft detector here — the mold hard-rejects them as
strict_shape TRAILING_FACT, so such a card never ships to reach this content pass.)

Usage:
  python content_check.py "<dir-or-file>"          # human report
  python content_check.py "<...>" --json
"""
import argparse, glob, json, os, re, sys
from difflib import SequenceMatcher

from lint_cards import _strip

RATIO = 0.66            # revealed-text similarity above which two cards are "near-duplicates"
SUBJECT_REPEAT = 3      # a subject term carded this many+ times is a redundancy candidate


def reveal(text):
    """Cloze card text -> the plain revealed sentence (answers shown, hints/markup stripped)."""
    text = re.sub(r"(\{\{c\d+::[^{}]*?)::[^{}]*?\}\}", r"\1}}", text)   # drop ::hints
    text = re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", text)                  # reveal answers
    return _strip(text).lower()


def subject(card):
    m = re.search(r"<b(?:\s[^>]*)?>(.*?)</b>", card.get("text", ""), re.S)
    return _strip(m.group(1)).lower() if m else None


def check(cards):
    revealed = [reveal(c.get("text", "")) for c in cards]
    ids = [c.get("id") for c in cards]

    # near-duplicate pairs — only ACROSS notes (skip intentional split/two-sided siblings,
    # which share the id prefix before "::", e.g. u_ab12::c1 and u_ab12::c1b).
    def base(i):
        return ids[i].split("::")[0] if ids[i] else i
    dup_pairs = []
    for i in range(len(cards)):
        for j in range(i + 1, len(cards)):
            if base(i) == base(j):
                continue
            r = SequenceMatcher(None, revealed[i], revealed[j]).ratio()
            if r >= RATIO:
                dup_pairs.append((round(r, 2), ids[i], ids[j]))
    dup_pairs.sort(reverse=True)

    # over-carded subjects
    subj = {}
    for c in cards:
        s = subject(c)
        if s:
            subj.setdefault(s, []).append(c.get("id"))
    over = {s: v for s, v in subj.items() if len(v) >= SUBJECT_REPEAT}

    # suspicious extra (the subject's head nouns never appear in the card's own answer-side reveal)
    bad_extra = []
    for c in cards:
        s = subject(c)
        if s and c.get("extra"):
            sig = re.findall(r"[a-z]{5,}", s)          # significant subject words (head nouns)
            ex = _strip(c["extra"]).lower()
            if sig and not any(w in ex for w in sig):  # NONE of them appear in the extra
                bad_extra.append(c.get("id"))

    return {"n": len(cards), "dup_pairs": dup_pairs, "over_carded": over,
            "suspicious_extra": bad_extra}


def _iter(target):
    """Yield (filename, cards). FAIL LOUDLY on a target that yields nothing useful.

    Pointed at a deck folder this used to print nothing at all and exit 0, which reads as
    "clean, zero duplicates" — and pointed at <deck>/out it swallowed slides.jsonl and reported
    154 phantom `None ≈ None` pairs. Both failures were silent. Give it a cards.jsonl.
    """
    files = ([target] if target.endswith(".jsonl") else
             sorted(glob.glob(os.path.join(target, "*.jsonl"))))
    if not files:
        sys.exit(f"no .jsonl found at {target!r} — point this at a cards.jsonl, e.g. "
                 f"<deck>/out/cards.jsonl (cards live under out/, not the deck folder)")
    noncard = [f for f in files if os.path.basename(f) in ("slides.jsonl",)]
    if noncard and len(files) > 1:
        print(f"!! ignoring {', '.join(os.path.basename(f) for f in noncard)} — not card files")
        files = [f for f in files if f not in noncard]
    for fn in files:
        cards = [json.loads(l) for l in open(fn, encoding="utf-8") if l.strip()]
        yield fn, cards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    for fn, cards in _iter(target=a.target):
        rep = check(cards)
        if a.json:
            print(json.dumps({"file": fn, **rep}, ensure_ascii=False, indent=2)); continue
        print(f"\n### {os.path.basename(os.path.dirname(os.path.dirname(fn))) or fn}  ({rep['n']} cards)")
        print(f"  near-dup pairs: {len(rep['dup_pairs'])} | over-carded subjects: {len(rep['over_carded'])} "
              f"| suspicious extra: {len(rep['suspicious_extra'])}")
        for r, a_, b_ in rep["dup_pairs"][:6]:
            print(f"    ~dup {r}: {a_}  ≈  {b_}")
        for s, v in list(rep["over_carded"].items())[:6]:
            print(f"    ×{len(v)} '{s}': {', '.join(v)}")


if __name__ == "__main__":
    main()
