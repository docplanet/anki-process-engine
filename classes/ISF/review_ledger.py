#!/usr/bin/env python3
"""Per-card REVIEW LEDGER — the judgment-axis gate, the way lint_cards.py is the shape gate.

lint_cards.py enforces mechanical SHAPE. It CANNOT tell whether a card is a self-answering
leak or nonsense — those are judgment calls a reviewer makes. This ledger records that
judgment PER CARD and lets sync/build refuse to ship a deck until every card has been
individually signed off IN ITS CURRENT FORM.

Why it exists: the leak that motivated it slipped through a holistic review that "found 4,
fixed 4," wrote a tidy prose summary, and silently never adjudicated a 5th card. Prose hides
an un-adjudicated card; a ledger keyed by card identity turns "silently skipped" into
"there is an empty slot the gate refuses to pass." Enforcement replaces persuasion.

IDENTITY: each card is keyed  <filestem>::<ordinal>  (0-based, same ordinal scheme as
sync_anki.py's `key::` tag). The ledger lives in the cards dir as `.review_ledger.json`, so it
travels with the cards.

FRESHNESS: each entry stores a CONTENT HASH of the card's meaning-bearing fields
(text/extra/front/back/image — NOT tags/source, so adding flag::beyond-scope does not void a
verdict, but editing the text does). Edit a card and its hash changes, so its prior verdict
goes STALE and the gate demands a fresh one. This is what makes "once flagged, it can't ship
un-resolved" airtight: a flagged card either (a) stays flagged -> blocked, (b) gets fixed ->
new hash -> must be re-reviewed, or (c) is re-adjudicated clean at the same hash (an audited
override). It cannot silently pass. Insert a line mid-file and every ordinal below shifts ->
those hashes stop matching -> the gate fails closed and demands re-review (never a silent pass).

The gate BLOCKS (sys.exit 1) if ANY current card is:
  - UNREVIEWED — no ledger entry for its key
  - STALE      — entry hash != the card's current content hash (edited since its verdict)
  - FLAGGED    — its current-hash verdict is `flagged` (a known-bad card)

Usage:
  python review_ledger.py status "<cards dir>"                        # coverage/freshness report
  python review_ledger.py status "<cards dir>" --json                 # structured, for agents
  python review_ledger.py gate   "<cards dir>"                        # exit 1 unless all covered+fresh+clean
  python review_ledger.py record "<cards dir>" --key F::N --verdict clean|flagged \
                                 [--resolution fixed|removed|kept] [--note "..."] [--reviewer NAME]
  python review_ledger.py ingest "<cards dir>" --from verdicts.json   # bulk: [{key,verdict,...}, ...]
"""
import argparse, glob, hashlib, json, os, sys

LEDGER_NAME = ".review_ledger.json"
_US = "␟"   # unit separator, so field boundaries can't be spoofed by concatenation


def ledger_path(cards_dir):
    return os.path.join(cards_dir, LEDGER_NAME)


def content_hash(card):
    """SHA over the card's MEANING-bearing fields only (not tags/source): a tag edit
    (e.g. adding flag::beyond-scope) must NOT void a verdict, but a text/extra edit MUST."""
    t = card.get("type")
    if t == "cloze":
        parts = [card.get("text", ""), card.get("extra", "")]
    elif t == "basic":
        parts = [card.get("front", ""), card.get("back", ""), card.get("extra", "")]
    elif t == "image":
        parts = [card.get("front", ""), card.get("back", ""), card.get("image", ""), card.get("extra", "")]
    else:
        parts = [json.dumps(card, sort_keys=True, ensure_ascii=False)]
    return hashlib.sha256(_US.join(parts).encode("utf-8")).hexdigest()[:16]


def load_cards(cards_dir):
    """Return {key: (card, hash)} for every card line, keyed <filestem>::<ordinal> (0-based,
    counting blank lines like sync_anki.py does, so ordinals line up with the `key::` tags)."""
    out = {}
    for path in sorted(glob.glob(os.path.join(cards_dir, "*.jsonl"))):
        fstem = os.path.splitext(os.path.basename(path))[0]
        for i, line in enumerate(open(path, encoding="utf-8")):
            line = line.strip()
            if not line:
                continue
            try:
                card = json.loads(line)
            except Exception:
                continue   # lint gate owns malformed JSON; the ledger just skips it
            out[card["id"] if card.get("id") else f"{fstem}::{i}"] = (card, content_hash(card))
    return out


def load_ledger(cards_dir):
    p = ledger_path(cards_dir)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "entries": {}}


