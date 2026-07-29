#!/usr/bin/env python3
"""build_deck — the one driver for building an Anki deck from lecture material.

`run` is the whole pipeline as four visible steps over ONE status-tracked cards.jsonl:
create -> review -> fix -> re-review. The author and reviewer are constrained claude sub-calls
(the author is read-only; the reviewer gets one tool, to re-check a proposed fix); the driver is
the only writer to Anki.
Nothing is ever deleted — every card keeps a status (draft/approved/needs-fix/cut/held) + a note.
See classes/ISF/okf/process.md for the full procedure.

    build_deck.py run    <deck_dir> --deck "<name>" [--slug S] [--dry-run]   THE pipeline
    build_deck.py commit <cards.jsonl> --deck "<name>" [--approved-only]      write by status to Anki
    build_deck.py slides <slides.pdf|.ppt> <out> <slug>                       render slides -> JPEGs
    build_deck.py sources <deck_dir>                                          extract PDFs/transcript
    build_deck.py media  <out_dir>                                            push slide images to Anki
    build_deck.py corpus [--out <path>]                                       pull the style corpus
    build_deck.py baseline [--root ISF]                                       snapshot every card (diff base)
    build_deck.py wrap    [--dry-run]                                         capture your edits -> corrections
    build_deck.py sync                                                        AnkiConnect sync

Anki steps need Anki running with the AnkiConnect add-on (http://127.0.0.1:8765).
Slide rendering needs poppler (pdftoppm, pdftotext, pdfinfo); .ppt/.pptx also needs LibreOffice.
"""
import argparse, datetime, glob, json, os, re, subprocess, sys, urllib.parse, urllib.request

import reference_cards

CLOZE_RE = re.compile(r"\{\{c\d+::([\s\S]*?)\}\}")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ANKI = "http://127.0.0.1:8765"
MODEL = "Custom Cloze"          # fields: Text, Extra, Source

# The note type is not standard — it must exist before insert, and a fresh Anki won't have it.
# Rather than crash and send the user hunting, the driver CREATES it (see _ensure_model). The
# template renders Extra + Source below the cloze; the CSS is the role colour system the whole
# rulebook assumes: b = subject (purple), i = answer (red), u = facet (teal), cloze = green.
MODEL_DEF = {
    "modelName": MODEL,
    "inOrderFields": ["Text", "Extra", "Source"],
    "isCloze": True,
    "cardTemplates": [{
        "Name": "Cloze",
        "Front": "{{cloze:Text}}",
        "Back": ("{{cloze:Text}}"
                 "{{#Extra}}<div class=\"extra\">{{Extra}}</div>{{/Extra}}"
                 "{{#Source}}<div class=\"src\">{{Source}}</div>{{/Source}}"),
    }],
    "css": (
        ".card { font-family: Menlo, baskerville, sans; font-size: 19px; line-height: 1.5;\n"
        "        max-width: 760px; margin: 0 auto; padding: 8px; text-align: center;\n"
        "        color: #D7DEE9; background-color: #333B45; }\n"
        ".nightMode.card, .night_mode .card { color: #D7DEE9 !important;"
        " background-color: #333B45 !important; }\n"
        ".cloze { font-weight: bold; color: MediumSeaGreen; }\n"
        ".nightMode .cloze, .night_mode .cloze { color: MediumSeaGreen !important; }\n"
        "b { color: #C695C6 !important; }\n"          # subject
        "i { color: IndianRed !important; }\n"        # answer
        "u { color: #5EB3B3 !important; }\n"          # facet
        "img { max-width: 100%; height: auto; border-radius: 6px; margin: 8px 0; }\n"
        "hr { border: none; border-top: 1px solid #555; margin: 14px 0; }\n"
        ".btn-reveal { display: inline-block; background: #3b4654; color: #D7DEE9;\n"
        "              border: 1px solid #51606e; border-radius: 6px; padding: 5px 12px;\n"
        "              font-size: 14px; cursor: pointer; margin: 12px 0 6px; }\n"
        ".btn-reveal:hover { background: #45525f; }\n"
        ".extra { text-align: center; background: #2c343d; border-radius: 8px;"
        " padding: 10px 14px; margin: 6px 0; }\n"
        ".src { color: #839496; font-size: 13px; font-style: italic; margin-top: 10px; }\n"
    ),
}


def _ensure_model():
    """Create the Custom Cloze note type if the collection lacks it (fresh Anki has no such type)."""
    if MODEL in set(invoke("modelNames")):
        return
    invoke("createModel", **MODEL_DEF)
    print(f"created note type {MODEL!r} (fields Text/Extra/Source, role-colour template)")


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
        if ext in (".docx", ".doc", ".rtf"):
            # Objectives often ship as a Word doc (this professor's do). They are the coverage
            # contract, so extract them rather than dropping them into `ignored`. `.rtf` goes
            # through the same textutil call: the Junqueira summaries arrive as .rtf, and without
            # this they printed NOT EXTRACTED and a whole assigned reading went uncarded unless
            # someone read that line and converted by hand.
            chosen[base] = (path, ".docx")
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
        elif ext == ".docx":
            r = subprocess.run(["textutil", "-convert", "txt", "-stdout", path],
                               capture_output=True, text=True)
            if r.returncode != 0 or not r.stdout.strip():
                ignored.append(os.path.basename(path) + " (textutil failed — convert by hand)")
                continue
            txt = r.stdout
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


# ── media ─────────────────────────────────────────────────────────────────────
def _push_media(out_dir, fatal=False):
    """Store <out_dir>/slides/*.jpg in Anki's media collection. Idempotent. Returns the count.

    Factored out of cmd_media so `run` can do it BEFORE the mechanical gate — see the call site."""
    imgs = sorted(glob.glob(os.path.join(out_dir, "slides", "*.jpg")))
    if not imgs:
        msg = f"no JPEGs under {out_dir}/slides — run `build_deck.py slides` first"
        if fatal:
            sys.exit(msg)
        print(f"· media: {msg} (skipping)")
        return 0
    try:
        for p in imgs:
            invoke("storeMediaFile", filename=os.path.basename(p), path=os.path.abspath(p))
    except Exception as e:
        if fatal:
            raise
        print(f"· media: Anki unreachable ({e}) — image cards will flag in the gate")
        return 0
    print(f"· stored {len(imgs)} image(s) in Anki media")
    return len(imgs)


def cmd_media(a):
    """Push rendered slide images into Anki's media collection (idempotent)."""
    _push_media(a.out_dir, fatal=True)


# ── the Anki writer ─────────────────────────────────────────────────────────────
def _style_backstop(cards):
    """Last line of defence before anything reaches Anki: no card may ship breaking a property the
    corpus violates ZERO times.

    This is NOT the old pre-review gate. It runs on the OUTPUT, after the reviewer has had its say
    — a gate that runs BEFORE the judge outranks the judge, which is exactly how a rule the corpus
    contradicted ('always have hints') once held 40-odd cards the reviewer never got to see. Here
    the reviewer has already decided; this only refuses to write a card whose defect is measurable
    and absolute. If it ever fires, the harness has a bug: the reviewer had the same tool and
    should have caught it."""
    try:
        import style_check
    except ImportError:
        return []
    bad = []
    for c in cards:
        v = style_check.check(c.get("text", ""))["blocking"]
        if v:
            bad.append((c.get("id"), [x["problem"] for x in v]))
    return bad


def _write_notes(deck, cards, notes, out_dir, suspend_flagged, tag_reviewed, step="commit"):
    """The audited write path: create the model/deck, add notes one at a time (per-card
    reporting), then suspend-flagged / tag-reviewed. Shared by `commit` and `run` so both reuse
    exactly the writer that was hardened over many incidents — not a copy."""
    # Only APPROVED cards are gated. A `held` card is one the loop could not resolve — it ships
    # suspended under flag::held precisely so you can finish it in Anki, so refusing to write it
    # because it still has the defect that held it is circular: it blocks the whole deck over a
    # card already marked as unfinished.
    blocked = _style_backstop([c for c in cards if c.get("status", "approved") == "approved"])
    if blocked:
        print(f"\n!! REFUSING TO WRITE — {len(blocked)} card(s) break a corpus invariant:")
        for cid, probs in blocked:
            print(f"   {cid}: {'; '.join(probs)}")
        print("   The reviewer approved these and should not have — it has the same checker.")
        print("   Inspect with:  style_check.py --deck <cards.jsonl> --status approved")
        sys.exit(1)
    _ensure_model()
    if deck not in set(invoke("deckNames")):
        invoke("createDeck", deck=deck)
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
    print(f"added {added}/{len(notes)} note(s) to {deck!r}")
    _log(out_dir, step, f"{added} added, {len(dupes)} dupes, {len(failed)} failed -> {deck}")
    if suspend_flagged and new_pairs:
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
    if tag_reviewed and new_pairs:
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
    return added, dupes, failed, new_pairs


# ── commit — the hard barrier ───────────────────────────────────────────────────
# Writes a reviewed cards.jsonl to Anki by status. `run` reviews every card to a status first;
# `commit` just ships the result (approved + held). It is the only path that writes cards.
def cmd_commit(a):
    """Write a reviewed deck to Anki from a status-tracked cards.jsonl. Ships `approved` cards
    (tagged src::reviewed) and, unless --approved-only, `held` cards too (tagged flag::held and
    suspended, so you can find and finish them in Anki). `cut` cards are never written. A plain
    cards.jsonl with no status field is treated as all-approved (backward compatible)."""
    cards = [json.loads(l) for l in open(a.cards, encoding="utf-8") if l.strip()]
    if not cards:
        sys.exit(f"{a.cards} is empty")
    out_dir = os.path.dirname(os.path.abspath(a.cards))
    if not any("status" in c for c in cards):
        approved, held, cut = cards, [], []
    else:
        approved = [c for c in cards if c.get("status") == "approved"]
        held = [c for c in cards if c.get("status") == "held"]
        cut = [c for c in cards if c.get("status") == "cut"]

    def tagged(card, extra_tag):
        c = dict(card)
        c["tags"] = list(dict.fromkeys((c.get("tags") or []) + [extra_tag]))
        return c
    to_ship = [tagged(c, "src::reviewed") for c in approved]
    if not a.approved_only:
        to_ship += [tagged(c, "flag::held") for c in held]

    print(f"ship: {len(approved)} approved" +
          ("" if a.approved_only else f" + {len(held)} held (flag::held, suspended)") +
          (f"  |  {len(cut)} cut stay in the file, not written" if cut else ""))
    if a.dry_run:
        print(f"DRY RUN — would write {len(to_ship)} note(s) to {a.deck!r}. Anki untouched.")
        return
    if not to_ship:
        print("nothing to write."); return
    notes = [{"deckName": a.deck, "modelName": MODEL,
              "fields": {"Text": c.get("text", ""), "Extra": c.get("extra", ""),
                         "Source": c.get("source", "")}, "tags": c.get("tags", [])} for c in to_ship]
    _write_notes(a.deck, to_ship, notes, out_dir, suspend_flagged=True, tag_reviewed=False, step="commit")
    invoke("sync")
    print("· synced")


# The style authority is `reference_cards.jsonl` — six hand-built cards, one per shape, tracked in
# git and GENERATED FROM `reference_cards.py`, which is the thing you edit to change the style.
# `corpus` regenerates it from that file. `corpus --deck <name>` dumps an Anki deck for comparison
# and REQUIRES --out, because pulling a real deck over the reference is what the six cards fix.
CORPUS_OUT = os.path.join(HERE, "reference_cards.jsonl")


