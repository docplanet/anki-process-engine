#!/usr/bin/env python3
"""Mechanical card review — everything a script can decide, so a reader doesn't have to.

Per card:
  * every `Source:` quote in Extra is a verbatim substring of THIS deck's source text
  * every answer cloze carries a hint (list cards exempt — their items share one cloze)
  * no card exceeds 3 distinct clozes
  * every referenced image exists in Anki's media collection
Deck-level: the style distribution vs the reference corpus (facet-rate on prose cards, multi-cloze
share) — a clear outlier prints ⚠ UNDER-STYLED and makes the exit non-zero.

~10s for a whole deck. What it CANNOT see — is this worth carding, does it read sensibly, is the
answer recallable — is the read-through in okf/review-checklist.md. Passing this is not a review.

Two modes. **Use the jsonl mode before inserting**: okf/process.md step 9 runs before step 12, so
there is nothing in Anki to query yet.

    check_cards.py "<deck>/out/cards.jsonl"                    # pre-insert (sources auto-found)
    check_cards.py --deck "ISF::Test 2::Histology::Week 3" \
                   --sources "<deck>/out/sources"              # post-insert / repair loop

--sources is a directory of .txt or a single file. With a cards.jsonl it defaults to
<that file's dir>/sources. WITHOUT it the verbatim-quote check — the main one — is skipped, and
the script says so loudly rather than printing a clean-looking 0 flags.
"""
import argparse, glob, html, json, os, re, sys, urllib.request

ANKI = "http://127.0.0.1:8765"
CLOZE = re.compile(r"\{\{c(\d+)::(.*?)\}\}", re.S)
HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "reference", "style_corpus.jsonl")


def _style_dist(texts):
    """Facet-rate on prose cards + cloze-count shares — the two style distributions that a glance
    misses. 'prose' = not a numbered-list card and not an image card, i.e. the cards facets and
    two-cloze structure actually apply to."""
    # Everything is measured over PROSE cards only — numbered-list cards are single-cloze by design
    # and image cards have their own shape, so counting them confounds the comparison (a list-heavy
    # deck would look "under-clozed" for a non-style reason).
    prose = facet = multi = 0
    for t in texts:
        if re.search(r"<br>\s*\d+\.", t) or "<img" in t:
            continue
        prose += 1
        if "<u" in t:
            facet += 1
        if len({n for n, _ in CLOZE.findall(t)}) >= 2:
            multi += 1
    return {"prose": prose,
            "facet_rate": (facet / prose) if prose else 0.0,
            "multicloze_rate": (multi / prose) if prose else 0.0}


def _corpus_dist():
    if not os.path.exists(CORPUS):
        return None
    texts = [json.loads(l)["fields"]["Text"] for l in open(CORPUS, encoding="utf-8") if l.strip()]
    return _style_dist(texts)


