#!/usr/bin/env python3
"""build_deck — the one driver for building an Anki deck from lecture material.

`run` is the whole pipeline as four visible steps over ONE status-tracked cards.jsonl:
create -> review -> fix -> re-review. The author and reviewer are constrained claude sub-calls
(the author is read-only; the reviewer is tool-less); the driver is the only writer to Anki.
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
import argparse, datetime, glob, json, os, subprocess, sys, urllib.request

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
        if ext in (".docx", ".doc"):
            # Objectives often ship as a Word doc (this professor's do). They are the coverage
            # contract, so extract them rather than dropping them into `ignored`.
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
def cmd_media(a):
    """Push rendered slide images into Anki's media collection (idempotent)."""
    imgs = sorted(glob.glob(os.path.join(a.out_dir, "slides", "*.jpg")))
    if not imgs:
        sys.exit(f"no JPEGs under {a.out_dir}/slides — run `build_deck.py slides` first")
    for p in imgs:
        invoke("storeMediaFile", filename=os.path.basename(p), path=os.path.abspath(p))
    print(f"stored {len(imgs)} image(s) in Anki media")


# ── the Anki writer ─────────────────────────────────────────────────────────────
def _write_notes(deck, cards, notes, out_dir, suspend_flagged, tag_reviewed, step="commit"):
    """The audited write path: create the model/deck, add notes one at a time (per-card
    reporting), then suspend-flagged / tag-reviewed. Shared by `commit` and `run` so both reuse
    exactly the writer that was hardened over many incidents — not a copy."""
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
# the ONLY writer to Anki. Claude is never the orchestrator here — it is called as two CONSTRAINED
# sub-processes: authoring (read-only tools, returns drafts; author_create/author_fix) and review
# (tool-less; review_all). Neither can edit the rules, reach Anki, or skip a step — the driver spawns them
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


def examples_block():
    """The owner-reviewed corpus cards themselves, dropped into the prompt as the STYLE AUTHORITY.
    style.md is explicit: shape is settled by these cards, NOT by a rule or a template classifier —
    'read the cards, don't consult a rule.' So we present the raw cards, ungrouped, no strict_shape."""
    if not os.path.exists(CORPUS_OUT):
        return ""
    cards = [json.loads(l)["fields"]["Text"].replace("\n", " ")
             for l in open(CORPUS_OUT, encoding="utf-8") if l.strip()]
    header = ("\n\n===== REFERENCE CORPUS — your cards must look like these =====\n"
              "These owner-reviewed cards DEFINE the house style. Match them. Where a written rule "
              "and these cards disagree, THE CARDS WIN. Note they do NOT all cloze the bold subject "
              "— a visible <b> subject is normal here; never force-cloze it.\n")
    return header + "\n".join("  " + c for c in cards)


def _author_system_prompt():
    """Authoring standards: the okf rulebook + corpus examples, oriented to WRITING cards. The
    sub-call reads the sources itself (read-only tools); we hand it the rules it must obey."""
    okf = os.path.join(HERE, "okf")
    parts = ["You are a flashcard AUTHOR for an Anki cloze deck. Turn the deck's OWN source material "
             "into cloze cards that obey the rules below and look like the reference corpus.\n"
             "Governing principle: FAITHFUL TRANSCRIPTION, NOT SYNTHESIS — render the source into "
             "card shape, add nothing, coin no terminology, prefer the source's own words. If a fact "
             "or term is not in the source, it does not go on a card.\n"
             "You have READ-ONLY tools and cannot write files — return every card via the schema.\n"]
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
           "--model", model, "--allowedTools", "Read Grep Glob", "--strict-mcp-config"]
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


