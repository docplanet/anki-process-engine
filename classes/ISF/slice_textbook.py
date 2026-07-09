#!/usr/bin/env python3
"""Slice the objective-cited page ranges out of a central textbook PDF into a subject's sources/.

The learning-objectives PDF is the index: each week's objectives cite exact textbook pages
(e.g. Marks 6e "pp 3-8, 475-482"). Rather than dump/grep a whole book, slice just those
pages so the generator/reviewer reads bounded, precisely-assigned text to ground on.

Two modes:
  --pdf-ranges  slice by ACTUAL PDF page numbers (robust; use for reflowed PDFs whose
                printed page numbers don't extract or don't match the objectives' edition).
                Find chapter bounds by content once, store them as pdf_ranges in course-map.
  --ranges      slice by PRINTED page numbers + --offset (offset = pdf_page - printed_page).
                Only reliable when the PDF is one-page-per-printed-page.

Optionally pass --label NAME to name outputs textbook-<book>-<label>.txt.

Usage:
  python slice_textbook.py BOOK.pdf OUTDIR --pdf-ranges 21-68 171-223 --label ch1 ch5-func-groups
  python slice_textbook.py BOOK.pdf OUTDIR --offset 18 --ranges 3-8 67-70
Needs: pdftotext (poppler)  —  install:  brew install poppler
"""
import argparse, os, re, shutil, subprocess, sys


def parse_range(r):
    m = re.match(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*$", r)
    if not m:
        sys.exit(f"bad range {r!r} — use '3-8' or '5'")
    a = int(m.group(1))
    b = int(m.group(2)) if m.group(2) else a
    return a, b


def main():
    ap = argparse.ArgumentParser(description="Slice textbook page ranges into a sources/ dir.")
    ap.add_argument("book", help="path to the textbook PDF")
    ap.add_argument("outdir", help="destination sources/ dir")
    ap.add_argument("--offset", type=int, default=0, help="pdf_page - printed_page (for --ranges)")
    ap.add_argument("--ranges", nargs="+", help="PRINTED page ranges, e.g. 3-8 475-482")
    ap.add_argument("--pdf-ranges", nargs="+", dest="pdf_ranges", help="ACTUAL PDF page ranges, e.g. 21-68")
    ap.add_argument("--label", nargs="+", help="optional label per range (else named by page span)")
    a = ap.parse_args()
    if not shutil.which("pdftotext"):
        sys.exit("pdftotext not found — install poppler (e.g. `brew install poppler`).")
    if not os.path.exists(a.book):
        sys.exit(f"textbook not found: {a.book}")
    if not a.ranges and not a.pdf_ranges:
        sys.exit("give --pdf-ranges (preferred) or --ranges + --offset")
    os.makedirs(a.outdir, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", os.path.splitext(os.path.basename(a.book))[0].lower()).strip("-")
    direct = bool(a.pdf_ranges)
    ranges = a.pdf_ranges if direct else a.ranges
    labels = a.label or []
    for i, r in enumerate(ranges):
        p1, p2 = parse_range(r)
        f, l = (p1, p2) if direct else (p1 + a.offset, p2 + a.offset)
        tag = labels[i] if i < len(labels) else (f"pdf{p1}-{p2}" if direct else f"pp{p1}-{p2}")
        out = os.path.join(a.outdir, f"textbook-{slug}-{tag}.txt")
        subprocess.run(["pdftotext", "-f", str(f), "-l", str(l), a.book, out], check=True)
        kind = "pdf" if direct else f"printed (pdf {f}-{l})"
        print(f"{kind} pp {p1}-{p2}  ->  {os.path.basename(out)}")
    print(f"\n{len(ranges)} range(s) sliced into {a.outdir}/")


if __name__ == "__main__":
    main()
