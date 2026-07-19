#!/usr/bin/env python3
"""Mechanical card review — everything a script can decide, so a reader doesn't have to.

Per card:
  * every `Source:` quote in Extra is a verbatim substring of THIS deck's source text
  * every answer cloze carries a hint (list cards exempt — their items share one cloze)
  * no card exceeds 3 distinct clozes
  * every referenced image exists in Anki's media collection

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

    media = set()
    if not a.no_media:
        try:
            media = set(invoke("getMediaFilesNames", pattern="*"))
        except Exception as e:
            print(f"!! Anki unreachable ({e}) — skipping the media check")
            a.no_media = True

    rows = list(cards_from_jsonl(a.cards) if a.cards
                else cards_from_anki(a.query or f'deck:"{a.deck}"'))
    bad = 0
    for ref, T, E, S in sorted(rows, key=lambda r: str(r[3])):
        f = []
        if NB is not None:
            # strip tags BEFORE finding quotes, else <img src="x.jpg"> reads as a quoted span
            plain = html.unescape(re.sub(r"<[^>]+>", " ", E))
            for q in re.findall(r'"([^"]{15,})"', plain):
                if norm(q) and norm(q) not in NB:
                    f.append(f'QUOTE not in sources: "{q[:70]}…"')
        if re.search(r"cues joined|consecutive cues", E, re.I):
            f.append("Extra says cues were JOINED — quote each cue separately")
        cl = CLOZE.findall(T)
        if len({n for n, _ in cl}) > 3:
            f.append("more than 3 distinct clozes")
        if not re.search(r"<br>\s*\d+\.", T):          # list items share a cloze and take no hints
            for _, body in cl:
                if "<i" in body and "::" not in body:
                    f.append("answer cloze with no hint")
        if not a.no_media:
            for img in re.findall(r'<img src="([^"]+)"', T + E):
                if img not in media:
                    f.append(f"image not in Anki media: {img}")
        if f:
            bad += 1
            print(f"[{ref}] {S}")
            for x in dict.fromkeys(f):
                print(f"    - {x}")
    print(f"\n{len(rows) - bad}/{len(rows)} clean | {bad} with a mechanical flag")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
