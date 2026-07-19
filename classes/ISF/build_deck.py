#!/usr/bin/env python3
"""build_deck — the one driver for building an Anki deck from lecture material.

It automates ONLY the deterministic steps. Scope, authoring, and review judgment are
AGENT work — no script writes cards. See classes/ISF/okf/process.md for the full procedure and
the manual fallback for every step below (each subcommand is independent; if one fails, do that
step by hand and continue).

    build_deck.py slides  <slides.pdf|.ppt> <out> <slug>   render slides -> JPEGs + slides.jsonl
    build_deck.py sources <deck_dir>                      extract PDFs/transcript -> out/sources/
    build_deck.py gate    <cards.jsonl>                   strict_shape mold gate (must be N/N)
    (see also check_cards.py — mechanical review: verbatim quotes, hints, media)
    build_deck.py dedupe  <cards.jsonl>                   content_check near-dup report
    build_deck.py media   <out_dir>                       push slide images into Anki media
    build_deck.py insert  <cards.jsonl> --deck "<name>"   add notes via AnkiConnect
    build_deck.py corpus  [--out <path>]                  pull the style reference corpus
    build_deck.py sync                                    AnkiConnect sync

Anki steps need Anki running with the AnkiConnect add-on (http://127.0.0.1:8765).
Slide rendering needs poppler (pdftoppm, pdftotext, pdfinfo); .ppt/.pptx also needs LibreOffice.
"""
import argparse, datetime, glob, json, os, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ANKI = "http://127.0.0.1:8765"
MODEL = "Custom Cloze"          # fields: Text, Extra, Source


def _log(out_dir, step, detail):
    """Record what ran into out/.build_deck.log so a later session can see the state of out/."""
    try:
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(os.path.join(out_dir, ".build_deck.log"), "a", encoding="utf-8") as f:
            f.write(f"{stamp}\t{step}\t{detail}\n")
    except OSError:
        pass                                     # logging must never break a build step


# ── AnkiConnect ───────────────────────────────────────────────────────────────
def invoke(action, **params):
    body = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKI, body, {"Content-Type": "application/json"})
    try:
        res = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except Exception as e:
        sys.exit(f"AnkiConnect unreachable at {ANKI} ({e}).\n"
                 "Open Anki with the AnkiConnect add-on, or do this step by hand "
                 "(see okf/process.md).")
    if res.get("error"):
        raise RuntimeError(f"{action}: {res['error']}")
    return res["result"]


# ── slides ────────────────────────────────────────────────────────────────────
def _as_pdf(path, out_dir):
    """Slide decks often ship as .ppt/.pptx — convert to PDF via LibreOffice first."""
    if path.lower().endswith(".pdf"):
        return path
    if not path.lower().endswith((".ppt", ".pptx", ".key", ".odp")):
        sys.exit(f"don't know how to render {path!r} — give a .pdf or .ppt/.pptx")
    os.makedirs(out_dir, exist_ok=True)
    print(f"converting {os.path.basename(path)} -> PDF (LibreOffice)…")
    r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", out_dir, path],
                       capture_output=True, text=True)
    pdf = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + ".pdf")
    if r.returncode != 0 or not os.path.exists(pdf):
        sys.exit(f"LibreOffice conversion failed ({r.returncode}). Install it "
                 "(`brew install --cask libreoffice`) or convert to PDF by hand, then re-run.")
    return pdf