def save_ledger(cards_dir, led):
    with open(ledger_path(cards_dir), "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def status(cards_dir):
    """Classify every current card against the ledger. Returns a structured report."""
    cards = load_cards(cards_dir)
    entries = load_ledger(cards_dir).get("entries", {})
    clean, stale, unreviewed, flagged = [], [], [], []
    for key, (_card, h) in sorted(cards.items()):
        e = entries.get(key)
        if not e:
            unreviewed.append(key)
        elif e.get("hash") != h:
            stale.append(key)
        elif e.get("verdict") == "flagged":
            flagged.append(key)
        else:
            clean.append(key)
    ok = not (stale or unreviewed or flagged)
    return {"ok": ok, "total": len(cards),
            "clean": clean, "stale": stale, "unreviewed": unreviewed, "flagged": flagged,
            "clean_count": len(clean), "stale_count": len(stale),
            "unreviewed_count": len(unreviewed), "flagged_count": len(flagged)}


def record(cards_dir, key, verdict, resolution=None, note=None, reviewer=None):
    """Write/replace one verdict, stamping the card's CURRENT hash. Refuses an unknown key."""
    cards = load_cards(cards_dir)
    if key not in cards:
        sys.exit(f"unknown card key {key!r} — not present in {cards_dir}")
    if verdict not in ("clean", "flagged"):
        sys.exit(f"verdict must be clean|flagged, got {verdict!r}")
    _, h = cards[key]
    led = load_ledger(cards_dir)
    led.setdefault("entries", {})[key] = {"hash": h, "verdict": verdict,
                                          "resolution": resolution, "note": note, "reviewer": reviewer}
    save_ledger(cards_dir, led)
    return led["entries"][key]


def ingest(cards_dir, rows):
    """Bulk-record [{key, verdict, resolution?, note?, reviewer?}, ...], stamping current hashes.
    Returns (n_ok, errors). Unknown keys / bad verdicts are collected, not fatal."""
    cards = load_cards(cards_dir)
    led = load_ledger(cards_dir)
    entries = led.setdefault("entries", {})
    n_ok, errs = 0, []
    for r in rows:
        key, verdict = r.get("key"), r.get("verdict")
        if key not in cards:
            errs.append(f"unknown key {key!r}"); continue
        if verdict not in ("clean", "flagged"):
            errs.append(f"{key}: bad verdict {verdict!r}"); continue
        _, h = cards[key]
        entries[key] = {"hash": h, "verdict": verdict, "resolution": r.get("resolution"),
                        "note": r.get("note"), "reviewer": r.get("reviewer")}
        n_ok += 1
    save_ledger(cards_dir, led)
    return n_ok, errs


def gate(cards_dir, no_review=False):
    """Hard REVIEW GATE for sync/build. sys.exit(1) unless every current card is covered,
    fresh, and not flagged. Pass no_review=True (the caller's --no-review) to override."""
    if no_review:
        return
    rep = status(cards_dir)
    if rep["ok"]:
        print(f"(review gate: {rep['clean_count']}/{rep['total']} cards reviewed clean & current)")
        return
    print(f"\nREVIEW GATE FAILED — {rep['unreviewed_count']} unreviewed, {rep['stale_count']} stale "
          f"(edited since review), {rep['flagged_count']} flagged. Adjudicate them (write the ledger) "
          f"or pass --no-review to override:", file=sys.stderr)
    for k in rep["unreviewed"]:
        print(f"  UNREVIEWED  {k}", file=sys.stderr)
    for k in rep["stale"]:
        print(f"  STALE       {k}  (card changed since its verdict — re-review)", file=sys.stderr)
    for k in rep["flagged"]:
        print(f"  FLAGGED     {k}  (known defect — fix it, which forces a re-review)", file=sys.stderr)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Per-card review ledger (the judgment-axis gate)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("status"); sp.add_argument("cards_dir"); sp.add_argument("--json", action="store_true")
    sub.add_parser("gate").add_argument("cards_dir")
    rp = sub.add_parser("record"); rp.add_argument("cards_dir")
    rp.add_argument("--key", required=True); rp.add_argument("--verdict", required=True)
    rp.add_argument("--resolution"); rp.add_argument("--note"); rp.add_argument("--reviewer")
    ip = sub.add_parser("ingest"); ip.add_argument("cards_dir"); ip.add_argument("--from", dest="src", required=True)
    a = ap.parse_args()

    if a.cmd == "status":
        rep = status(a.cards_dir)
        if a.json:
            print(json.dumps(rep, ensure_ascii=False, indent=2)); return 0
        print(f"review ledger: {rep['clean_count']}/{rep['total']} clean & current  |  "
              f"{rep['unreviewed_count']} unreviewed, {rep['stale_count']} stale, {rep['flagged_count']} flagged")
        for label, keys in (("UNREVIEWED", rep["unreviewed"]), ("STALE", rep["stale"]), ("FLAGGED", rep["flagged"])):
            for k in keys:
                print(f"  {label:11} {k}")
        print("\nOK — all cards reviewed clean & current" if rep["ok"] else "\nNOT READY — gate would block")
        return 0 if rep["ok"] else 1
    if a.cmd == "gate":
        gate(a.cards_dir); return 0
    if a.cmd == "record":
        e = record(a.cards_dir, a.key, a.verdict, a.resolution, a.note, a.reviewer)
        print(f"recorded {a.key}: {e['verdict']} (hash {e['hash']})"); return 0
    if a.cmd == "ingest":
        with open(a.src, encoding="utf-8") as f:
            rows = json.load(f)
        n, errs = ingest(a.cards_dir, rows)
        print(f"ingested {n} verdict(s)" + (f"; {len(errs)} error(s):" if errs else ""))
        for e in errs:
            print("  " + e)
        return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
