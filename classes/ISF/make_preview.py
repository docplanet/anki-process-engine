#!/usr/bin/env python3
"""Render card JSONL files to readable markdown previews (the human-review surface).

Reveals cloze answers, converts <b>/<i> to markdown bold/italic, drops hints, and
inlines images. Run after editing cards so the previews never go stale.

Usage:  python make_preview.py "Week 1/Histology/cards"
Writes: <stem>-preview.md next to each <stem>.jsonl in the given dir.
"""
import json, re, glob, os, sys


def render(text):
    text = re.sub(r"(\{\{c\d+::[^{}]*?)::[^{}]*?\}\}", r"\1}}", text)  # drop ::hints
    text = re.sub(r"\{\{c\d+::(.*?)\}\}", r"\1", text)                 # reveal cloze answers
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text)
    # keep <u>…</u> as-is — markdown renders raw <u>, so underline (the "facet" role) stays visible
    return text.replace("<br>", "  \n   ")


def main(cards_dir):
    for path in sorted(glob.glob(os.path.join(cards_dir, "*.jsonl"))):
        stem = os.path.splitext(os.path.basename(path))[0]
        rows, n = [], 0
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            c = json.loads(line); n += 1
            if c["type"] == "cloze":
                rows.append(f"{n}. {render(c['text'])}")
            elif c["type"] == "basic":
                rows.append(f"{n}. **Q:** {render(c['front'])}  \n   **A:** {render(c['back'])}")
            elif c["type"] == "image":
                rows.append(f"{n}. {render(c['front'])}  \n   ![]({c['image']})  \n   **A:** {render(c['back'])}")
            if c.get("extra"):
                rows[-1] += f"  \n   > extra: {render(c['extra'])}"
        out = os.path.join(cards_dir, f"{stem}-preview.md")
        header = (f"# {stem} — preview ({n} cards)\n\n"
                  f"*Auto-generated from {stem}.jsonl by make_preview.py — do not hand-edit. "
                  f"Cloze answers shown; **bold** = subject term, *italic* = answer/description.*\n\n")
        open(out, "w", encoding="utf-8").write(header + "\n\n".join(rows) + "\n")
        print(f"wrote {os.path.basename(out)} ({n} cards)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