def cmd_corpus(a):
    """Regenerate reference_cards.jsonl from reference_cards.py — or dump an Anki deck elsewhere.

    The reference used to be a 37-card pull from `ISF::Test 2::Histology::Bone`, and every style
    rule derives from whatever it contains — so a re-pull could silently redefine the style, and
    once did: measuring that deck's 22% hintless rate turned "every cloze gets a hint" into "hint
    the ones that need it", and the next deck came back 65% hintless. The reference is now six
    hand-built cards under review, and the Anki path cannot write over them.
    """
    if not a.deck:
        rows = reference_cards.corpus_rows()
        with open(CORPUS_OUT, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{len(rows)} reference cards -> {CORPUS_OUT}  (from reference_cards.py)")
        return
    if not a.out:
        sys.exit("--deck needs --out: pulling a deck over reference_cards.jsonl would redefine "
                 "the style. To change the style, edit reference_cards.py and re-run `corpus`.")
    if os.path.abspath(a.out) == CORPUS_OUT:
        sys.exit(f"refusing to write {CORPUS_OUT} from an Anki deck — edit reference_cards.py.")
    notes = invoke("notesInfo", notes=invoke("findNotes", query=f'deck:"{a.deck}"'))
    if not notes:
        sys.exit(f"no notes in {a.deck!r} — is Anki open and the deck name right?")
    with open(a.out, "w", encoding="utf-8") as f:
        for n in notes:
            f.write(json.dumps({"note_id": n["noteId"], "model": n["modelName"],
                                "fields": {k: v["value"] for k, v in n["fields"].items()},
                                "tags": n["tags"]}, ensure_ascii=False) + "\n")
    print(f"{len(notes)} cards from {a.deck!r} -> {a.out}  (a dump for comparison, NOT the style)")


# ── continuity: baseline snapshot + edit capture ────────────────────────────────
# The learning signal is your OWN edits. `baseline` snapshots every card's current state to
# anki_baseline.jsonl; `wrap` re-pulls, diffs each field against that snapshot, records every
# change (before + after) to corrections.jsonl, then advances the baseline so each edit is
# captured once. No wrong-* tagging needed — an inline edit IS the correction, and the diff is
# grounded by construction (it's a change you actually made). Both pulls come live from Anki, so
# nothing has to be persisted at commit; the note id join key comes from the pull itself.
BASELINE_ROOT = "ISF"
BASELINE_OUT = os.path.join(HERE, "reference", "anki_baseline.jsonl")
CORRECTIONS_OUT = os.path.join(HERE, "corrections.jsonl")  # tracked — the ONE artifact Anki
# can't regenerate (once the baseline advances, the "before" is gone), so it must NOT live in the
# git-ignored reference/ dir. The baseline itself stays in reference/: it's rebuildable any time.


def _write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _load_jsonl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _pull_all(root):
    """One row per note under `root`: {note_id, deck, model, fields, tags}. `deck` is the note's
    real (leaf) deck, resolved from its cards (notesInfo doesn't carry it). Unlike `corpus`, this
    KEEPS wrong-* cards — the whole point is to catch every edit, defect flags included."""
    nids = invoke("findNotes", query=f'deck:"{root}"')
    if not nids:
        return []
    note_deck = {}
    for c in invoke("cardsInfo", cards=invoke("findCards", query=f'deck:"{root}"')):
        note_deck.setdefault(c["note"], c["deckName"])
    return [{"note_id": n["noteId"], "deck": note_deck.get(n["noteId"], root),
             "model": n["modelName"],
             "fields": {k: v["value"] for k, v in n["fields"].items()},
             "tags": n["tags"]}
            for n in invoke("notesInfo", notes=nids)]


def cmd_baseline(a):
    """Snapshot every ISF card's current state -> reference/anki_baseline.jsonl — the 'last known
    state' that `wrap` diffs your edits against. Run once to start (gets every card in); re-run to
    refresh. Cull by narrowing --root or deleting rows from the file."""
    snap = _pull_all(a.root)
    if not snap:
        sys.exit(f"no notes under {a.root!r} — is Anki open and the deck name right?")
    from collections import Counter
    _write_jsonl(a.out or BASELINE_OUT, snap)
    print(f"baseline: {len(snap)} card(s) -> {a.out or BASELINE_OUT}")
    for deck, n in sorted(Counter(c["deck"] for c in snap).items()):
        print(f"  {n:4d}  {deck}")


def _norm(s):
    # Anki stores fields as HTML; ignore only surrounding whitespace so a trivial resave isn't
    # logged as an edit. Any real content change still differs.
    return (s or "").strip()


def cmd_wrap(a):
    """Capture the edits you've made in Anki since the last baseline: pull every card now, diff
    each field against reference/anki_baseline.jsonl, and append every change to a PIPELINE-made
    card (before + after) to corrections.jsonl (tracked). Edits to imported AnKing/Pixorize decks
    are skipped — not our content, and copyrighted. Then advance the baseline so each edit is
    recorded once. Run `baseline` first."""
    base_path = a.baseline or BASELINE_OUT
    old = {c["note_id"]: c for c in _load_jsonl(base_path)}
    if not old:
        sys.exit(f"no baseline at {base_path} — run `build_deck baseline` first")
    now = _pull_all(a.root)
    now_by_id = {c["note_id"]: c for c in now}
    ts = datetime.datetime.now().isoformat(timespec="seconds")

    corrections, skipped = [], 0
    for nid, cur in now_by_id.items():
        prev = old.get(nid)
        if prev is None:
            continue  # new card since baseline — not an edit; it joins the advanced baseline
        changed = [f for f in set(prev["fields"]) | set(cur["fields"])
                   if _norm(prev["fields"].get(f, "")) != _norm(cur["fields"].get(f, ""))]
        if not changed:
            continue
        # Learn ONLY from cards the pipeline made (the Custom Cloze model). Edits to imported
        # AnKing/Pixorize decks teach the author/reviewer nothing about OUR generation and are
        # copyrighted — the baseline still tracks them (so they advance and don't re-surface),
        # but they never enter the memory, which keeps corrections.jsonl safe to commit.
        if cur.get("model") != MODEL:
            skipped += 1
            continue
        corrections.append({"note_id": nid, "deck": cur.get("deck"), "kind": "edit",
                            "changed": changed, "before": prev["fields"],
                            "after": cur["fields"], "ts": ts})
    for nid in (n for n in old if n not in now_by_id):           # deletions
        if old[nid].get("model") != MODEL:
            skipped += 1
            continue
        corrections.append({"note_id": nid, "deck": old[nid].get("deck"), "kind": "deleted",
                            "changed": list(old[nid]["fields"]), "before": old[nid]["fields"],
                            "after": None, "ts": ts})
    new = [nid for nid in now_by_id if nid not in old]
    n_edit = sum(c["kind"] == "edit" for c in corrections)
    n_del = len(corrections) - n_edit

    if a.dry_run:
        print(f"DRY RUN — {n_edit} edit(s) + {n_del} deletion(s) would log, {len(new)} new, "
              f"{skipped} non-pipeline skipped. Nothing written; baseline unchanged.")
        for c in corrections[:15]:
            print(f"  {c['kind']:7} {c['deck']}  fields={c['changed']}  nid={c['note_id']}")
        return

    if corrections:
        with open(CORRECTIONS_OUT, "a", encoding="utf-8") as f:
            for c in corrections:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    _write_jsonl(base_path, now)   # advance the baseline to now
    print(f"wrap: logged {n_edit} edit(s) + {n_del} deletion(s) -> "
          + (CORRECTIONS_OUT if corrections else "(nothing to log)")
          + f"  |  {len(new)} new, {skipped} non-pipeline skipped")
    print(f"  baseline advanced to {len(now)} card(s)")


def cmd_sync(a):
    invoke("sync")
    print("synced")


# ── run — THE pipeline driver ────────────────────────────────────────────────────
# A human (or scheduler) runs `build_deck run`. It orchestrates the whole pipeline itself and is
# the only thing that writes to Anki. Claude is never the orchestrator here — it is called as two CONSTRAINED
# sub-processes: authoring (read-only tools, returns drafts; author_create/author_fix) and review
# (one tool, to re-check a proposed fix; review_all). Neither can edit the rules, reach Anki, or
# skip a step — the driver spawns them
# without those tools. That inversion — script drives, agent is a sub-call — is what makes this a
# harness rather than a toolbox the agent picks up.

# Card drafts come back as structured output; the DRIVER writes them. The author needs no write tool.
AUTHOR_SCHEMA = {
    "type": "object",
    "properties": {"cards": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "text": {"type": "string"},
            "extra": {"type": "string"},
            "source": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "text", "extra", "source", "tags"], "additionalProperties": False}}},
    "required": ["cards"], "additionalProperties": False,
}


def _card_shape(text):
    """A card's markup shape: (n distinct clozes, roles clozed, roles left visible, is a list)."""
    cl = []
    for m in CLOZE_RE.finditer(text):
        p = m.group(1).split("::")
        cl.append(p[0] if len(p) == 1 else "::".join(p[:-1]))
    n = len({m.group(0).split("::")[0] for m in CLOZE_RE.finditer(text)})
    clozed = "".join(r for r in "biu" if any(re.search("<" + r + "[ >]", b) for b in cl))
    visible = "".join(r for r in "biu" if re.search("<" + r + "[ >]", CLOZE_RE.sub("", text)))
    return (n, clozed, visible, bool(re.search(r"(?:<br>|<div>)\s*\d+\.", text)))


def exemplars(per_shape=1):
    """ONE reference card per distinct markup shape — not the whole deck.

    The 37-card reference deck has only SIX shapes; 31 of the cards are repetition. Dumping all of
    them cost ~11k chars sitting between the rules and where the author starts writing, and that
    distance is the mechanism behind the worst failure this pipeline has had: with an identical
    prompt, a 37-card generation hinted every cloze and a 125-card generation was 65% hintless.
    Nothing was forgotten — the rules were just far behind the model's own output by then.

    Repetition also skews the signal. Seventeen near-identical two-cloze cards read as "this is
    what we do" and bury the 3-cloze and visible-subject cases in noise. One per shape makes every
    shape equally visible. Shortest card per shape: the clearest example of a shape is the one with
    the least incidental content."""
    if not os.path.exists(CORPUS_OUT):
        return []
    cards = [json.loads(l)["fields"]["Text"].replace("\n", " ")
             for l in open(CORPUS_OUT, encoding="utf-8") if l.strip()]
    by = {}
    for c in cards:
        by.setdefault(_card_shape(c), []).append(c)
    out = []
    for shape in sorted(by, key=lambda s: -len(by[s])):
        out += sorted(by[shape], key=len)[:per_shape]
    return out


def examples_block():
    """The reference cards dropped into the prompt as the STYLE AUTHORITY — one per SHAPE.
    style.md is explicit: shape is settled by these cards, NOT by a rule or a template classifier —
    'read the cards, don't consult a rule.'"""
    if not os.path.exists(CORPUS_OUT):
        return ""
    cards = exemplars()
    # This header is the LAST thing before the corpus dump, ~79% through a 52k-char prompt, and it
    # carries "THE CARDS WIN" authority — so whatever it says outranks everything above it in
    # practice. It used to end "a visible <b> subject is normal here; never force-cloze it", and
    # that one clause is why four hormone cards shipped with the hormone left visible: the reviewer
    # obeyed it and wrote "'Parathyroid hormone' serves as the general FRAME". State the MEASUREMENT
    # and the test here; never an absolute.
    header = ("\n\n===== REFERENCE CARDS — one per SHAPE. Your cards must look like these =====\n"
              "There are six, hand-built and owner-accepted, and this is all of them — one per "
              "shape. They DEFINE the house style; where a written rule and these cards disagree, "
              "THE CARDS WIN. Note the LIST card: the numbers sit OUTSIDE the braces and are not "
              "italicised, one item per line, every item sharing one cloze number. Note the IMAGE "
              "card: the picture is its own cloze and takes no hint.\n"
              "Every shape below is legitimate — including the ones that leave the <b> subject "
              "visible. Neither clozing nor not-clozing the subject is the default. Decide per card "
              "with the test in index.md: WRITE DOWN THE QUESTION THIS CARD ASKS, AND CHECK WHETHER "
              "THE SUBJECT IS ITS ANSWER. 'Which hormone raises blood calcium?' makes PTH the "
              "answer — cloze it. 'Bone's organic components' asks nothing about bone — leave it "
              "visible.\n")
    return header + "\n".join("  " + c for c in cards)