def author_create(deck_dir, model, slug=None, audit_round=0):
    """STEP 1 — author cloze cards from the deck's sources. Short, examples-led prompt: the full
    style guide + real corpus examples are already in the system prompt; the task just points to the
    sources and states the card SHAPE plainly."""
    out_dir = os.path.join(deck_dir, "out")
    base = os.path.abspath(out_dir)
    obj_files = glob.glob(os.path.join(out_dir, "sources", "*[Oo]bjective*.txt"))
    obj_text = ("\n\n===== LEARNING OBJECTIVES — every one gets at least one card =====\n" +
                open(obj_files[0], encoding="utf-8", errors="replace").read()[:6000]) if obj_files else ""
    task = (
        f"Author cloze flashcards for this lecture. Read its sources with the Read tool (absolute "
        f"paths): the .txt files in {base}/sources/ (objectives, transcript, slide text) and the slide "
        f"images {base}/slides/*.jpg.\n\n"
        f"THE CARD SHAPE — make your cards LOOK LIKE the reference-corpus examples in your instructions. "
        f"Roles: <b> = subject, <i> = answer, <u> = facet.\n"
        f"  • CLOZE EVERY TESTABLE TERM. If the <b> subject is itself a term the student must RECALL "
        f"(a named structure/entity — 'lacunae', 'osteon', 'canaliculi'), cloze it as c1 — the corpus's "
        f"single most common card clozes BOTH the subject and the answer. Leave the subject VISIBLE only "
        f"when it is the general FRAME of the question, not a word being tested (e.g. '<b>amino acids</b> "
        f"have {{{{c1::<i>(S)</i>}}}} configuration' — 'amino acids' is the frame). Ask: would the student "
        f"need to PRODUCE this word? If yes, cloze it — never leave a testable term as visible prose.\n"
        f"  • The <i> answer is the LAST thing on the card. Nothing testable comes after it.\n"
        f"  • Exactly ONE <i> answer, ONE fact per card. A chain (A→B→C) becomes SEPARATE one-answer cards.\n"
        f"  • Every cloze gets a hint, phrased as an English question.\n\n"
        f"COVERAGE: every numbered objective below must get at least one card.\n"
        f"SOURCE: each card's `extra` = the slide <img> + a VERBATIM `<b>Source:</b> \"quote\"` copied "
        f"from a source you read. If you can't find a real quote for a fact, skip it — never a placeholder.\n"
        f"TAG each: isf::<subject>::<topic>, week::NN, src::okf-gen, slide::"
        + (f"{slug}-NN" if slug else "<slug>-NN") + " (when slide-based).\n" + obj_text)
    return _author_call(task, deck_dir, model, "author", audit_round)


def author_fix(deck_dir, model, needs_fix, audit_round, source_hint=None):
    """STEP 3 — the author rewrites each flagged card. Two powers beyond a plain rewrite:
      • SPLIT — a chain / compound / buried-answer card becomes SEVERAL one-answer cards (never
        resolve a compound by deleting a real fact).
      • VERIFY — when a source is given, check a flagged 'not in source' fact against the lecture
        before removing it; if the lecture supports it, keep the fact and fix the citation instead.
    Returns (list_of_cards, cost). A split reuses the original id for the first card and '<id>-b',
    '<id>-c' for the rest, so the loop can map results back to the card they came from."""
    lines = ["Revise these cards. Each has a PROBLEM to fix. Rules:\n"
             "• Fix ONLY the flagged problem, keep the SAME fact(s), and match the corpus shape: "
             "the <i> answer is the LAST thing (exactly one <i> answer per card), every cloze has an "
             "English-question hint, a verbatim Source quote in `extra`. CLOZE the <b> subject when it "
             "is a term the student must recall (a named structure/entity — 'lacunae', 'osteon'); "
             "leave it visible only when it is the general frame, not a word being tested.\n"
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
    cards, cost = _author_call("\n".join(lines), deck_dir, model, "fix", audit_round)
    return cards, cost


# ── review sub-call (STEP 2 — tool-less; FLAGS a status + note, never rewrites) ───────────────────
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
             "cards below (the style authority) and return one verdict:\n"
             "  approved — it looks like the corpus cards and is worth knowing. Approve ONLY what you "
             "would not change. A visible (un-clozed) <b> subject is fine WHEN it is the general FRAME "
             "of the question (like 'amino acids'); it is a DEFECT when the subject is itself a term the "
             "student must recall (a named structure — 'lacunae', 'osteon') left un-clozed.\n"
             "  needs-fix — it breaks a rule the CORPUS actually follows (a TESTABLE-TERM subject left "
             "un-clozed, <i> answer not last, two red <i> answers, a chain fact that must be split, "
             "under-clozed answer, a fragmented enumeration). Put the SPECIFIC fix in `note`. Do NOT "
             "rewrite the card — the author fixes it from your note.\n"
             "  cut — low yield (restates a bullet, vacuous filler) OR the fact is wrong/unsupported. "
             "Say why in `note`.\n"
             "Grade STYLE against the corpus CARDS, not a remembered rule, and not on whether the card "
             "'reads okay'. If a written rule and the cards disagree, the cards win.\n"]
    for rel in ("index.md", "style.md", "review-checklist.md", "rules/card-structure.md",
                "rules/yield.md", "rules/accuracy.md", "rules/no-duplicate.md"):
        parts.append(f"\n\n===== {rel} =====\n" + open(os.path.join(okf, rel), encoding="utf-8").read())
    return "".join(parts) + examples_block()