def invoke(action, **params):
    body = json.dumps({"action": action, "version": 6, "params": params}).encode()
    req = urllib.request.Request(ANKI, body, {"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if res.get("error"):
        raise RuntimeError(f"{action}: {res['error']}")
    return res["result"]


def norm(s: str) -> str:
    """Comparable text: drop [dynein]-style corrections, punctuation, case, spacing."""
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = s.replace("’", "'").replace("‘", "'").replace("­", "")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def load_sources(spec):
    if not spec:
        return None
    files = [spec] if os.path.isfile(spec) else sorted(glob.glob(os.path.join(spec, "*.txt")))
    if not files:
        sys.exit(f"no source .txt found at {spec!r} — run `build_deck sources <deck dir>` first")
    blob = " ".join(open(f, encoding="utf-8", errors="replace").read() for f in files)
    print(f"sources: {len(files)} file(s), {len(blob):,} chars from {spec}")
    return norm(blob)


def load_media(no_media=False):
    """The set of Anki media filenames (empty if unreachable or skipped). Shared with commit."""
    if no_media:
        return set(), True
    try:
        return set(invoke("getMediaFilesNames", pattern="*")), False
    except Exception as e:
        print(f"!! Anki unreachable ({e}) — skipping the media check")
        return set(), True


def cards_from_jsonl(path):
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        if line.strip():
            c = json.loads(line)
            yield (c.get("id", f"line{i}"), c.get("text", ""), c.get("extra", ""), c.get("source", ""))


def cards_from_anki(query):
    for n in invoke("notesInfo", notes=invoke("findNotes", query=query)):
        f = n["fields"]
        yield (n["noteId"], f["Text"]["value"], f.get("Extra", {}).get("value", ""),
               f.get("Source", {}).get("value", ""))


def check_card(T, E, S, NB, media, no_media=False):
    """Every mechanical per-card flag for one card, as a list of strings (empty = clean).

    This is exactly the logic main() runs per card, factored out so `build_deck commit` can
    call it in-process. NB is the normalized source blob (or None to skip the quote check);
    `media` is the set of Anki media filenames (empty + no_media=True to skip the media check)."""
    f = []
    if NB is not None:
        # strip tags BEFORE finding quotes, else <img src="x.jpg"> reads as a quoted span
        plain = html.unescape(re.sub(r"<[^>]+>", " ", E))
        # Pair quotes strictly left-to-right with NO length floor. A floor made a short
        # quoted term swallow its own closing quote and invert every pairing after it, so
        # the real quotes silently went unchecked while label text got reported instead.
        spans = re.findall(r'"([^"]*)"', plain)
        for q in spans:
            nq = norm(q)
            if len(nq) < 12:
                continue                       # a bare term, not a Source quote — skip, quietly
            if nq not in NB:
                f.append(f'QUOTE not in sources: "{q[:70]}…"')
    # NOTE: there is deliberately no "Extra says cues were joined" check. A previous version
    # grepped the author's own label and produced 42 of 59 flags on the reference deck, 12 of
    # them provably false and none genuine — it penalised honest disclosure and could not see
    # an undisclosed join at all. The verbatim check above is what catches a real join: a
    # sentence stitched from two cues is not a substring of the source.
    cl = CLOZE.findall(T)
    if len({n for n, _ in cl}) > 3:
        f.append("more than 3 distinct clozes")
    if not re.search(r"<br>\s*\d+\.", T):          # list items share a cloze and take no hints
        for _, body in cl:
            if "<i" in body and "::" not in body:
                f.append("answer cloze with no hint")
    if not no_media:
        for img in re.findall(r'<img src="([^"]+)"', T + E):
            if img not in media:
                f.append(f"image not in Anki media: {img}")
    return list(dict.fromkeys(f))                  # de-dup, preserve order


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cards", nargs="?", help="a cards.jsonl to check (pre-insert)")
    ap.add_argument("--deck", help="an Anki deck name to check instead (post-insert)")
    ap.add_argument("--query", help="a raw AnkiConnect search instead of --deck")
    ap.add_argument("--sources", help="dir of extracted source .txt (default: <cards dir>/sources)")
    ap.add_argument("--no-media", action="store_true", help="skip the Anki media check")
    a = ap.parse_args()
    if not a.cards and not (a.deck or a.query):
        ap.error("give a cards.jsonl, or --deck/--query")

    src = a.sources
    if not src and a.cards:                       # <deck>/out/cards.jsonl -> <deck>/out/sources
        guess = os.path.join(os.path.dirname(os.path.abspath(a.cards)), "sources")
        if os.path.isdir(guess):
            src = guess
    NB = load_sources(src)
    if NB is None:
        print("!! NO --sources GIVEN: skipping the verbatim-quote check, which is the main one.\n"
              "!! A clean result below does NOT mean the quotes were checked.")

    media, a.no_media = load_media(a.no_media)

    rows = list(cards_from_jsonl(a.cards) if a.cards
                else cards_from_anki(a.query or f'deck:"{a.deck}"'))
    bad = 0
    deck_texts = [T for _ref, T, _E, _S in rows]
    for ref, T, E, S in sorted(rows, key=lambda r: str(r[3])):
        f = check_card(T, E, S, NB, media, a.no_media)
        if f:
            bad += 1
            print(f"[{ref}] {S}")
            for x in f:
                print(f"    - {x}")
    print(f"\n{len(rows) - bad}/{len(rows)} clean | {bad} with a mechanical flag")

    # ── style distribution vs the corpus ──────────────────────────────────────────────────────
    # The durable fix for under-styling: a whole deck once shipped with facets on ~6% of cards
    # against the corpus's ~86%, and half its cards single-cloze against the corpus's ~7% — a
    # glaring distribution mismatch a glance missed and a lint catches instantly. This is advisory
    # (a subject can genuinely be less facet-heavy), so a clear outlier makes the exit non-zero and
    # you resolve it EITHER by marking the missing facets / clozing the untested roles OR by
    # explaining why this deck is legitimately flatter. Do not just re-run past it.
    cd = _corpus_dist()
    if cd is None:
        print("!! no style corpus at reference/style_corpus.jsonl — skipping the distribution "
              "check (run `build_deck corpus`)")
    else:
        dd = _style_dist(deck_texts)
        print("\nstyle distribution vs corpus:")
        under = []
        for label, key in (("facet <u> on prose cards", "facet_rate"),
                           ("multi-cloze (2–3) share", "multicloze_rate")):
            d, c = dd[key], cd[key]
            flag = c > 0 and d < 0.6 * c            # a clear outlier, not a small gap
            mark = "  ⚠ UNDER-STYLED" if flag else ""
            print(f"  {label:26s} deck {d*100:3.0f}%  |  corpus {c*100:3.0f}%{mark}")
            if flag:
                under.append(label)
        if under:
            print("  → likely unmarked facets and/or untested second roles. Re-run review step 4 "
                  "per card, or explain why this deck is legitimately flatter.")
            bad += 1                                 # make it count: check_cards exits non-zero

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