def _author_system_prompt():
    """Authoring standards: the okf rulebook + corpus examples, oriented to WRITING cards. The
    sub-call reads the sources itself (read-only tools); we hand it the rules it must obey."""
    okf = os.path.join(HERE, "okf")
    parts = ["You are a flashcard AUTHOR for an Anki cloze deck. Turn the deck's OWN source material "
             "into cloze cards that obey the rules below and look like the reference corpus.\n"
             "WHAT A CARD IS FOR: to make the student PRODUCE a key term or phrase FROM MEMORY, "
             "inside a complete thought. That is what reinforces recall — not re-reading a fact, not "
             "recognising it, but having to say it. So the question that decides every cloze is: "
             "WHAT MUST THE STUDENT PRODUCE FOR THIS CARD TO BE DOING ITS JOB? That word is the "
             "blank; everything else is there to make the sentence a complete, natural thought "
             "around it. If a card can be answered without recalling the thing it is about, it is "
             "not doing its job.\n"
             "Governing principle: FAITHFUL TRANSCRIPTION, NOT SYNTHESIS — render the source into "
             "card shape, add nothing, coin no terminology, prefer the source's own words. If a fact "
             "or term is not in the source, it does not go on a card.\n"
             "You have READ-ONLY tools and cannot write files — return every card via the schema.\n"
             "\nRUN `check_card` ON EVERY CARD YOU WRITE, BEFORE YOU RETURN IT. It measures the card "
             "against the owner's corpus and reports what the corpus NEVER does. A card with a "
             "BLOCKING finding is broken — fix it and re-check until the finding is gone. Do not "
             "return a card you have not checked.\n"
             "When you are FIXING a card, change ONLY what the note asks for. A fix that restructures "
             "the card usually trades one defect for another — re-check the result and confirm you "
             "have not introduced a finding the original did not have.\n"]
    for rel in ("index.md", "style.md", "review-checklist.md", "rules/card-structure.md",
                "rules/yield.md", "rules/accuracy.md", "rules/no-duplicate.md"):
        parts.append(f"\n\n===== {rel} =====\n" + open(os.path.join(okf, rel), encoding="utf-8").read())
    return "".join(parts) + examples_block()


def _author_call(task, deck_dir, model, kind, audit_round):
    """Plumbing: spawn a READ-ONLY claude that returns card JSONL via the schema, and log its full
    trace (files read, reasoning, metadata) to out/author.audit.jsonl. Returns (cards, cost)."""
    out_dir = os.path.join(deck_dir, "out")
    cmd = ["claude", "-p", task, "--system-prompt", _author_system_prompt(),
           "--json-schema", json.dumps(AUTHOR_SCHEMA), "--output-format", "stream-json", "--verbose",
           "--model", model, "--strict-mcp-config",
           "--mcp-config", _style_mcp_config(),
           "--allowedTools", "Read Grep Glob mcp__style__check_card mcp__style__invariants"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"author sub-call failed ({r.returncode}): {r.stderr[:300]}")
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    cards, cost, meta, reads = [], 0.0, {}, []
    audit = open(os.path.join(out_dir, "author.audit.jsonl"), "a", encoding="utf-8")
    def rec(**kw):
        audit.write(json.dumps({"round": audit_round, "kind": kind, "ts": stamp, **kw},
                               ensure_ascii=False) + "\n")
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = e.get("type")
        if t == "assistant":
            for b in e.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    rec(event="tool_use", tool=b.get("name"), input=b.get("input"))
                    if b.get("name") == "Read":
                        fp = (b.get("input") or {}).get("file_path")
                        if fp:
                            reads.append(fp)
                elif b.get("type") == "text" and b.get("text", "").strip():
                    rec(event="reasoning", text=b["text"])
        elif t == "result":
            cost = e.get("total_cost_usd", 0.0) or 0.0
            meta = {"session_id": e.get("session_id"), "num_turns": e.get("num_turns"), "cost_usd": cost}
            so = e.get("structured_output")
            if not so and e.get("result"):
                try:
                    so = json.loads(e["result"])
                except (json.JSONDecodeError, TypeError):
                    so = None
            cards = (so or {}).get("cards", [])
    rec(event="summary", n_cards=len(cards), files_read=reads, **meta)
    audit.close()
    return cards, cost


def author_create(deck_dir, model, slug=None, audit_round=0, sources=None):
    """STEP 1 — author cloze cards from the deck's sources. Short, examples-led prompt: the full
    style guide + real corpus examples are already in the system prompt; the task just points to the
    sources and states the card SHAPE plainly.

    `sources` is the explicit in-scope file list (from --sources). Naming the files beats pointing
    at a directory: the author cards what it was told to card instead of deciding for itself which
    of whatever is lying in the folder looks relevant."""
    out_dir = os.path.join(deck_dir, "out")
    base = os.path.abspath(out_dir)
    obj_files = glob.glob(os.path.join(out_dir, "sources", "*[Oo]bjective*.txt"))
    obj_text = ("\n\n===== LEARNING OBJECTIVES — every one gets at least one card =====\n" +
                open(obj_files[0], encoding="utf-8", errors="replace").read()[:6000]) if obj_files else ""
    listed = "\n".join(f"  {os.path.abspath(p)}" for p in (sources or []))
    scope = (f"CARD THESE SOURCES, ALL OF THEM. Read each one end to end with the Read tool and "
             f"work through it completely — every source named here is in scope because it was "
             f"chosen, so do not decide any of it is unimportant:\n{listed}\n"
             f"Slide images for figures: {base}/slides/*.jpg\n\n"
             if sources else
             f"Read this lecture's sources with the Read tool (absolute paths): the .txt files in "
             f"{base}/sources/ (objectives, transcript, slide text) and the slide images "
             f"{base}/slides/*.jpg.\n\n")
    task = (
        f"Author cloze flashcards for this lecture.\n\n{scope}"
        f"THE CARD SHAPE — make your cards LOOK LIKE the reference-corpus examples in your instructions. "
        f"Roles: <b> = subject, <i> = answer, <u> = facet.\n"
        f"  • CLOZE EVERY TESTABLE TERM. If the <b> subject is itself a term the student must RECALL "
        f"(a named structure/entity — 'lacunae', 'osteon', 'canaliculi'), cloze it as c1 — the corpus's "
        f"single most common card clozes BOTH the subject and the answer. Leave the subject VISIBLE only "
        f"when it is the general FRAME of the question, not a word being tested (e.g. '<b>amino acids</b> "
        f"have {{{{c1::<i>(S)</i>}}}} configuration' — 'amino acids' is the frame). Ask: would the student "
        f"need to PRODUCE this word? If yes, cloze it — never leave a testable term as visible prose.\n"
        f"  • THE CARD ENDS ON ITS ANSWER. The <i> span covers the WHOLE value tested — never cloze a "
        f"fragment and let the rest of the sentence trail after it unstyled. ✗ '{{{{c1::<i>raise</i>}}}} "
        f"low blood calcium levels to normal'  ✓ '{{{{c1::<u>raise</u>::raise or lower?}}}} "
        f"{{{{c2::<i>blood calcium levels to normal</i>::what?}}}}'. On a PROSE card, nothing "
        f"unstyled follows the answer. (An IMAGE card is exempt — ref-06 closes with 'that we can "
        f"see'. Its idiom names the thing and finishes the sentence.)\n"
        f"  • ONE <i> answer per PROSE card, ONE fact per card. A chain (A→B→C) becomes SEPARATE "
        f"one-answer cards. A LIST card is the exception: every item is <i> and they SHARE one "
        f"cloze number, so the list is one answer — see ref-05.\n"
        f"  • EVERY CLOZE GETS A HINT. No exceptions. Substituted into the blank, the hint must read "
        f"as natural English — '{{{{c1::<i>osteocytes</i>::what cells?}}}}' reads 'Lacunae contain "
        f"[what cells?]'. This is the owner's rule, stated directly. An earlier version of this line "
        f"said to hint only the clozes that needed it; the author took that as permission and a "
        f"124-card deck came back 65% hintless. There is no such permission.\n"
        f"  • Order the roles subject-first: <b> subject … <u> facet … <i> answer.\n\n"
        f"COVERAGE: every numbered objective below must get at least one card.\n"
        f"SOURCE: each card's `extra` = the slide <img> + a VERBATIM `<b>Source:</b> \"quote\"` copied "
        f"from a source you read. If you can't find a real quote for a fact, skip it — never a placeholder.\n"
        f"TAG each: isf::<subject>::<topic>, week::NN, src::okf-gen, slide::"
        + (f"{slug}-NN" if slug else "<slug>-NN") + " (when slide-based).\n" + obj_text)
    return _author_call(task, deck_dir, model, "author", audit_round)


DEDUP_SCHEMA = {
    "type": "object",
    "properties": {"duplicates": {"type": "array", "items": {
        "type": "object",
        "properties": {"dupe_id": {"type": "string"}, "keeps_id": {"type": "string"},
                       "why": {"type": "string"}},
        "required": ["dupe_id", "keeps_id", "why"], "additionalProperties": False}}},
    "required": ["duplicates"], "additionalProperties": False,
}

# The note prefix that marks a card the LECTURER told the class not to learn. A sentinel rather
# than a status because `held` is also where the fix loop parks cards it ran out of rounds on, and
# --resume must re-draft those while leaving this alone.
EXCLUDED_NOTE = "lecturer excluded this: "

TRANSCRIPT_SCHEMA = {
    "type": "object",
    "properties": {"unsupported": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "verdict": {"type": "string",
                       "enum": ["contradicted", "excluded", "low-emphasis"]},
                       "why": {"type": "string"}},
        "required": ["id", "verdict", "why"], "additionalProperties": False}}},
    "required": ["unsupported"], "additionalProperties": False,
}


