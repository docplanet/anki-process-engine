#!/usr/bin/env python3
"""Prep ONE lecture folder end-to-end into the run-ready convention.

Drop a lecture's raw materials into a folder (slides .pptx/.pdf, a recording .vtt/.txt, the learning
objectives .pdf/.docx, any textbook chapter .pdf), then run this. It:
  1. organizes originals into  raw/
  2. converts .pptx -> .pdf (soffice) and .docx -> .txt (textutil)
  3. extracts every source to  sources/*.txt   (reusing extract_sources.py: pdftotext + VTT cleaner)
  4. copies the slide deck to   slides.pdf      (the anchor the engine renders per page)
  5. scaffolds a                job.yaml        (cards_dir: out) with role-guessed sources

Result — the clean lecture layout the pipeline expects:
    <lecture>/ { slides.pdf, job.yaml, raw/, sources/, out/ }

Usage:
    python prep_lecture.py "<lecture-dir>" --deck "ISF::Week 2::Biochemistry (Engine)::Carbohydrate" \
                           --subject biochem [--slides "<deck filename>"]

Needs: poppler (pdftotext/pdftoppm), and for conversion: soffice (LibreOffice) / textutil (macOS).
"""
import argparse, glob, os, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_sources as ex  # reuse slug/guess_role/clean_vtt/extract  # noqa: E402

RAW_EXTS = (".pdf", ".pptx", ".vtt", ".txt", ".m4a", ".mp4", ".docx", ".doc", ".rtf")


def _soffice():
    return shutil.which("soffice") or (
        "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.exists("/Applications/LibreOffice.app/Contents/MacOS/soffice") else None)


def pptx_to_pdf(pptx, out_dir):
    """.pptx -> .pdf via LibreOffice headless. Returns the pdf path (or None)."""
    so = _soffice()
    if not so:
        print(f"  !! soffice not found — cannot convert {os.path.basename(pptx)}; "
              f"export it to PDF manually (`brew install --cask libreoffice` to automate)")
        return None
    subprocess.run([so, "--headless", "--convert-to", "pdf", "--outdir", out_dir, pptx],
                   check=True, capture_output=True)
    pdf = os.path.join(out_dir, os.path.splitext(os.path.basename(pptx))[0] + ".pdf")
    return pdf if os.path.exists(pdf) else None


def docx_to_txt(docx, out_txt):
    """.docx -> .txt via macOS textutil. Returns out_txt (or None)."""
    if not shutil.which("textutil"):
        print(f"  !! textutil not found (macOS only) — convert {os.path.basename(docx)} to .txt manually")
        return None
    subprocess.run(["textutil", "-convert", "txt", "-output", out_txt, docx], check=True)
    return out_txt if os.path.exists(out_txt) else None


def organize_raw(lec):
    """Move loose originals at the lecture root into raw/. Returns the raw/ dir."""
    raw = os.path.join(lec, "raw")
    os.makedirs(raw, exist_ok=True)
    for f in os.listdir(lec):
        p = os.path.join(lec, f)
        if os.path.isfile(p) and os.path.splitext(f)[1].lower() in RAW_EXTS and f != "slides.pdf":
            shutil.move(p, os.path.join(raw, f))
    return raw


def pick_slides(raw, override):
    """Choose the anchor slide-deck PDF: --slides override, else a converted pptx, else role=slides."""
    if override:
        cand = os.path.join(raw, override)
        return cand if os.path.exists(cand) else None
    pdfs = sorted(glob.glob(os.path.join(raw, "*.pdf")))
    # prefer a PDF whose sibling .pptx exists (i.e. the converted slide deck)
    for p in pdfs:
        if os.path.exists(os.path.splitext(p)[0] + ".pptx"):
            return p
    slide_like = [p for p in pdfs if ex.guess_role(os.path.basename(p)) == "slides"]
    return (slide_like or pdfs or [None])[0]


def scaffold_job(lec, deck, subject, sources_by_role):
    lines = ["run:", f'  deck: "{deck}"', f"  subject: {subject}", "  cards_dir: out", "",
             "sources:", "  - { file: slides.pdf, role: slides, anchor: true, extract: pdf_pages }"]
    for role in ("transcript", "objectives", "textbook"):
        for f in sources_by_role.get(role, []):
            lines.append(f"  - {{ file: sources/{f}, role: {role}, extract: text }}")
    lines += ["", "anchor:", "  unit: slide", "  source_role: slides", "",
              "yield:", "  max_cards_per_unit: 4", "  default: 1", "  allow_zero: true", "",
              "gates:", "  spec: consensus", "  accuracy: hard", "  style: hard"]
    open(os.path.join(lec, "job.yaml"), "w").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Prep a lecture folder into the run-ready convention")
    ap.add_argument("lecture_dir")
    ap.add_argument("--deck", required=True, help='Anki deck name, e.g. "ISF::Week 2::Biochemistry (Engine)::Carbohydrate"')
    ap.add_argument("--subject", default="", help="subject tag (biochem/histology/embryology)")
    ap.add_argument("--slides", help="raw slide-deck filename to use as the anchor (else auto-detected)")
    a = ap.parse_args()
    lec = os.path.abspath(a.lecture_dir)
    if not os.path.isdir(lec):
        sys.exit(f"not a directory: {lec}")
    if not shutil.which("pdftotext"):
        sys.exit("pdftotext not found — install poppler (`brew install poppler`).")

    raw = organize_raw(lec)
    src_dir = os.path.join(lec, "sources"); os.makedirs(src_dir, exist_ok=True)
    os.makedirs(os.path.join(lec, "out"), exist_ok=True)

    # 1) convert pptx -> pdf (into raw/)
    for pptx in sorted(glob.glob(os.path.join(raw, "*.pptx"))):
        pdf = pptx_to_pdf(pptx, raw)
        if pdf:
            print(f"  pptx -> pdf : {os.path.basename(pdf)}")
    # 2) convert docx -> sources/*.txt (role-guessed via filename)
    for docx in sorted(glob.glob(os.path.join(raw, "*.docx"))):
        out = os.path.join(src_dir, ex.slug(os.path.splitext(os.path.basename(docx))[0]) + ".txt")
        if docx_to_txt(docx, out):
            print(f"  docx -> txt : {os.path.basename(out)}")

    # 3) extract every raw pdf/vtt/txt -> sources/ (reuse extract_sources)
    sources_by_role = {}
    for src in sorted(glob.glob(os.path.join(raw, "*.pdf")) + glob.glob(os.path.join(raw, "*.vtt")) + glob.glob(os.path.join(raw, "*.txt"))):
        base = os.path.basename(src)
        out = os.path.join(src_dir, ex.slug(os.path.splitext(base)[0]) + ".txt")
        ex.extract(src, out)
        sources_by_role.setdefault(ex.guess_role(base), []).append(os.path.basename(out))

    # 4) slides anchor -> slides.pdf at the lecture root
    slides = pick_slides(raw, a.slides)
    if not slides:
        sys.exit("no slide-deck PDF found — pass --slides <file> or add the deck to the folder")
    shutil.copy2(slides, os.path.join(lec, "slides.pdf"))
    print(f"  slides.pdf  : {os.path.basename(slides)}")

    # 5) scaffold job.yaml (the slide-text source is redundant with the PDF anchor, so it's omitted)
    scaffold_job(lec, a.deck, a.subject, sources_by_role)
    print(f"\nprepped {os.path.relpath(lec)} -> job.yaml written")
    print("  review sources/_manifest.txt + job.yaml, then run the regen pipeline (see classes/ISF/REGEN-PIPELINE.md)")


if __name__ == "__main__":
    main()
