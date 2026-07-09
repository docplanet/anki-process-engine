#!/usr/bin/env python3
"""Extract a subject folder's source materials to greppable text for grounded generation + review.

Handles the source shapes Bastyr courses actually ship:
  *.pdf   slides, learning objectives, textbook excerpts   (via pdftotext)
  *.vtt   Zoom auto-caption lecture TRANSCRIPT             (timestamps stripped, rolling dupes collapsed)
  *.txt   plain transcript / chat logs                     (copied through)

Grounding only works when the reviewer reads the ASSIGNED source, not its own training
knowledge. This caches every source as plain text next to the cards and writes
sources/_manifest.txt with a heuristic ROLE guess that the Prep phase refines.

Source hierarchy (see the skill): objectives = checklist, transcript = guiding emphasis
(what the teacher actually said/stressed), slides = structural spine, textbook = precision.

Usage:   python extract_sources.py "Week 1/Biochemistry"
Writes:  <subject>/sources/<slug>.txt for every source, plus <subject>/sources/_manifest.txt
Needs:   pdftotext (poppler)  —  install:  brew install poppler
"""
import glob, os, re, shutil, subprocess, sys


def slug(name):
    s = re.sub(r"&[a-z]+;", " ", name.lower())      # strip html entities (&amp; etc.)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def guess_role(fname):
    n = fname.lower()
    if "objective" in n:
        return "objectives"
    if n.endswith(".vtt") or "transcript" in n or "recording" in n or "caption" in n:
        return "transcript"
    if "chat" in n:
        return "chat"
    if any(k in n for k in ("textbook", "chapter", "junqueira", "lippincott", "marks")):
        return "textbook"
    if "slide" in n or "lecture" in n or n.endswith(".pdf"):
        return "slides"
    return "other"


def clean_vtt(raw):
    """WebVTT -> plain text: drop header/timestamps/cue indices/inline tags, collapse rolling dupes."""
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s == "WEBVTT" or s.startswith("NOTE"):
            continue
        if "-->" in s:                       # timestamp cue line
            continue
        if re.fullmatch(r"\d+", s):          # cue index
            continue
        s = re.sub(r"<[^>]+>", "", s).strip()  # inline tags e.g. <v Speaker>...</v>
        if s:
            lines.append(s)
    out = []                                 # Zoom captions repeat lines as they scroll
    for s in lines:
        if not out or out[-1] != s:
            out.append(s)
    return "\n".join(out) + "\n"


def extract(path, out):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        subprocess.run(["pdftotext", path, out], check=True)
    elif ext == ".vtt":
        raw = open(path, encoding="utf-8", errors="replace").read()
        open(out, "w", encoding="utf-8").write(clean_vtt(raw))
    else:                                    # .txt (transcript/chat) and other text-ish
        raw = open(path, encoding="utf-8", errors="replace").read()
        open(out, "w", encoding="utf-8").write(raw)


def main(subject_dir):
    if not shutil.which("pdftotext"):
        sys.exit("pdftotext not found — install poppler (e.g. `brew install poppler`).")
    srcs = []
    for ext in ("*.pdf", "*.vtt", "*.txt"):
        srcs += glob.glob(os.path.join(subject_dir, ext))
    srcs = sorted(set(srcs))
    if not srcs:
        sys.exit(f"no source files (.pdf/.vtt/.txt) found in {subject_dir}")
    out_dir = os.path.join(subject_dir, "sources")
    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    print(f"{'SOURCE':52}  {'ROLE':11}  ->  TEXT")
    for src in srcs:
        base = os.path.basename(src)
        stem = os.path.splitext(base)[0]
        out = os.path.join(out_dir, slug(stem) + ".txt")
        extract(src, out)
        role = guess_role(base)
        manifest.append(f"{role:11}  sources/{os.path.basename(out)}  <-  {base}")
        print(f"{base[:52]:52}  {role:11}  ->  sources/{os.path.basename(out)}")
    header = ("# Source manifest — heuristic ROLE guesses; the Prep phase refines these.\n"
              "# Hierarchy: objectives=checklist, transcript=guiding emphasis, slides=spine, textbook=precision.\n\n")
    open(os.path.join(out_dir, "_manifest.txt"), "w", encoding="utf-8").write(header + "\n".join(manifest) + "\n")
    print(f"\n{len(srcs)} source(s) extracted to {out_dir}/  (roles in sources/_manifest.txt)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit('usage: python extract_sources.py "<subject-dir>"')
    main(sys.argv[1])