def dedup_agent(cards, model):
    """Ask an agent which cards teach the SAME fact. Returns [(dupe_id, keeps_id, why)].

    This replaced a word-overlap score, which was the wrong instrument. Containment flagged
    'Type IV collagen is found in the basal lamina' as a duplicate of 'Type VII collagen connects
    the basal lamina to the connective tissue underneath' — four shared words out of five. Parallel
    phrasing on contrasting terms is house style, so a comparison-table deck generates those
    collisions by design, and four such cards were dropped from one build before any reviewer saw
    them. An agent tells type IV from type VII without being taught how."""
    listing = "\n".join(f"{c['id']}: {re.sub(r'<[^>]+>', '', c.get('text', ''))}" for c in cards)
    task = (
        "Below are flashcards from one deck. Find ONLY the pairs that teach the SAME FACT — where "
        "knowing one makes the other redundant.\n\n"
        "NOT duplicates, however similar the wording:\n"
        "  • different values of the same variable — 'type IV collagen' vs 'type VII collagen', "
        "'9%' vs '15%', 'periosteum' vs 'endosteum'. Contrasting pairs in parallel phrasing are "
        "deliberate house style.\n"
        "  • different aspects of one subject — where it is found vs what it does.\n"
        "  • a general statement and a specific instance of it.\n"
        "A pair is a duplicate only if a student who knows one learns nothing from the other.\n\n"
        "For each, give dupe_id (the one to drop), keeps_id (the one to keep — prefer the clearer "
        "or more complete card), and one line of why.\n\n" + listing)
    cmd = ["claude", "-p", task, "--json-schema", json.dumps(DEDUP_SCHEMA),
           "--output-format", "json", "--model", model, "--allowedTools", "", "--strict-mcp-config"]
    r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        print(f"  !! dedup agent failed ({r.stderr[:100]}) — no cards flagged")
        return [], 0.0
    try:
        d = json.loads(r.stdout)
        p = d.get("structured_output") or (json.loads(d["result"]) if d.get("result") else {})
        return [(x["dupe_id"], x["keeps_id"], x.get("why", "")) for x in p.get("duplicates", [])], \
               (d.get("total_cost_usd") or 0.0)
    except Exception as e:
        print(f"  !! dedup agent output unreadable ({e}) — no cards flagged")
        return [], 0.0


def transcript_agent(cards, transcript_path, model, other_sources=(), batch=25):
    """Ask an agent what the LECTURER said that the other sources cannot tell you.

    Deliberately narrow. The obvious version of this check — "is this card supported by the
    transcript?" — is wrong here, because a deck is authored from every file in `--sources` and
    only one of them is the recording. Histology Week 5 had seven sources: a comparison table, two
    Junqueira summaries, PowerPoints, and one transcript. For six of the seven, absence from the
    transcript is the NORMAL state; the lecturer never read the table aloud. So `not-taught` fired
    on correct cards from material the owner had explicitly named, sent them to `needs-fix`, and
    handed the fixer a defect no rewrite can repair — you cannot rewrite a card into having been
    taught. It also inverted the scope rule in resolve_sources: `--sources` STATES what must be
    carded, so the transcript does not get a veto over a named source.

    What only the transcript can settle is what the lecturer SAID:
      contradicted — he stated something different from the card. A real defect, always.
      excluded     — he told the class not to learn it. No rewrite saves it; a human decides.
      low-emphasis — advisory yield signal, reported and never routed anywhere.

    Returns ([(id, verdict, why)], cost).
    """
    text = open(transcript_path, encoding="utf-8", errors="replace").read()
    others = ", ".join(os.path.basename(p) for p in other_sources) or "(none)"
    out, total = [], 0.0
    for i in range(0, len(cards), batch):
        chunk = cards[i:i + batch]
        listing = "\n".join(f"{c['id']}: {re.sub(r'<[^>]+>', '', c.get('text', ''))}" for c in chunk)
        task = (
            "Here is a lecture transcript, then flashcards for that lecture.\n\n"
            "THE CARDS WERE NOT MADE FROM THE TRANSCRIPT ALONE. They were made from every assigned "
            f"source for this lecture, which also includes: {others}. A card can be entirely "
            "correct and appear NOWHERE in this transcript — the lecturer did not read the handouts "
            "or the textbook aloud. **Absence from the transcript is NOT a finding. Do not report "
            "it.** Reporting it once sent correct cards from assigned readings into a fix loop.\n\n"
            "Report ONLY what the lecturer SAID, which no other source can tell us:\n"
            "  contradicted — he stated something DIFFERENT from what the card says. Quote him.\n"
            "  excluded     — he told the class not to learn this: 'you don't need to know', "
            "'skip this', 'not on the exam', 'I won't test you on'. Quote him. Being skipped in "
            "silence is NOT exclusion — he must have said it.\n"
            "  low-emphasis — he covered it, but named it once in passing with nothing taught "
            "about it. Advisory only. Use this sparingly, and NEVER for a card whose material "
            "lives in one of the other sources listed above.\n\n"
            "If the transcript neither contradicts a card nor excludes it, say nothing about it.\n\n"
            f"===== TRANSCRIPT =====\n{text}\n\n===== CARDS =====\n{listing}")
        cmd = ["claude", "-p", task, "--json-schema", json.dumps(TRANSCRIPT_SCHEMA),
               "--output-format", "json", "--model", model, "--allowedTools", "",
               "--strict-mcp-config"]
        r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            print(f"  !! transcript agent failed on batch {i // batch + 1}")
            continue
        try:
            d = json.loads(r.stdout)
            total += d.get("total_cost_usd") or 0.0
            p = d.get("structured_output") or (json.loads(d["result"]) if d.get("result") else {})
            out += [(x["id"], x["verdict"], x.get("why", "")) for x in p.get("unsupported", [])]
        except Exception as e:
            print(f"  !! transcript agent output unreadable ({e})")
    return out, total


def resolve_sources(deck_dir, spec):
    """The extracted source files IN SCOPE for this deck. Returns (paths, missing_specs).

    Scope is STATED, not inferred. An earlier version of this pipeline tried to work out what
    deserved a card by counting term frequencies in whatever happened to be in the folder; the
    owner's answer was that the material to card is given — "we need cards for the powerpoint,
    transcript and the Junqueira summary". So `spec` is a comma-separated list of substrings, each
    of which MUST match a file, and a spec that matches nothing is an error rather than a silent
    omission."""
    have = sorted(glob.glob(os.path.join(deck_dir, "out", "sources", "*.txt")))
    if not spec:
        return have, []

    def key(s):
        """Match on letters and digits only, URL-decoded. These files arrive from downloads with
        names like 'Bone%20Histology%20Power%20Point%20Slides.ppt.txt', and nobody is going to type
        that — 'powerpoint' has to find 'Power%20Point'."""
        return re.sub(r"[^a-z0-9]+", "", urllib.parse.unquote(s).lower())

    chosen, missing = [], []
    for want in [s.strip() for s in spec.split(",") if s.strip()]:
        hits = [p for p in have if key(want) in key(os.path.basename(p))]
        chosen += hits
        if not hits:
            missing.append(want)
    chosen = sorted(set(chosen))
    # SAY WHAT WAS LEFT OUT. A spec that matches NOTHING is already an error, but a spec that
    # matches ONE of TWO files you meant is silent — and that is the case that bites: Histology
    # Week 5 held both "Junqueira Cartilage Summary" and "Junquiera CT summary" (transposed 'ie'),
    # so --sources "…,junqueira" selected one, dropped the other, and reported success. The
    # unselected list is the only thing that makes an under-selection visible.
    left_out = [os.path.basename(p) for p in have if p not in chosen]
    if left_out:
        print(f"· --sources selected {len(chosen)} of {len(have)} extracted file(s). NOT carded: "
              + ", ".join(left_out))
        print("  If one of those should be in scope, stop and add it — a spec that matches one of "
              "two intended files passes silently.")
    return chosen, missing


def author_fix(deck_dir, model, needs_fix, audit_round, source_hint=None):
    """STEP 3 — the author rewrites each flagged card. Two powers beyond a plain rewrite:
      • SPLIT — a chain / compound / buried-answer card becomes SEVERAL one-answer cards (never
        resolve a compound by deleting a real fact).
      • VERIFY — when a source is given, check a flagged 'not in source' fact against the lecture
        before removing it; if the lecture supports it, keep the fact and fix the citation instead.
    Returns (list_of_cards, cost). A split reuses the original id for the first card and '<id>-b',
    '<id>-c' for the rest, so the loop can map results back to the card they came from."""
    lines = ["Revise these cards. Each has a PROBLEM to fix, and a STYLE CHECK measured against the "
             "corpus. Rules:\n"
             "• Fix ONLY the flagged problem and keep the SAME fact(s). A fix that restructures the "
             "card trades one defect for another — the most common failure here is returning a card "
             "that resolves the note but breaks something the original got right.\n"
             "• The STYLE CHECK under each card is measured, not opinion. Every BLOCKING line must be "
             "gone from your replacement, and you must not introduce a new one. Do not 'fix' anything "
             "the check does not flag and the note does not mention.\n"
             "• Keep a verbatim Source quote in `extra`. CLOZE the <b> subject when it is a term the "
             "student must recall (a named structure/entity — 'lacunae', 'osteon'); leave it visible "
             "only when it is the general frame, not a word being tested.\n"
             "• SPLIT when the problem is a CHAIN / COMPOUND / BURIED ANSWER (more than one fact, or "
             "a trailing testable detail): return SEVERAL one-answer cards, not one. Reuse the given "
             "id for the first and ids '<id>-b', '<id>-c' for the rest. NEVER resolve a compound by "
             "DELETING a real fact — split it out instead.\n"]
    if source_hint:
        lines.append(f"• VERIFY, don't delete: the lecture source is at {source_hint} — Read/Grep "
                     f"it. Before removing a fact the note calls 'added' or 'not in source', CHECK "
                     f"the lecture. If the lecture supports the fact, KEEP it and REPLACE the "
                     f"verbatim Source quote in `extra` with a real line from the lecture that "
                     f"covers it. Only drop a fact the lecture genuinely does not support.\n")
    for c in needs_fix:
        lines.append(f"\n--- id {c.get('id')} ---\nText: {c.get('text','')}\nExtra: {c.get('extra','')}"
                     f"\nPROBLEM: {c.get('note','')}")
        try:                                  # inline, never rely on the fixer fetching the tool
            import style_check
            lines.append(style_check.render(c.get("text", "")))
        except ImportError:
            pass
    cards, cost = _author_call("\n".join(lines), deck_dir, model, "fix", audit_round)
    return cards, cost


# ── review sub-call (STEP 2 — FLAGS a status + note, never rewrites) ───────────────────
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {"verdicts": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"},
                       "verdict": {"type": "string", "enum": ["approved", "needs-fix", "cut"]},
                       "note": {"type": "string"}},
        "required": ["id", "verdict", "note"], "additionalProperties": False}}},
    "required": ["verdicts"], "additionalProperties": False,
}


def _review_system_prompt():
    okf = os.path.join(HERE, "okf")
    parts = ["You are a strict flashcard REVIEWER. For EACH card, compare it to the REFERENCE CORPUS "
             "cards below (the style authority) and return one verdict.\n"
             "WHAT A CARD IS FOR: to make the student PRODUCE a key term or phrase FROM MEMORY, "
             "inside a complete thought. Judge every card against that first. WRITE DOWN THE "
             "QUESTION THE CARD ASKS, then check the subject: IS THE SUBJECT THAT QUESTION'S ANSWER? "
             "If it is and it is left visible, the card cannot do its job — that is `needs-fix`. "
             "'<b>Parathyroid hormone</b> acts on bone to {{c1::raise blood calcium}}' asks WHICH "
             "HORMONE raises blood calcium, so PTH is the answer and must be clozed; calling it a "
             "'general frame' is exactly the error this instruction exists to stop. A class the "
             "sentence is merely scoped to ('amino acids') is not an answer and stays visible.\n"
             "  approved — it looks like the corpus cards and is worth knowing. Approve ONLY what you "
             "would not change.\n"
             "  needs-fix — it breaks a rule the CORPUS actually follows (a TESTABLE-TERM subject left "
             "un-clozed, two red <i> answers, a chain fact that must be split, under-clozed answer, a "
             "fragmented enumeration). Put the SPECIFIC fix in `note`. Do NOT rewrite the card — the "
             "author fixes it from your note.\n"
             "  cut — low yield (restates a bullet, vacuous filler) OR the fact is wrong/unsupported. "
             "Say why in `note`.\n"
             "Grade STYLE against the corpus CARDS, not a remembered rule, and not on whether the card "
             "'reads okay'. If a written rule and the cards disagree, the cards win.\n"
             "\nYOU HAVE ONE TOOL: `check_card`. CALL IT FOR EVERY CARD before you decide, and call it "
             "again on any replacement text you put in `note`. It measures the card against the corpus "
             "and reports what the corpus NEVER does.\n"
             "  - ANY 'BLOCKING' finding => the verdict is `needs-fix`. No exceptions, no judgment "
             "call: those properties have ZERO counterexamples in the corpus. Copy the finding and "
             "its fix into `note`.\n"
             "  - 'UNUSUAL' findings are rare-but-real in the corpus. Change the card unless you can "
             "say why this card is the exception.\n"
             "  - Judge shape against the COMPARABLE cards the tool returns for that specific card, "
             "not against the full corpus dump.\n"
             "  - Answer the tool's JUDGMENT questions yourself — it cannot, and it does not try.\n"
             "The tool reports facts about the card; it never decides yield, accuracy, or whether a "
             "visible bold subject is a term or a frame. Those remain yours.\n"]
    for rel in ("index.md", "style.md", "review-checklist.md", "rules/card-structure.md",
                "rules/yield.md", "rules/accuracy.md", "rules/no-duplicate.md"):
        parts.append(f"\n\n===== {rel} =====\n" + open(os.path.join(okf, rel), encoding="utf-8").read())
    return "".join(parts) + examples_block()


