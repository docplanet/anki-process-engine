#!/usr/bin/env python3
"""Stage 0: render a lecture slide PDF to per-slide JPEGs + a slides.jsonl context DB.

    build_slides_db.py <slides.pdf> <out_dir> <deck-slug>

Emits <out_dir>/slides/isf-<deck-slug>-slide-NN.jpg (one per page) and <out_dir>/slides.jsonl with one
row per slide: {"slide": <int>, "image": "isf-<slug>-slide-NN.jpg", "text": "<page text>"}.

NOTE: this file is a faithful RECONSTRUCTION (the session original lived in a since-wiped scratchpad).
The image-name/zero-pad convention and jsonl schema match the surviving out/ artifacts exactly:
pdftoppm zero-pads the page number to the width of the max page, so a >99-slide deck (histology, 108)
yields 3-digit names (isf-...-slide-004), and a <=99-slide deck yields 2-digit (isf-...-slide-04).
Downstream (facts extraction, cards, audit_regen) depends on that exact naming.
See classes/ISF/REGEN-PIPELINE.md.
"""
import json, os, subprocess, sys

def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    pdf, out_dir, slug = sys.argv[1], sys.argv[2], sys.argv[3]
    slidedir = os.path.join(out_dir, "slides")
    os.makedirs(slidedir, exist_ok=True)
    # page count (pdfinfo from poppler)
    info = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True, check=True).stdout
    npages = next((int(l.split(":")[1]) for l in info.splitlines() if l.startswith("Pages:")), None)
    if npages is None:
        sys.exit(f"pdfinfo produced no 'Pages:' line for {pdf!r} — is it a valid PDF?")
    pad = len(str(npages))  # mirror pdftoppm's auto-pad width
    # render each page to JPEG: pdftoppm writes <root>-NN.jpg with its own pad width
    root = os.path.join(slidedir, f"isf-{slug}-slide")
    subprocess.run(["pdftoppm", "-jpeg", "-r", "150", pdf, root], check=True)
    # page-aligned text, split on form-feed
    text = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    pages = text.split("\f")
    rows = []
    for i in range(1, npages + 1):
        img = f"isf-{slug}-slide-{i:0{pad}d}.jpg"
        page_text = pages[i - 1].strip() if i - 1 < len(pages) else ""
        rows.append({"slide": i, "image": img, "text": page_text})
    with open(os.path.join(out_dir, "slides.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{slug}: {npages} slides → {slidedir}/isf-{slug}-slide-{'N'*pad}.jpg + slides.jsonl")

if __name__ == "__main__":
    main()