def review_all(cards, model, batch=10):
    """Tool-less reviewer over all cards (in batches). Returns ({id: {verdict, note}}, cost)."""
    sysp = _review_system_prompt()
    out, total = {}, 0.0
    for i in range(0, len(cards), batch):
        chunk = cards[i:i + batch]
        lines = ["Review EACH card. Return one verdict per card, keyed by its id.\n"]
        for c in chunk:
            lines.append(f"\n--- id: {c['id']} ---\nText: {c.get('text','')}\n"
                         f"Extra: {c.get('extra','')}\nSource: {c.get('source','')}")
        cmd = ["claude", "-p", "\n".join(lines), "--system-prompt", sysp,
               "--json-schema", json.dumps(REVIEW_SCHEMA), "--output-format", "json",
               "--model", model, "--allowedTools", "", "--strict-mcp-config"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            for c in chunk:
                out[c["id"]] = {"verdict": "needs-fix", "note": f"reviewer error: {r.stderr[:120]}"}
            continue
        d = json.loads(r.stdout)
        total += d.get("total_cost_usd", 0.0) or 0.0
        payload = d.get("structured_output") or (json.loads(d["result"]) if d.get("result") else {})
        for v in payload.get("verdicts", []):
            out[str(v.get("id"))] = {"verdict": v.get("verdict", "needs-fix"), "note": v.get("note", "")}
        for c in chunk:
            out.setdefault(c["id"], {"verdict": "needs-fix", "note": "no verdict returned — re-review"})
    return out, total


def _slug(s):
    return "".join(ch if ch.isalnum() else "-" for ch in s).strip("-").lower()


def cmd_review_deck(a):
    """Feed an EXISTING Anki deck through the harness's tool-less reviewer (read-only). Pulls every
    pipeline card (Custom Cloze) in --deck, runs strict_shape + the reviewer over it, and writes a
    punch-list (verdict + fix-note per card) to --out. Anki is NOT touched — this only assesses. Use
    it to triage a hand-made deck; then fix cards in Anki and `wrap` captures the fixes."""
    from strict_shape import classify_card
    allc = _pull_all(a.deck)
    snap = [c for c in allc if c.get("model") == MODEL]
    if not snap:
        sys.exit(f"no Custom-Cloze cards in {a.deck!r} — is the deck name right, and Anki open?")
    cards = [{"id": str(c["note_id"]), "text": c["fields"].get("Text", ""),
              "extra": c["fields"].get("Extra", ""), "source": c["fields"].get("Source", "")}
             for c in snap]
    print(f"reviewing {len(cards)} Custom-Cloze card(s) from {a.deck!r} "
          f"— {(len(cards) + 9) // 10} tool-less reviewer batch(es)…")
    verdicts, cost = review_all(cards, a.model)
    rows = []
    for c in cards:
        v = verdicts.get(c["id"], {"verdict": "needs-fix", "note": "no verdict returned"})
        shape = classify_card({"type": "cloze", "text": c["text"]})
        rows.append({"note_id": c["id"], "verdict": v["verdict"], "note": v["note"],
                     "shape_ok": bool(shape.ok), "text": c["text"]})
    order = {"cut": 0, "needs-fix": 1, "approved": 2}
    rows.sort(key=lambda r: (order.get(r["verdict"], 1), r["shape_ok"]))
    out = a.out or os.path.join(HERE, "out", f"review-{_slug(a.deck)}.jsonl")
    _write_jsonl(out, rows)
    from collections import Counter
    t = Counter(r["verdict"] for r in rows)
    bad_shape = sum(1 for r in rows if not r["shape_ok"])
    print(f"\n  approved {t.get('approved', 0)}  |  needs-fix {t.get('needs-fix', 0)}  |  "
          f"cut {t.get('cut', 0)}   ·   {bad_shape} fail strict_shape   ·   ${cost:.2f}")
    print(f"  full punch-list -> {out}\n")
    for r in rows:
        if r["verdict"] != "approved":
            flag = "" if r["shape_ok"] else " [shape]"
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
        if not drafts:
            break
        # 2a mechanical marking — flags needs-fix with the exact reason; NEVER deletes a card
        to_review = []
        for c in drafts:
            m = mechanical(c)
            if m:
                c["status"] = "needs-fix"; c["note"] = "; ".join(m)
            else:
                to_review.append(c)
        # 2b tool-less reviewer on the mechanically-clean drafts -> approved / needs-fix / cut
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
      2 review   mechanical gate + tool-less reviewer set each card's status (+ note for fixes)
      3 fix      the author rewrites needs-fix cards from the note, back to draft
      4 re-review  loop 2-3 until nothing is needs-fix (bounded; leftovers -> held, still in the file)
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

    total = 0.0
    print("· OCR slide images -> sources (so figure/bullet quotes are verifiable)…")
    total += ocr_slides(deck_dir, a.model)
    open(os.path.join(out_dir, "author.audit.jsonl"), "w").close()          # fresh audit per run
    src_dir = os.path.join(out_dir, "sources")
    NB = load_sources(src_dir if os.path.isdir(src_dir) else None)
    media, no_media = load_media(a.no_media)

    def save(cards):
        with open(cards_path, "w", encoding="utf-8") as f:
            for c in cards:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

    def mechanical(c):
        """Deterministic checks — PROVENANCE only (verbatim source). SHAPE is judged by the tool-less
        reviewer against the corpus cards; style.md says the corpus stats are 'not limits to enforce',
        so there is NO mechanical shape/template gate (strict_shape no longer governs the process)."""
        return check_card(c.get("text", ""), c.get("extra", ""), c.get("source", ""),
                          NB, media, no_media)

    # ── STEP 1 — create ─────────────────────────────────────────────────────────
    print("· step 1 — authoring draft cards…")
    drafted, cost = author_create(deck_dir, a.model, slug=a.slug, audit_round=0); total += cost
    cards = [{**c, "status": "draft", "note": ""} for c in drafted]
    save(cards)
    print(f"  {len(cards)} drafted -> {cards_path}")

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
        return []   # no mechanical shape/template gate — the tool-less reviewer judges shape vs the corpus

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
    p.add_argument("--max-author-rounds", type=int, default=2,
                   help="author->gate revision rounds before dropping still-failing cards")
    p.add_argument("--no-media", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="run author+gate+review and report what commit WOULD ship; touch Anki not at all")
    p.set_defaults(fn=cmd_run)

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

    p = sub.add_parser("corpus", help="pull the style reference corpus from Anki")
    p.add_argument("--deck", default=CORPUS_DECK)
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

    p = sub.add_parser("review-deck", help="feed an existing Anki deck through the tool-less reviewer (read-only)")
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