def _style_mcp_config():
    """The style checker as the reviewer's ONE tool. Needs the venv interpreter — `mcp` lives
    there, not in the system python."""
    py = os.path.join(HERE, ".venv", "bin", "python")
    return json.dumps({"mcpServers": {"style": {
        "command": py if os.path.exists(py) else sys.executable,
        "args": [os.path.join(HERE, "style_mcp.py")]}}})


def review_all(cards, model, batch=5, use_tool=True, jobs=8):
    """Reviewer over all cards. Returns ({id: {verdict, note}}, cost).

    Every card carries its own measured STYLE CHECK, inlined below it (see the chunk loop). That
    guarantee is per-card, so it does NOT depend on the batch size — which is why batching is back.
    batch=1 was briefly the default while the reviewer had to CALL the checker per card; at ~2,500
    lines of system prompt re-sent per call it made a single review round over 46 cards take ~45
    minutes, and bought nothing once the report was inlined. 5 keeps per-card evidence while
    amortising the prompt."""
    from concurrent.futures import ThreadPoolExecutor
    sysp = _review_system_prompt()
    out, total = {}, 0.0
    chunks = [cards[i:i + batch] for i in range(0, len(cards), batch)]

    def run_chunk(chunk):
        lines = ["Review EACH card. Return one verdict per card, keyed by its id.\n"]
        if use_tool:
            lines.append(
                "Each card below already carries its STYLE CHECK, computed against the corpus. "
                "Any BLOCKING finding means needs-fix — copy it and its fix into `note`.\n"
                "Use the `check_card` tool to re-check any replacement text you propose.\n")
        for c in chunk:
            lines.append(f"\n--- id: {c['id']} ---\nText: {c.get('text','')}\n"
                         f"Extra: {c.get('extra','')}\nSource: {c.get('source','')}")
            if use_tool:
                # INLINE the report rather than trusting the model to fetch it. MCP tools are
                # DEFERRED in this CLI: they are absent from the tool list at init (`status:
                # pending`) and must be discovered via ToolSearch, so whether the model ever calls
                # check_card is probabilistic. bone-005 shipped `approved` with a BLOCKING finding
                # for exactly this reason — reviewed with no tool, fell back to eyeballing. The
                # tool stays available for re-checking a PROPOSED fix, which cannot be precomputed.
                try:
                    import style_check
                    lines.append("\n" + style_check.render(c.get("text", "")))
                except ImportError:
                    pass
        cmd = ["claude", "-p", "\n".join(lines), "--system-prompt", sysp,
               "--json-schema", json.dumps(REVIEW_SCHEMA), "--output-format", "json",
               "--model", model, "--strict-mcp-config"]
        cmd += (["--mcp-config", _style_mcp_config(),
                 "--allowedTools", "mcp__style__check_card,mcp__style__invariants"]
                if use_tool else ["--allowedTools", ""])
        r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            return ({c["id"]: {"verdict": "needs-fix",
                               "note": f"reviewer error: {r.stderr[:120]}"} for c in chunk}, 0.0)
        got = {}
        try:
            d = json.loads(r.stdout)
            cost = d.get("total_cost_usd", 0.0) or 0.0
            payload = d.get("structured_output") or (json.loads(d["result"]) if d.get("result") else {})
        except Exception as e:
            return ({c["id"]: {"verdict": "needs-fix",
                               "note": f"unparseable reviewer output: {e}"} for c in chunk}, 0.0)
        for v in payload.get("verdicts", []):
            got[str(v.get("id"))] = {"verdict": v.get("verdict", "needs-fix"), "note": v.get("note", "")}
        for c in chunk:
            got.setdefault(c["id"], {"verdict": "needs-fix", "note": "no verdict returned — re-review"})
        return got, cost

    # Batches are independent, so run them concurrently. Sequential review is what made a single
    # round over 46 cards take ~42 minutes; nothing about a verdict depends on another batch.
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for got, cost in ex.map(run_chunk, chunks):
            out.update(got)
            total += cost
    return out, total


def _slug(s):
    return "".join(ch if ch.isalnum() else "-" for ch in s).strip("-").lower()


def cmd_review_deck(a):
    """Feed an EXISTING Anki deck through the harness's reviewer (read-only). Pulls every pipeline
    card (Custom Cloze) in --deck, runs the corpus-derived style check + the reviewer over it, and
    writes a punch-list (verdict + findings per card) to --out. Anki is NOT touched — this only
    assesses. Use it to triage a hand-made deck; then fix cards in Anki and `wrap` captures the fixes.

    The shape column used to come from `strict_shape.classify_card`, whose T1-T5 templates were
    measured from the deprecated AnKing Neurogenetics deck — so this diagnostic was grading the
    owner's decks against a deck the project had abandoned. It now reports the same BLOCKING
    invariants the pipeline enforces, measured from the live corpus."""
    allc = _pull_all(a.deck)
    snap = [c for c in allc if c.get("model") == MODEL]
    if not snap:
        sys.exit(f"no Custom-Cloze cards in {a.deck!r} — is the deck name right, and Anki open?")
    cards = [{"id": str(c["note_id"]), "text": c["fields"].get("Text", ""),
              "extra": c["fields"].get("Extra", ""), "source": c["fields"].get("Source", "")}
             for c in snap]
    print(f"reviewing {len(cards)} Custom-Cloze card(s) from {a.deck!r}…")
    verdicts, cost = review_all(cards, a.model)
    rows = []
    for c in cards:
        v = verdicts.get(c["id"], {"verdict": "needs-fix", "note": "no verdict returned"})
        blocking = _blocking_of(c["text"])
        rows.append({"note_id": c["id"], "verdict": v["verdict"], "note": v["note"],
                     "blocking": blocking, "text": c["text"]})
    order = {"cut": 0, "needs-fix": 1, "approved": 2}
    rows.sort(key=lambda r: (order.get(r["verdict"], 1), not r["blocking"]))
    out = a.out or os.path.join(HERE, "out", f"review-{_slug(a.deck)}.jsonl")
    _write_jsonl(out, rows)
    from collections import Counter
    t = Counter(r["verdict"] for r in rows)
    bad_shape = sum(1 for r in rows if r["blocking"])
    print(f"\n  approved {t.get('approved', 0)}  |  needs-fix {t.get('needs-fix', 0)}  |  "
          f"cut {t.get('cut', 0)}   ·   {bad_shape} break a corpus invariant   ·   ${cost:.2f}")
    print(f"  full punch-list -> {out}\n")
    for r in rows:
        if r["verdict"] != "approved" or r["blocking"]:
            flag = f" [{'; '.join(r['blocking'])}]" if r["blocking"] else ""
            print(f"  [{r['verdict']:9}]{flag} {r['note']}")
    skipped = len(allc) - len(snap)
    if skipped:
        print(f"\n  ({skipped} non-Custom-Cloze card(s) skipped — not pipeline-shaped)")