def cmd_slides(a):
    """Render each slide to a JPEG and emit slides.jsonl (slide, image, text).

    Accepts a PDF, or a .ppt/.pptx which is converted to PDF first.
    """
    slidedir = os.path.join(a.out_dir, "slides")
    os.makedirs(slidedir, exist_ok=True)
    a.pdf = _as_pdf(a.pdf, a.out_dir)
    info = subprocess.run(["pdfinfo", a.pdf], capture_output=True, text=True, check=True).stdout
    npages = next((int(l.split(":")[1]) for l in info.splitlines() if l.startswith("Pages:")), None)
    if npages is None:
        sys.exit(f"pdfinfo produced no 'Pages:' line for {a.pdf!r} — is it a valid PDF?")
    pad = len(str(npages))                       # mirror pdftoppm's auto-pad width
    root = os.path.join(slidedir, f"isf-{a.slug}-slide")
    subprocess.run(["pdftoppm", "-jpeg", "-r", "150", a.pdf, root], check=True)
    text = subprocess.run(["pdftotext", "-layout", a.pdf, "-"],
                          capture_output=True, text=True, check=True).stdout
    pages = text.split("\f")
    out = os.path.join(a.out_dir, "slides.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for i in range(1, npages + 1):
            f.write(json.dumps({"slide": i,
                                "image": f"isf-{a.slug}-slide-{i:0{pad}d}.jpg",
                                "text": pages[i - 1].strip() if i - 1 < len(pages) else ""},
                               ensure_ascii=False) + "\n")
    _log(a.out_dir, "slides", f"{npages} slides from {os.path.basename(a.pdf)} (slug={a.slug})")
    print(f"{a.slug}: {npages} slides -> {slidedir}/ + {out}")


# ── sources ───────────────────────────────────────────────────────────────────
def cmd_sources(a):
    """Extract every PDF and transcript in the deck folder to plain text under out/sources/.

    A recording often ships as .txt + .vtt + .srt with the SAME basename; they'd collide on
    output, so keep only the cleanest one per basename (.txt > .vtt > .srt).
    """
    dest = os.path.join(a.deck_dir, "out", "sources")
    os.makedirs(dest, exist_ok=True)
    PREF = {".txt": 0, ".vtt": 1, ".srt": 2}          # lower = preferred
    SLIDES = (".ppt", ".pptx", ".key", ".odp")
    chosen, skipped, ignored = {}, [], []
    for path in sorted(glob.glob(os.path.join(a.deck_dir, "*"))):
        base, ext = os.path.splitext(os.path.basename(path))
        ext = ext.lower()
        if os.path.isdir(path):
            continue
        if ext in SLIDES:
            # A slide deck shipped as .ppt/.pptx is still source text. Converting it here is what
            # makes `out/sources/` complete — skipping it silently once left a whole lecture's
            # slides unextracted, and four reviewers verified cards against half the material.
            chosen[base] = (_as_pdf(path, os.path.join(a.deck_dir, "out")), ".pdf")
        elif ext == ".pdf":
            chosen[base] = (path, ext)                 # PDFs never collide with transcripts here
        elif ext in PREF:
            cur = chosen.get(base)
            if cur is None or PREF[ext] < PREF.get(cur[1], 99):
                if cur:
                    skipped.append(os.path.basename(cur[0]))
                chosen[base] = (path, ext)
            else:
                skipped.append(os.path.basename(path))
        else:
            ignored.append(os.path.basename(path))     # never drop a file without saying so

    n = 0
    for base, (path, ext) in sorted(chosen.items()):
        if ext == ".pdf":
            txt = subprocess.run(["pdftotext", "-layout", path, "-"],
                                 capture_output=True, text=True).stdout
        else:
            txt = open(path, encoding="utf-8", errors="replace").read()
        open(os.path.join(dest, base + ".txt"), "w", encoding="utf-8").write(txt)
        print(f"  {os.path.basename(path)} -> out/sources/{base}.txt ({len(txt.split())} words)")
        n += 1
    for s in skipped:
        print(f"  (skipped {s} — same basename, cleaner format kept)")
    for s in ignored:
        print(f"  !! NOT EXTRACTED: {s} — unknown type. Extract it by hand; a reviewer reading "
              f"out/sources/ will not see this material.")
    _log(os.path.join(a.deck_dir, "out"), "sources",
         f"{n} file(s) -> out/sources/" + (f"; NOT EXTRACTED: {', '.join(ignored)}" if ignored else ""))
    print(f"{n} source file(s) extracted to {dest}")
    if not n:
        print("  (nothing found — drop the slides PDF, objectives PDF and transcript in the folder)")


# ── gate / dedupe ─────────────────────────────────────────────────────────────
def _run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args])
    return r.returncode


def cmd_gate(a):
    """The mold. Must print N/N conforming. Recognition/attribute cards are exempt."""
    sys.exit(_run("strict_shape.py", a.cards))


def cmd_dedupe(a):
    sys.exit(_run("content_check.py", a.cards))


# ── media ─────────────────────────────────────────────────────────────────────
def cmd_media(a):
    """Push rendered slide images into Anki's media collection (idempotent)."""
    imgs = sorted(glob.glob(os.path.join(a.out_dir, "slides", "*.jpg")))
    if not imgs:
        sys.exit(f"no JPEGs under {a.out_dir}/slides — run `build_deck.py slides` first")
    for p in imgs:
        invoke("storeMediaFile", filename=os.path.basename(p), path=os.path.abspath(p))
    print(f"stored {len(imgs)} image(s) in Anki media")


# ── insert ────────────────────────────────────────────────────────────────────
def cmd_insert(a):
    """Add notes from JSONL. Each line: {text, extra, source, tags[]} (id/type optional)."""
    cards = [json.loads(l) for l in open(a.cards, encoding="utf-8") if l.strip()]
    if not cards:
        sys.exit(f"{a.cards} is empty")
    if MODEL not in set(invoke("modelNames")):
        sys.exit(f"note type {MODEL!r} not found in this collection")
    notes = [{"deckName": a.deck, "modelName": MODEL,
              "fields": {"Text": c.get("text", ""), "Extra": c.get("extra", ""),
                         "Source": c.get("source", "")},
              "tags": c.get("tags", [])} for c in cards]
    if a.dry_run:                                # must not touch the collection at all
        exists = a.deck in set(invoke("deckNames"))
        print(f"DRY RUN — would add {len(notes)} note(s) to {a.deck!r}"
              f"{'' if exists else ' (deck would be created)'}")
        return
    if a.deck not in set(invoke("deckNames")):
        invoke("createDeck", deck=a.deck)
    # addNotes raises if EVERY note fails, so add one at a time and report per-card
    # Keep (note_id, card) PAIRS. Zipping new_ids against cards afterwards misaligns as soon as
    # any card is a duplicate or fails — it once suspended an unrelated note and printed success.
    added, dupes, failed, new_pairs = 0, [], [], []
    for i, note in enumerate(notes):
        ref = cards[i].get("id", i)
        try:
            r = invoke("addNote", note=note)
            added += 1 if r else 0
            if r:
                new_pairs.append((r, cards[i]))
            else:
                failed.append(ref)
        except RuntimeError as e:
            (dupes if "duplicate" in str(e).lower() else failed).append(ref)
    print(f"added {added}/{len(notes)} note(s) to {a.deck!r}")
    _log(os.path.dirname(os.path.abspath(a.cards)), "insert",
         f"{added} added, {len(dupes)} dupes, {len(failed)} failed -> {a.deck}")
    if a.suspend_flagged and new_pairs:
        # yield.md/no-duplicate.md require flag::* cards to enter SUSPENDED. Also suspend wrong-*:
        # a card the owner flagged as defective must never ship live (one such card was suspended
        # only because a human did it by hand, and a rebuild would have shipped it).
        flagged = [nid for nid, c in new_pairs
                   if any(t.startswith("flag::") or t.startswith("wrong-")
                          for t in c.get("tags", []))]
        if flagged:
            cids = invoke("findCards", query=" OR ".join(f"nid:{n}" for n in flagged))
            invoke("suspend", cards=cids)
            print(f"  suspended {len(flagged)} note(s) tagged flag::* "
                  f"({len(cids)} card(s)) — unsuspend in Anki when you want them")
    if a.tag_reviewed and new_pairs:
        # Tag EXACTLY the notes this call created. Never tag by a negative query like
        # `-tag:src::reviewed` — that sweeps in every older untagged card in the deck and marks
        # unreviewed work as reviewed. That has happened twice; the second time was hours after
        # documenting the first. Hence a flag that carries the real id list instead of a doc note.
        invoke("addTags", notes=[nid for nid, _ in new_pairs], tags="src::reviewed")
        print(f"  tagged {len(new_pairs)} newly added note(s) src::reviewed")
    if dupes:
        print(f"  {len(dupes)} skipped as duplicates (already in the collection): "
              f"{', '.join(map(str, dupes[:8]))}{' …' if len(dupes) > 8 else ''}")
        print("  NOTE: Anki dedupes on the first field. To relocate existing notes, move them in "
              "Anki (Browse → Change Deck) — re-inserting is blocked by design.")
    for ref in failed:
        print(f"  FAILED: {ref}")