def ocr_slides(deck_dir, model):
    """Transcribe slide-image text into out/sources/slides-ocr.txt so quotes lifted from slide
    figures (which pdftotext misses) are verifiable at commit. A read-only VISION sub-call,
    independent of the author — genuine provenance, not the author certifying itself. Batched and
    cached (skips if slides-ocr.txt already exists)."""
    out_dir = os.path.join(deck_dir, "out")
    ocr_path = os.path.join(out_dir, "sources", "slides-ocr.txt")
    if os.path.exists(ocr_path) and os.path.getsize(ocr_path):
        print("  slide OCR cached — skipping")
        return 0.0
    imgs = sorted(glob.glob(os.path.join(out_dir, "slides", "*.jpg")))
    if not imgs:
        return 0.0
    total, chunks = 0.0, [imgs[i:i + 6] for i in range(0, len(imgs), 6)]
    parts = []
    for gi, group in enumerate(chunks, 1):
        task = ("Transcribe the VISIBLE TEXT of each slide image below, VERBATIM. Read each with the "
                "Read tool. Output one block per slide: a line '=== <filename> ===' then every word of "
                "text on that slide (title, bullets, labels, table cells, figure captions) exactly as "
                "written — no paraphrase, no commentary, skip nothing textual.\n\n" + "\n".join(group))
        cmd = ["claude", "-p", task, "--output-format", "json", "--model", model,
               "--allowedTools", "Read", "--strict-mcp-config"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ! slide OCR batch {gi}/{len(chunks)} failed — image quotes may not verify")
            continue
        d = json.loads(r.stdout)
        parts.append(d.get("result", "") or "")
        total += d.get("total_cost_usd", 0.0) or 0.0
        print(f"  OCR batch {gi}/{len(chunks)} ({len(group)} slides)")
    with open(ocr_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(parts))
    return total


def _blocking_of(text):
    """The corpus-invariant violations in one card's Text, as plain strings (empty = clean).

    Safe to gate on, unlike the shape rules that preceded it: every BLOCKING predicate has ZERO
    counterexamples in the corpus, and `tests/test_style_check.py` asserts both that and that every
    corpus card passes. The old hint gate blocked cards for a rule 48% of the corpus broke — that
    cannot happen to a rule derived from the corpus itself."""
    try:
        import style_check
    except ImportError:
        return []
    return [b["problem"] for b in style_check.check(text)["blocking"]]


STYLE_PASS_SCHEMA = {
    "type": "object",
    "properties": {
        "changed": {"type": "boolean"},
        "text": {"type": "string"},
        "why": {"type": "string"},
    },
    "required": ["changed", "text", "why"], "additionalProperties": False,
}


def _style_guide_block():
    """The COMPACT style guide: style.md's five lines + the corpus-derived invariant table.

    Deliberately NOT the full okf rulebook (39k chars) nor the full corpus dump. This prompt is
    rebuilt for every card, so its size IS the running time — the batched reviewer carried 51k
    chars of system prompt per call and took ~40s a card. The per-card COMPARABLE cards and the
    measured findings arrive with the card itself, which is what the corpus dump was there for."""
    style = open(os.path.join(HERE, "okf", "style.md"), encoding="utf-8").read()
    try:
        import style_check
        rows = style_check.derive()
        n = rows[0][5] if rows else 0
        table = "\n".join(f"  [{t}] {lab}  ({h} of {n} corpus cards)"
                          for _k, lab, _f, _x, h, _n, t in rows if t != "allowed")
        table = (f"\n\n===== MEASURED RULES (from {n} owner-accepted cards) =====\n"
                 "BLOCKING = zero counterexamples in the corpus. UNUSUAL = rare, justify it.\n" + table)
    except ImportError:
        table = ""
    return "===== STYLE =====\n" + style + table


def _style_pass_system_prompt():
    return (
        "You EDIT one Anki cloze card so it matches the house style. You see ONE card and nothing "
        "else — no other cards, no history.\n"
        "Return `changed:false` and the text VERBATIM unless the card actually breaks the style. "
        "Leaving a correct card alone is a SUCCESS, not a missed opportunity — most cards are fine.\n"
        "When you do edit:\n"
        "  - Fix ONLY the style. Never change which facts the card states, never add or remove a "
        "fact, never reword for taste.\n"
        "  - Every BLOCKING finding must be gone, and you must not introduce a new one.\n"
        "  - Keep the same cloze numbers and hints unless the finding is about them.\n"
        "  - `why` is ONE short line naming what you changed.\n"
        "Roles: <b> subject, <u> facet (the aspect asked about), <i> answer (the value recalled).\n"
        + _style_guide_block())


def style_pass_card(card, model, effort="low"):
    """ONE card, ONE fresh context, no tools. Returns (new_text or None, why, cost).

    Each call is an independent process, so nothing carries over between cards — a verdict on card
    N cannot colour card N+1. That isolation is the point: the batched reviewer judged 5-10 cards
    in one context and its opinions bled across them."""
    import style_check
    text = card.get("text", "")
    task = ("Card (JSON):\n" + json.dumps({"id": card.get("id"), "text": text}, ensure_ascii=False) +
            "\n\n" + style_check.render(text) +
            "\n\nReturn the card's `text`, edited only if the style requires it.")
    cmd = ["claude", "-p", task, "--system-prompt", _style_pass_system_prompt(),
           "--json-schema", json.dumps(STYLE_PASS_SCHEMA), "--output-format", "json",
           "--model", model, "--effort", effort, "--allowedTools", "", "--strict-mcp-config"]
    r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        return None, f"agent error: {r.stderr[:120]}", 0.0
    try:
        d = json.loads(r.stdout)
        cost = d.get("total_cost_usd", 0.0) or 0.0
        p = d.get("structured_output") or (json.loads(d["result"]) if d.get("result") else {})
    except Exception as e:
        return None, f"unparseable: {e}", 0.0
    new = (p.get("text") or "").strip()
    if not p.get("changed") or not new or new == text:
        return None, p.get("why", ""), cost
    return new, p.get("why", ""), cost


def style_findings(text):
    """BLOCKING + UNUSUAL problems for one card — everything the checker has an opinion about."""
    try:
        import style_check
    except ImportError:
        return []
    r = style_check.check(text)
    return [x["problem"] for x in r["blocking"] + r["unusual"]]


def review_fix_loop(cards, deck_dir, model, max_rounds, mechanical, save=None, source_hint=None):
    """STEPS 2–4 of the pipeline — review → fix → re-review over a list of status-carrying cards,
    IN PLACE, bounded by `max_rounds`. Shared by `run` (after it authors drafts) and `insert`
    (after it seeds drafts from an existing Anki deck) so there is ONE loop, not two.
    `mechanical(card) -> [reasons]` is the deterministic gate (shape, plus verbatim-source when
    sources exist); `save(cards)` persists after each mutation if given. Nothing is dropped — a
    card the author can't resolve becomes `held`. Returns (cards, total_cost)."""
    total = 0.0
    def _save():
        if save:
            save(cards)
    for rnd in range(1, max_rounds + 2):
        drafts = [c for c in cards if c.get("status") == "draft"]
        # Keep going when something is already `needs-fix` even with no drafts left. Cards now
        # arrive here pre-reviewed (step 1 reviews each file as it is authored) and the only thing
        # left to resolve is what dedup / the transcript check pushed back — with the old
        # break-on-no-drafts those would have been surfaced as `held` without one fix attempt.
        if not drafts and not any(c.get("status") == "needs-fix" for c in cards):
            break
        # 2a mechanical marking — flags needs-fix with the exact reason; NEVER deletes a card
        to_review = []
        for c in drafts:
            m = mechanical(c) + _blocking_of(c.get("text", ""))
            if m:
                c["status"] = "needs-fix"; c["note"] = "; ".join(m)
            else:
                to_review.append(c)
        # 2b reviewer on the mechanically-clean drafts -> approved / needs-fix / cut
        if to_review:
            print(f"· step 2 — round {rnd}: reviewing {len(to_review)} card(s)…")
            verdicts, cost = review_all(to_review, model); total += cost
            for c in to_review:
                v = verdicts.get(c["id"], {"verdict": "needs-fix", "note": "no verdict — re-review"})
                c["status"] = v["verdict"]; c["note"] = v.get("note", "")
        _save()
        need = [c for c in cards if c.get("status") == "needs-fix"]
        if not need:
            break
        if rnd > max_rounds:
            for c in need:
                c["status"] = "held"                 # ran out of fix rounds — surfaced, not dropped
            break
        # 3 the author rewrites needs-fix cards (may SPLIT one -> several). Map every returned card
        #   back onto the deck by id: a known id UPDATES that card; a new '<id>-b' APPENDS a split-
        #   off. Re-fixing a card that already split thus updates its split-off in place instead of
        #   spawning a duplicate each round.
        print(f"· step 3 — round {rnd}: author fixing {len(need)} card(s)…")
        returned, cost = author_fix(deck_dir, model, need, audit_round=rnd, source_hint=source_hint)
        total += cost
        by_id = {c["id"]: c for c in cards}
        for c in need:
            oid = c["id"]
            got = [rc for rc in returned if rc.get("text") and
                   (str(rc.get("id")) == oid or str(rc.get("id", "")).startswith(oid + "-"))]
            for rc in got:
                rid = str(rc["id"])
                tgt = by_id.get(rid)
                if tgt is None:                           # a genuinely new split-off
                    tgt = {"id": rid, "source": c.get("source", ""), "tags": c.get("tags", []),
                           "extra": c.get("extra", "")}
                    cards.append(tgt); by_id[rid] = tgt
                tgt["text"] = rc["text"]
                if rc.get("extra"):
                    tgt["extra"] = rc["extra"]
                # VERIFY THE FIX BEFORE IT RE-ENTERS THE QUEUE. Checking a returned card costs
                # nothing and is deterministic, so a fix that still breaks a corpus invariant goes
                # straight back to a fresh fixer instead of spending a review call to learn what we
                # can already prove. This is the loop's answer to "the fix introduced a new defect":
                # bone-035-a was told only to reuse the source's wording and came back restructured
                # with a second bold cloze, which then cost a full review round to discover.
                still = _blocking_of(tgt["text"])
                if still:
                    tgt["status"] = "needs-fix"
                    tgt["note"] = ("YOUR PREVIOUS FIX STILL BREAKS THE CORPUS: " + "; ".join(still) +
                                   ". Fix ONLY this, and do not restructure the rest of the card.")
                else:
                    tgt["status"] = "draft"; tgt["note"] = ""
            # if nothing mapped to this card, it stays needs-fix (retried next round or held)
        _save()
    # any card still needs-fix (author couldn't resolve it) -> held: surfaced, never dropped
    for c in cards:
        if c.get("status") == "needs-fix":
            c["status"] = "held"
    _save()
    return cards, total


def cmd_run(a):
    """THE driver — your 4 steps over ONE status-tracked cards.jsonl. NOTHING is ever deleted:
    every card stays in the file with a status (draft / approved / needs-fix / cut / held) + a note
    saying why. Only `approved` cards are written to Anki.

      1 create   author writes draft cards
      2 review   mechanical gate + reviewer set each card's status (+ note for fixes)
      3 fix      the author rewrites needs-fix cards from the note, back to draft
      4 re-review  loop 2-3 until nothing is needs-fix (bounded; leftovers -> held, still in the file)

    --resume skips step 1 and re-enters the existing cards.jsonl's held/needs-fix cards at step 2.
    """
    from check_cards import load_sources, load_media, check_card
    from collections import Counter
    deck_dir = a.deck_dir
    out_dir = os.path.join(deck_dir, "out")
    os.makedirs(out_dir, exist_ok=True)
    cards_path = os.path.join(out_dir, "cards.jsonl")

    if not os.path.isdir(os.path.join(out_dir, "sources")):
        print("· sources missing — extracting…")
        cmd_sources(argparse.Namespace(deck_dir=deck_dir))
    if not os.path.exists(os.path.join(out_dir, "slides.jsonl")):
        sys.exit(f"no {out_dir}/slides.jsonl — render slides first:\n"
                 f"  build_deck slides <slides.pdf> {out_dir} <slug>")

    resume = getattr(a, "resume", False)
    if resume and not os.path.exists(cards_path):
        sys.exit(f"--resume needs an existing {cards_path} — run without --resume to author it first.")

    # Scope is STATED, never inferred. Three documents say so; the flag used to default to "",
    # which cards everything, so omitting it did exactly what they forbid — silently, with the run
    # reporting success. Checked HERE, before the OCR call and the media push: the first version of
    # this validation sat inside the authoring branch, and a missing --sources burned a paid OCR
    # pass and 131 media writes before erroring. Same mistake as truncating the audit log first.
    if not resume and a.sources is None and not getattr(a, "all_sources", False):
        sys.exit("--sources is REQUIRED: name what must be carded, e.g.\n"
                 '  --sources "powerpoint,transcript,junqueira"\n'
                 "Scope is stated, not inferred from whatever is in the folder. To card every "
                 "extracted file on purpose, pass --all-sources.")

    total = 0.0
    print("· OCR slide images -> sources (so figure/bullet quotes are verifiable)…")
    total += ocr_slides(deck_dir, a.model)
    src_dir = os.path.join(out_dir, "sources")
    NB = load_sources(src_dir if os.path.isdir(src_dir) else None)
    # Push slide JPEGs into Anki BEFORE the gate runs. `media` is documented as step 10 — after the
    # pipeline — but check_card flags "image not in Anki media" on every <img> card, so on the
    # documented ordering an image card comes back needs-fix on round 1 and the fixer burns its
    # rounds on a defect no rewrite can repair. The step is idempotent, so doing it here costs
    # nothing and removes the ordering trap entirely.
    if not a.no_media:
        _push_media(out_dir)
    media, no_media = load_media(a.no_media)

    def save(cards):
        with open(cards_path, "w", encoding="utf-8") as f:
            for c in cards:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

    def mechanical(c):
        """Deterministic checks — PROVENANCE (verbatim source) + media, and the ONE shape rule the
        corpus never breaks (>3 distinct clozes — zero corpus violations). Everything else about SHAPE is judged by
        the reviewer against the corpus cards; style.md says the corpus stats are 'not
        limits to enforce', so there is no template gate (strict_shape no longer governs the
        process). Keep it that way: this gate runs BEFORE the reviewer and short-circuits it, so any
        rule added here outranks the corpus instead of being checked against it."""
        return check_card(c.get("text", ""), c.get("extra", ""), c.get("source", ""),
                          NB, media, no_media)

    # ── STEP 1 — create (or, with --resume, re-enter the leftovers) ─────────────
    if resume:
        # Re-run steps 2–4 over an EXISTING cards.jsonl instead of authoring fresh. This is how a
        # harness fix gets tested against the very cards that exposed it: without it, validating a
        # gate change costs a full re-author and lands on different cards, so the regression case is
        # gone. `held`/`needs-fix` go back to `draft` (their notes were written by the old rules and
        # would otherwise steer the author); `approved` and `cut` are verdicts already reached and
        # are left alone.
        cards = _load_jsonl(cards_path)
        redo = ["held", "needs-fix"]
        if getattr(a, "recheck_approved", False):
            redo.append("approved")            # a harness change makes prior approvals stale
        again = [c for c in cards if c.get("status") in redo]
        # ONE exception: a card held because the lecturer told the class not to learn it. That note
        # is a finding about the LECTURE, not about the card's markup, so the "its note was written
        # by the old rules" reasoning does not apply — clearing it would re-author and re-approve
        # the card, silently reversing a decision the transcript settled.
        excluded = [c for c in again if str(c.get("note", "")).startswith(EXCLUDED_NOTE)]
        if excluded:
            again = [c for c in again if c not in excluded]
            print(f"  keeping {len(excluded)} card(s) held: the lecturer excluded them")
        if getattr(a, "recheck_flagged", False):
            # Re-review only what the checker can already prove is suspect. Re-reviewing a clean
            # approved card costs a full model call to re-confirm what measurement settled for
            # free — that is the whole cost of a --recheck-approved pass (37 of 46 cards on Bone).
            again = [c for c in again
                     if c.get("status") != "approved" or _blocking_of(c.get("text", ""))
                     or style_findings(c.get("text", ""))]
        for c in again:
            c["status"] = "draft"; c["note"] = ""
        st = Counter(c.get("status") for c in cards)
        print(f"· step 1 skipped (--resume) — {len(cards)} card(s) from {cards_path}")
        print(f"  re-entering {len(again)} {'/'.join(redo)} as draft · {dict(st)}")
        if not [c for c in cards if c.get("status") == "draft"]:
            print("  nothing to re-review — every card is already approved or cut.")
        save(cards)
    else:
        # Scope is STATED, never inferred. Three documents say so; the flag used to default to ""
        # which cards everything, so omitting it did exactly what they forbid — silently, and with
        # the run reporting success. Requiring it is what makes the rule true rather than aspirational.
        if a.sources is None and not getattr(a, "all_sources", False):
            sys.exit("--sources is REQUIRED: name what must be carded, e.g.\n"
                     "  --sources \"powerpoint,transcript,junqueira\"\n"
                     "Scope is stated, not inferred from whatever is in the folder. To card every "
                     "extracted file on purpose, pass --all-sources.")
        in_scope, missing = resolve_sources(deck_dir, a.sources or "")
        if missing:
            sys.exit(f"--sources named {missing} but no such file is in {out_dir}/sources/.\n"
                     f"  have: {[os.path.basename(p) for p in resolve_sources(deck_dir, '')[0]]}\n"
                     f"  Scope is stated, so a source you asked for and did not get is an error.")
        # Truncate the audit HERE, not before OCR — it used to be wiped at the top of the run, so a
        # run that aborted on a bad --sources destroyed the PREVIOUS run's author trace. That is
        # exactly how the record of why PTH was left un-clozed was lost: nothing to read but 0 bytes.
        open(os.path.join(out_dir, "author.audit.jsonl"), "w").close()
        # ONE AUTHORING RUN PER FILE. Not one run over all of them: a single call asked to card 8
        # sources returned 125 cards and quality collapsed inside that one response — 65% of clozes
        # came back hintless against a reference deck that hints every one. The same author on a
        # 37-card deck hinted all 37. Per-file keeps every call in the range where it stays careful,
        # and dedup + review then run ACROSS the whole set (step 1b onward), which is where
        # cross-file repetition is supposed to be caught anyway.
        # AUTHOR **AND REVIEW** ONE FILE AT A TIME. Reviewing only after every file was authored
        # meant a file whose cards came back bad was not discovered until all of them had been
        # paid for. Per file, the loop is small, converges fast, and a drifting author is caught
        # at file 2 instead of file 7. Dedup and the transcript check still run across the WHOLE
        # set afterwards, because neither can be judged one file at a time.
        print(f"· step 1 — author + review, ONE FILE AT A TIME ({len(in_scope)} file(s))"
              f"{' (--sources)' if a.sources else ' (all extracted)'}:")
        cards = []
        for i, src in enumerate(in_scope, 1):
            name = os.path.basename(src)
            print(f"\n  ── [{i}/{len(in_scope)}] {name}")
            drafted, cost = author_create(deck_dir, a.model, slug=a.slug, audit_round=i,
                                          sources=[src]); total += cost
            # ids collide across files (each run numbers from 01), so namespace by file index
            for c in drafted:
                c["id"] = f"f{i}-{c.get('id', 'x')}"
            batch = [{**c, "status": "draft", "note": ""} for c in drafted if c.get("text")]
            print(f"     authored {len(batch)} card(s) — reviewing this file now…")
            done = cards                       # already-settled cards from earlier files
            batch, cost = review_fix_loop(batch, deck_dir, a.model, a.max_author_rounds,
                                          mechanical, save=lambda b: save(done + b),
                                          source_hint=src_dir if os.path.isdir(src_dir) else None)
            total += cost
            cards += batch
            save(cards)
            st = Counter(c.get("status") for c in batch)
            print(f"     [{i}/{len(in_scope)}] {name} -> {dict(st)}   ({len(cards)} total, ${total:.2f})")
        print(f"\n  {len(cards)} card(s) from {len(in_scope)} file(s) -> {cards_path}")

        # ── STEP 1b — dedup, by an AGENT ─────────────────────────────────────
        by_id = {c["id"]: c for c in cards}
        dupes, cost = dedup_agent(cards, a.model); total += cost
        print(f"· step 1b — dedup: {len(dupes)} duplicate(s) of {len(cards)} card(s)")
        for dupe_id, keeps_id, why in dupes:
            c = by_id.get(dupe_id)
            if not c or keeps_id not in by_id:
                continue
            c["status"] = "duplicate"; c["note"] = f"duplicate of {keeps_id} — {why}"
            print(f"    {dupe_id} = {keeps_id}: {why[:80]}")
        save(cards)

        # ── STEP 1c — check every card against the transcript ────────────────
        tx = [p for p in in_scope if "transcript" in os.path.basename(p).lower()]
        if tx:
            # Every card still in play — NOT just `draft`. Step 1 now reviews each file as it is
            # authored, so by the time this runs nothing is a draft any more and filtering on that
            # checked exactly zero cards while printing a reassuring "0 unsupported".
            live = [c for c in cards if c.get("status") in ("draft", "approved", "needs-fix")]
            others = [p for p in in_scope if p != tx[0]]
            bad, cost = transcript_agent(live, tx[0], a.model, other_sources=others)
            total += cost
            print(f"· step 1c — transcript check ({os.path.basename(tx[0])}, "
                  f"{len(others)} other source(s) in scope): {len(bad)} of {len(live)} flagged")
            for cid, verdict, why in bad:
                c = by_id.get(cid)
                if not c:
                    continue
                # Each verdict needs a DIFFERENT destination. Routing all three to needs-fix was
                # the bug: it handed the fixer defects no rewrite can repair.
                if verdict == "contradicted":
                    # A wrong fact IS fixable — correct it and re-review.
                    c["status"] = "needs-fix"; c["note"] = f"lecturer contradicts this: {why}"
                elif verdict == "excluded":
                    # He said don't learn it. No rewrite saves it, and cutting it silently on one
                    # agent's reading of a garbled transcript is worse — a human decides.
                    c["status"] = "held"; c["note"] = f"{EXCLUDED_NOTE}{why}"
                else:
                    # low-emphasis is a yield SIGNAL, not a verdict. Printed, never routed.
                    c["note"] = f"low emphasis in lecture: {why}"
                print(f"    [{verdict}] {cid}: {why[:80]}")
            save(cards)
        else:
            print("· step 1c — transcript check SKIPPED: no transcript among the sources")

    # ── STEPS 2–4 — review / fix / re-review (the shared loop, also used by `insert`) ──────────
    cards, cost = review_fix_loop(cards, deck_dir, a.model, a.max_author_rounds, mechanical, save,
                                  source_hint=src_dir if os.path.isdir(src_dir) else None)
    total += cost
    st = Counter(c.get("status") for c in cards)
    print(f"\n── done | {dict(st)} | ${total:.2f}")
    print(f"  every card is accounted for in {cards_path} — grep by status; nothing was dropped")

    approved = [c for c in cards if c.get("status") == "approved"]
    if a.dry_run:
        print(f"DRY RUN — {len(approved)} approved card(s) would be written to {a.deck!r}. Anki untouched.")
        return
    if not approved:
        print("nothing approved — nothing written to Anki."); return
    notes = [{"deckName": a.deck, "modelName": MODEL,
              "fields": {"Text": c.get("text", ""), "Extra": c.get("extra", ""),
                         "Source": c.get("source", "")}, "tags": c.get("tags", [])} for c in approved]
    _write_notes(a.deck, approved, notes, out_dir, suspend_flagged=True, tag_reviewed=True, step="run")
    invoke("sync"); print("· synced")


def cmd_insert(a):
    """Insert an EXISTING Anki deck into the harness's review → fix → re-review loop — the SAME
    loop `run` uses, minus `create` (the cards already exist). Pulls the deck's pipeline cards
    (Custom Cloze), seeds them as drafts, and runs review_fix_loop with a SHAPE-ONLY gate (verbatim-
    source checking needs the rendered sources — a follow-up via --deck-dir). Writes the reviewed/
    fixed result to <work>/out/cards.jsonl, one status per card. Anki is NOT touched — inspect the
    result, then decide about writing the fixes back into the notes."""
    from collections import Counter
    allc = _pull_all(a.deck)
    snap = [c for c in allc if c.get("model") == MODEL]
    if not snap:
        sys.exit(f"no Custom-Cloze cards in {a.deck!r} — is the deck name right, and Anki open?")
    cards = [{"id": str(c["note_id"]), "text": c["fields"].get("Text", ""),
              "extra": c["fields"].get("Extra", ""), "source": c["fields"].get("Source", ""),
              "tags": c.get("tags", []), "status": "draft", "note": ""} for c in snap]
    work = a.deck_dir or os.path.join(HERE, "out", f"insert-{_slug(a.deck)}")
    out_dir = os.path.join(work, "out")
    os.makedirs(out_dir, exist_ok=True)
    cards_path = os.path.join(out_dir, "cards.jsonl")
    open(os.path.join(out_dir, "author.audit.jsonl"), "w").close()

    def save(cs):
        with open(cards_path, "w", encoding="utf-8") as f:
            for c in cs:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

    def mechanical(c):
        return []   # no mechanical shape/template gate — the reviewer judges shape vs the corpus

    src = os.path.abspath(a.source) if a.source else None
    print(f"inserting {len(cards)} card(s) from {a.deck!r} into review→fix→re-review "
          f"({'source-verified' if src else 'shape-only'} gate, split enabled, "
          f"{a.max_author_rounds} fix round(s))…")
    cards, cost = review_fix_loop(cards, work, a.model, a.max_author_rounds, mechanical, save,
                                  source_hint=src)
    st = Counter(c.get("status") for c in cards)
    print(f"\n── {dict(st)}  ·  ${cost:.2f}  ·  {cards_path}")
    print("  Anki untouched — this is the harness's verdict + fixes, not yet written back.\n")
    for c in cards:
        if c.get("status") != "approved":
            print(f"  [{c.get('status'):8}] nid {c['id']}: {(c.get('note') or '')[:150]}")


def cmd_style_pass(a):
    """Cycle every card through a fresh one-card style agent until the file stops changing.

    One card + the compact style guide per call, context cleared between cards, cards run in
    parallel. Stops after `--rounds` passes OR after 2 consecutive passes that changed nothing —
    convergence, not a fixed budget.

    This replaces the review -> note -> fix -> re-review round trip for STYLE. That handoff was
    where the damage happened: the reviewer wrote a note, a separate fixer read it, and the fixer
    routinely rewrote more than the note asked (bone-035-a was told to reuse one word from the
    source and came back restructured with a new defect). One agent that edits the card it is
    looking at cannot misread a note, because there is no note.

    Every card records what each pass did in `style_log`, so a card that keeps getting rewritten
    round after round is visible rather than averaged away."""
    from concurrent.futures import ThreadPoolExecutor
    from collections import Counter
    cards_path = a.cards
    cards = _load_jsonl(cards_path)
    todo = [c for c in cards if c.get("status") in (a.status.split(",") if a.status else [])] \
        if a.status else cards
    print(f"style pass over {len(todo)} of {len(cards)} card(s) in {cards_path}")
    print(f"  model={a.model} effort={a.effort} parallel={a.jobs} max rounds={a.rounds}\n")

    total, quiet = 0.0, 0
    for rnd in range(1, a.rounds + 1):
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            results = list(ex.map(lambda c: style_pass_card(c, a.model, a.effort), todo))
        edits = 0
        for c, (new, why, cost) in zip(todo, results):
            total += cost
            log = c.setdefault("style_log", [])
            if new:
                edits += 1
                before = c["text"]
                c["text"] = new
                blocking = _blocking_of(new)
                c["style_status"] = "blocking" if blocking else "edited"
                log.append({"round": rnd, "changed": True, "why": why,
                            "blocking_after": blocking})
                print(f"  [{rnd}] {c['id']:12} EDITED  {why[:70]}")
                if blocking:
                    print(f"       !! still blocking: {'; '.join(blocking)}")
                _log(os.path.dirname(os.path.abspath(cards_path)), "style-pass",
                     f"{c['id']} r{rnd}: {before[:60]} -> {new[:60]}")
            else:
                c["style_status"] = "clean" if not _blocking_of(c["text"]) else "blocking"
                log.append({"round": rnd, "changed": False, "why": why})
        _write_jsonl(cards_path, cards)
        left = sum(1 for c in todo if _blocking_of(c.get("text", "")))
        print(f"  -- round {rnd}: {edits} edit(s), {left} card(s) still blocking, ${total:.2f}\n")
        quiet = quiet + 1 if edits == 0 else 0
        if quiet >= 2:
            print(f"converged — 2 consecutive passes with no edits (stopped at round {rnd})")
            break
    else:
        print(f"reached the {a.rounds}-round cap")

    st = Counter(c.get("style_status") for c in todo)
    blocking = [c["id"] for c in todo if _blocking_of(c.get("text", ""))]
    print(f"\n── {dict(st)} · ${total:.2f} · {cards_path}")
    if blocking:
        print(f"!! {len(blocking)} card(s) STILL breaking a corpus invariant: {', '.join(blocking)}")
    else:
        print("✓ every card passes every corpus invariant")


def cmd_apply(a):
    """Write a reviewed cards.jsonl (from `insert` or `run`) back to Anki: UPDATE existing notes in
    place (approved cards whose id is a real note id), ADD approved split-offs / new cards as new
    notes, and LEAVE held/cut untouched — held originals stay and get tagged flag::needs-human.
    Updating OVERWRITES a note's current fields, so anything hand-edited since the cards.jsonl was
    produced is replaced. --dry-run prints the plan and writes nothing."""
    cards = [json.loads(l) for l in open(a.cards, encoding="utf-8") if l.strip()]
    dedup = {}
    for c in cards:
        dedup[str(c["id"])] = c                    # last row wins — drops any stale duplicate id
    cards = list(dedup.values())
    approved = [c for c in cards if c.get("status") == "approved"]
    held = [c for c in cards if c.get("status") == "held"]
    existing = set(str(n) for n in invoke("findNotes", query=f'deck:"{a.deck}"'))
    update = [c for c in approved if str(c["id"]).isdigit() and str(c["id"]) in existing]
    add = [c for c in approved if c not in update]
    held_real = [int(c["id"]) for c in held if str(c["id"]).isdigit() and str(c["id"]) in existing]
    print(f"apply plan for {a.deck!r}:")
    print(f"  correct (update in place): {len(update)}")
    print(f"  add (new split-offs/cards): {len(add)}")
    print(f"  held left untouched: {len(held)}  ({len(held_real)} originals will be flagged)")
    if a.dry_run:
        print("DRY RUN — Anki not touched.")
        return
    for c in update:
        invoke("updateNoteFields", note={"id": int(c["id"]),
               "fields": {"Text": c.get("text", ""), "Extra": c.get("extra", ""),
                          "Source": c.get("source", "")}})
    if update:
        invoke("addTags", notes=[int(c["id"]) for c in update], tags="src::harness-fixed")
    if add:
        notes = [{"deckName": a.deck, "modelName": MODEL,
                  "fields": {"Text": c.get("text", ""), "Extra": c.get("extra", ""),
                             "Source": c.get("source", "")},
                  "tags": list(dict.fromkeys((c.get("tags") or []) + ["src::harness-fixed"]))}
                 for c in add]
        _write_notes(a.deck, add, notes, os.path.dirname(os.path.abspath(a.cards)),
                     suspend_flagged=False, tag_reviewed=False, step="apply")
    if held_real:
        invoke("addTags", notes=held_real, tags="flag::needs-human")
    invoke("sync")
    print(f"· corrected {len(update)} · added {len(add)} · flagged {len(held_real)} held · synced")


# ── cli ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="THE pipeline: create -> review -> fix -> re-review (one status file)")
    p.add_argument("deck_dir", help="the deck folder (with slides rendered + sources extractable)")
    p.add_argument("--deck", required=True, help="target Anki deck name")
    p.add_argument("--slug", help="slide slug for slide::<slug>-NN tags")
    p.add_argument("--model", default="claude-sonnet-4-5", help="model for author + review sub-calls")
    p.add_argument("--max-author-rounds", type=int, default=5,
                   help="review->fix rounds before a card is surfaced as `held`. Higher than it was: "
                        "a fix that still breaks a corpus invariant is now caught for free and "
                        "returned to the fixer without spending a review call, so rounds are cheap")
    p.add_argument("--no-media", action="store_true")
    p.add_argument("--sources", default=None,
                   help="WHAT TO CARD — comma-separated substrings of the source filenames, e.g. "
                        "'powerpoint,transcript,junqueira'. Matched case-insensitively on "
                        "alphanumerics only, so 'powerpoint' finds a URL-encoded 'Power Point'. Each must "
                        "match a file in out/sources/ or the run stops. REQUIRED — pass "
                        "--all-sources to deliberately card everything extracted")
    p.add_argument("--all-sources", action="store_true",
                   help="card every extracted file. The explicit form of the old empty --sources")
    p.add_argument("--resume", action="store_true",
                   help="skip create; re-run review->fix over the existing out/cards.jsonl, putting "
                        "held/needs-fix back to draft (approved/cut untouched). Use after a harness "
                        "fix to re-test the exact cards that exposed it")
    p.add_argument("--recheck-approved", action="store_true",
                   help="with --resume: re-review the APPROVED cards too. Use when the reviewer "
                        "itself changed — an approval only means the reviewer of the day passed it")
    p.add_argument("--recheck-flagged", action="store_true",
                   help="with --recheck-approved: re-review only the approved cards the style "
                        "checker actually flags, not every one. Usually what you want — a clean "
                        "card costs a model call to re-confirm what measurement already settled")
    p.add_argument("--dry-run", action="store_true",
                   help="run author+gate+review and report what commit WOULD ship; touch Anki not at all")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("style-pass", help="cycle every card through a fresh 1-card style agent "
                                          "until the file stops changing")
    p.add_argument("cards", help="the cards.jsonl to edit IN PLACE")
    p.add_argument("--model", default="claude-sonnet-4-5")
    p.add_argument("--effort", default="low", help="reasoning effort per card (default: low)")
    p.add_argument("--rounds", type=int, default=5, help="max passes over the file")
    p.add_argument("--jobs", type=int, default=8, help="cards reviewed in parallel")
    p.add_argument("--status", default="", help="only cards with these statuses (comma-separated); "
                                                "default: every card in the file")
    p.set_defaults(fn=cmd_style_pass)

    p = sub.add_parser("slides", help="render slide PDF/.ppt -> JPEGs + slides.jsonl")
    p.add_argument("pdf"); p.add_argument("out_dir"); p.add_argument("slug")
    p.set_defaults(fn=cmd_slides)

    p = sub.add_parser("sources", help="extract PDFs/transcripts -> out/sources/*.txt")
    p.add_argument("deck_dir"); p.set_defaults(fn=cmd_sources)

    p = sub.add_parser("media", help="push slide images into Anki media")
    p.add_argument("out_dir"); p.set_defaults(fn=cmd_media)

    p = sub.add_parser("commit", help="write a reviewed cards.jsonl to Anki (approved + held by status)")
    p.add_argument("cards"); p.add_argument("--deck", required=True)
    p.add_argument("--approved-only", action="store_true",
                   help="ship only status==approved; skip the held cards")
    p.add_argument("--dry-run", action="store_true", help="report what would be written; touch nothing")
    p.set_defaults(fn=cmd_commit)

    p = sub.add_parser("corpus", help="regenerate reference_cards.jsonl from reference_cards.py")
    p.add_argument("--deck", default=None, help="instead, dump this Anki deck (needs --out)")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_corpus)

    p = sub.add_parser("baseline", help="snapshot every ISF card (the diff base wrap compares against)")
    p.add_argument("--root", default=BASELINE_ROOT, help="top deck to snapshot under (default ISF)")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_baseline)

    p = sub.add_parser("wrap", help="capture your Anki edits since baseline -> corrections.jsonl")
    p.add_argument("--root", default=BASELINE_ROOT)
    p.add_argument("--baseline", default=None, help="baseline file (default reference/anki_baseline.jsonl)")
    p.add_argument("--dry-run", action="store_true",
                   help="show edits found; write nothing, don't advance the baseline")
    p.set_defaults(fn=cmd_wrap)

    p = sub.add_parser("insert", help="insert an existing Anki deck into review→fix→re-review (no create)")
    p.add_argument("--deck", required=True, help="Anki deck to pull the cards from")
    p.add_argument("--deck-dir", default=None, help="optional working dir / deck folder with rendered sources")
    p.add_argument("--source", default=None, help="lecture source file/dir the fixer verifies facts against")
    p.add_argument("--model", default="claude-sonnet-4-5")
    p.add_argument("--max-author-rounds", type=int, default=2)
    p.set_defaults(fn=cmd_insert)

    p = sub.add_parser("review-deck", help="audit an existing Anki deck: corpus-derived style check + reviewer (read-only)")
    p.add_argument("--deck", required=True, help="Anki deck name to audit")
    p.add_argument("--model", default="claude-sonnet-4-5", help="reviewer model")
    p.add_argument("--out", default=None)
    p.set_defaults(fn=cmd_review_deck)

    p = sub.add_parser("apply", help="write a reviewed cards.jsonl back to Anki (update existing + add splits)")
    p.add_argument("cards", help="the cards.jsonl to apply (e.g. out/insert-…/out/cards.jsonl)")
    p.add_argument("--deck", required=True, help="the Anki deck")
    p.add_argument("--dry-run", action="store_true", help="print the plan; write nothing")
    p.set_defaults(fn=cmd_apply)

    p = sub.add_parser("sync", help="AnkiConnect sync")
    p.set_defaults(fn=cmd_sync)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