CORPUS_DECK = "ISF::Test 2::Biochemistry::Amino Acid Structures"
CORPUS_OUT = os.path.join(HERE, "reference", "style_corpus.jsonl")


def cmd_corpus(a):
    """Pull the owner-reviewed style corpus out of Anki.

    okf/style.md makes these cards the authority for every shape question, so they must be
    re-pullable on demand — they previously lived only in /tmp, one reboot from gone.
    """
    out = a.out or CORPUS_OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    notes = invoke("notesInfo", notes=invoke("findNotes", query=f'deck:"{a.deck}"'))
    if not notes:
        sys.exit(f"no notes in {a.deck!r} — is Anki open and the deck name right?")
    # EXCLUDE cards the owner flagged as defective. review-checklist.md makes this corpus the
    # "acceptable by definition" bar, so a wrong-* card in it teaches a reviewer to stay silent
    # about the very defect the owner complained of.
    rejected = [n for n in notes if any(t.startswith("wrong-") for t in n["tags"])]
    notes = [n for n in notes if n not in rejected]
    if rejected:
        print(f"  excluded {len(rejected)} card(s) tagged wrong-* — the owner flagged them as "
              f"defective, so they are not part of the style bar")
    with open(out, "w", encoding="utf-8") as f:
        for n in notes:
            f.write(json.dumps({"note_id": n["noteId"], "model": n["modelName"],
                                "fields": {k: v["value"] for k, v in n["fields"].items()},
                                "tags": n["tags"]}, ensure_ascii=False) + "\n")
    print(f"{len(notes)} reference cards -> {out}")


def cmd_sync(a):
    invoke("sync")
    print("synced")


# ── cli ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("slides", help="render slide PDF/.ppt -> JPEGs + slides.jsonl")
    p.add_argument("pdf"); p.add_argument("out_dir"); p.add_argument("slug")
    p.set_defaults(fn=cmd_slides)

    p = sub.add_parser("sources", help="extract PDFs/transcripts -> out/sources/*.txt")
    p.add_argument("deck_dir"); p.set_defaults(fn=cmd_sources)

    p = sub.add_parser("gate", help="strict_shape mold gate")
    p.add_argument("cards"); p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("dedupe", help="content_check near-duplicate report")
    p.add_argument("cards"); p.set_defaults(fn=cmd_dedupe)

    p = sub.add_parser("media", help="push slide images into Anki media")
    p.add_argument("out_dir"); p.set_defaults(fn=cmd_media)

    p = sub.add_parser("insert", help="add notes via AnkiConnect")
    p.add_argument("cards"); p.add_argument("--deck", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--suspend-flagged", action="store_true",
                   help="suspend any note tagged flag::* (low-yield / beyond-scope) as required by "
                        "okf/rules/yield.md — the owner unsuspends what they want")
    p.add_argument("--tag-reviewed", action="store_true",
                   help="tag exactly the notes this call adds src::reviewed (use only when the "
                        "cards have actually been through review)")
    p.set_defaults(fn=cmd_insert)

    p = sub.add_parser("corpus", help="pull the style reference corpus from Anki")
    p.add_argument("--deck", default=CORPUS_DECK)
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_corpus)

    p = sub.add_parser("sync", help="AnkiConnect sync")
    p.set_defaults(fn=cmd_sync)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
