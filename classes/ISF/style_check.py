#!/usr/bin/env python3
"""Style checking for ISF cloze cards, with every rule DERIVED FROM THE CORPUS at call time.

Why this exists
---------------
Shape rules kept getting written from intuition and shipped without ever being checked against the
owner's own cards. Three separate rules died that way ("always cloze the <b> subject", "always have
hints", and `strict_shape`'s T1-T5 templates, which were measured from a deprecated AnKing deck).
Each one was enforced for a while against cards that contradicted it.

So no rule here is asserted. Every predicate below is run over `reference/style_corpus.jsonl` on
each call and reported with its measured corpus rate:

  BLOCKING  the corpus violates it ZERO times   -> a real invariant of the house style
  UNUSUAL   the corpus violates it rarely (<5%) -> advisory, reported with the rate
  (silent)  the corpus violates it often        -> not a rule, never reported

If the corpus changes, the rules change with it. A predicate that stops being an invariant stops
blocking automatically. This is the one property `strict_shape.py` could not have.

Deliberately NOT enforced here: anything requiring judgment (is this <b> span a term to recall or
the question's frame? does this hint read like English in the blank?). Those are returned as
QUESTIONS for the reviewer, not verdicts — a regex cannot answer them and should not pretend to.

    python style_check.py --derive              # the invariant table, corpus rates and all
    python style_check.py --deck <cards.jsonl>  # audit a deck's approved cards
    python style_check.py --card '<text>'       # check one card
"""
import json, os, re, sys, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "reference", "style_corpus.jsonl")

CLOZE = re.compile(r"\{\{c(\d+)::([\s\S]*?)\}\}")
TAG = re.compile(r"<(/?)(b|i|u)(?:\s[^>]*)?>")
ROLE_NAME = {"b": "bold subject", "i": "italic answer", "u": "underlined facet"}

UNUSUAL_MAX = 0.05          # corpus rate below this is reported as UNUSUAL, not silently allowed


# ── parsing ──────────────────────────────────────────────────────────────────
def clozes(T):
    """[(num, body, hint)] for each {{cN::body}} or {{cN::body::hint}}."""
    out = []
    for m in CLOZE.finditer(T):
        p = m.group(2).split("::")
        out.append((m.group(1),
                    p[0] if len(p) == 1 else "::".join(p[:-1]),
                    "" if len(p) == 1 else p[-1]))
    return out


def roleseq(T):
    """Opening role tags in document order, e.g. ['b','i'] — the card's role grammar."""
    return [m.group(2) for m in TAG.finditer(T) if not m.group(1)]


def has(s, tag):
    return bool(re.search(r"<" + tag + r"(?:\s[^>]*)?>", s))


def outside(T):
    """The card with every cloze removed — what stays visible on the front."""
    return CLOZE.sub(" ", T)


def _text_only(s):
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"&[a-z]+;|&#\d+;", " ", s)


# ── predicates: each returns True when the card VIOLATES it ──────────────────
def p_u_before_b(T):
    s = roleseq(T)
    return "b" in s and "u" in s and s.index("u") < s.index("b")


def p_gt3_clozes(T):
    return len({n for n, _, _ in clozes(T)}) > 3


def p_two_bold_clozes(T):
    return len({n for n, b, _ in clozes(T) if has(b, "b")}) > 1


def p_two_italic_answers(T):
    """DISTINCT cloze numbers wearing <i>. The same number twice is ONE list cloze, not two answers."""
    return len({n for n, b, _ in clozes(T) if has(b, "i")}) > 1


def p_no_role_markup(T):
    return not roleseq(T)


def p_comma_in_hint(T):
    return any("," in h for _, _, h in clozes(T))


def p_facet_cloze_no_answer(T):
    """A clozed <u> facet doing the answer's job, with no <i> answer clozed anywhere."""
    return (any(has(b, "u") for _, b, _ in clozes(T))
            and not any(has(b, "i") for _, b, _ in clozes(T)))


def p_bold_inside_italic(T):
    return bool(re.search(r"<i(?:\s[^>]*)?>(?:(?!</i>).)*<b[ >]", T, re.S))


def p_unstyled_text_in_cloze(T):
    """Context nouns smuggled inside the braces — card-structure rule 6 wants the braces to hold
    the tested term and nothing else."""
    for _, body, _ in clozes(T):
        stripped = re.sub(r"<(b|i|u)(?:\s[^>]*)?>[\s\S]*?</\1>", "", body)
        if "<img" in body:
            continue
        if re.search(r"[A-Za-z0-9]", _text_only(stripped)):
            return True
    return False


def p_empty_cloze(T):
    return any(not _text_only(b).strip() and "<img" not in b for _, b, _ in clozes(T))


def p_hintless_cloze(T):
    """A cloze with no hint. The image cloze itself never takes one.

    This is the owner's rule stated directly — "EVERY cloze gets a hint" — and it is now also
    measurable, because the reference deck keeps it perfectly. Against the OLD corpus it could not
    be: those hand-built cards were 22% hintless, so the check would have flagged 40 of 84 of them.
    That is exactly why the rule was removed as a "prose invention", replaced with "hint only the
    ones that need it", and a 124-card deck came back 65% hintless."""
    return any("<img" not in b and not h.strip() for _, b, h in clozes(T))


def _answer_side(T):
    """The card REVEALED: {{cN::body::hint}} -> body. Hints must be stripped before looking at what
    trails the answer — a hint sits after </i> INSIDE the braces, so leaving it in makes every
    hinted card look like it has trailing prose. That error is why this rule was missed once."""
    def sub(m):
        p = m.group(2).split("::")
        return p[0] if len(p) == 1 else "::".join(p[:-1])
    return CLOZE.sub(sub, T)


def p_trailing_prose(T):
    """Unstyled words left dangling after the last styled span, on the revealed card.

    This is card-structure.md's "Complete span" rule, finally measured: the <i> answer must cover
    the WHOLE value tested, not a fragment with the rest trailing as prose. The corpus leaves at
    most ONE word (79 of 84 leave none; the 5 exceptions are one word — 'is', 'pH'), so two or more
    is the corpus-derived line.

    Do NOT restate this as 'the last role tag must be <i>' — that is a different claim and the
    corpus breaks it 23 of 84 times (image cards legitimately end on <b>: 'This amino acid is
    {{c1::<b>glycine</b>}}'). Measuring that version is how this rule got discarded as 'not a rule'
    while 13 of 43 approved cards broke it."""
    tail = _answer_side(T)
    ends = list(re.finditer(r"</(?:b|i|u)>", tail))
    if not ends:
        return False
    rest = re.sub(r"<[^>]+>", " ", tail[ends[-1].end():])
    rest = re.sub(r"&nbsp;|&[a-z]+;|&#\d+;", " ", rest)
    return len([w for w in rest.split() if re.search(r"[A-Za-z]", w)]) >= 2


PREDICATES = [
    ("u_before_b", "underlined facet appears before the bold subject",
     p_u_before_b,
     "Order the roles subject-first: <b>subject</b> ... <u>facet</u> ... <i>answer</i>."),
    ("gt3_clozes", "more than 3 distinct clozes",
     p_gt3_clozes,
     "Split the fact into linked cards; 3 is the ceiling."),
    ("two_bold_clozes", "two distinct clozes both wearing <b>",
     p_two_bold_clozes,
     "Distinct clozes are distinctly styled. Make the second node visible context, or split."),
    ("two_italic_answers", "two distinct clozes both wearing <i>",
     p_two_italic_answers,
     "One red answer per card. The extra node is context, or the card splits."),
    ("no_role_markup", "no <b>/<i>/<u> role markup at all",
     p_no_role_markup,
     "Mark the roles: <b> subject, <u> facet, <i> answer."),
    ("comma_in_hint", "a comma inside a hint",
     p_comma_in_hint,
     "Hints are short noun phrases ending in '?' — no commas."),
    ("facet_cloze_no_answer", "a clozed <u> facet with no <i> answer clozed anywhere",
     p_facet_cloze_no_answer,
     "The value being tested is the answer: wrap it in <i>, not <u>. <u> marks the ASPECT asked "
     "about, not the thing recalled."),
    ("bold_inside_italic", "<b> nested inside <i>",
     p_bold_inside_italic,
     "One role per span."),
    ("unstyled_text_in_cloze", "unstyled context text inside the braces",
     p_unstyled_text_in_cloze,
     "The braces hold the tested term and nothing else; scoping nouns stay outside the cloze."),
    ("empty_cloze", "a cloze with no content",
     p_empty_cloze,
     "Remove it or fill it."),
    ("hintless_cloze", "a cloze with no hint",
     p_hintless_cloze,
     "EVERY cloze gets a hint. Substituted into the blank it must read as natural English: "
     "'{{c1::<i>osteocytes</i>::what cells?}}' reads 'Lacunae contain [what cells?]'."),
    ("trailing_prose", "unstyled prose trailing after the answer",
     p_trailing_prose,
     "The <i> answer must cover the WHOLE value tested, so the card ENDS on it. Either extend the "
     "<i> span over the trailing words, or cloze them as the real answer and demote the current "
     "one to a <u> facet. Do not just re-tag the fragment — the trailing words are the answer."),
]


# ── corpus + derivation ──────────────────────────────────────────────────────
def load_corpus(path=CORPUS):
    if not os.path.exists(path):
        return []
    return [json.loads(l)["fields"]["Text"]
            for l in open(path, encoding="utf-8") if l.strip()]


def derive(corpus=None):
    """Measure every predicate against the corpus. Returns [(key, label, fn, fix, hits, n, tier)]."""
    corpus = load_corpus() if corpus is None else corpus
    n = len(corpus) or 1
    out = []
    for key, label, fn, fix in PREDICATES:
        hits = sum(1 for T in corpus if fn(T))
        tier = "BLOCKING" if hits == 0 else ("UNUSUAL" if hits / n <= UNUSUAL_MAX else "allowed")
        out.append((key, label, fn, fix, hits, len(corpus), tier))
    return out


# ── comparable corpus cards ──────────────────────────────────────────────────
def shape(T):
    cl = clozes(T)
    return (len({n for n, _, _ in cl}),
            frozenset(r for _, b, _ in cl for r in "biu" if has(b, r)),
            "<img" in T)


def comparable(T, corpus=None, k=4):
    """Corpus cards structurally like this one. Four relevant examples beat all 84 as
    undifferentiated wallpaper — but only if they really are relevant, so rank by ROLE OVERLAP
    rather than exact-shape tiers. Exact-match tiering hid the most instructive cards: a card
    clozing {b,u} learns most from the corpus cards clozing {b,u,i}, which are precisely the ones
    showing that a clozed <u> is accompanied by a clozed <i>. Image-ness is a hard filter: an
    image card is never a useful model for a prose card."""
    corpus = load_corpus() if corpus is None else corpus
    n_me, roles_me, img_me = shape(T)
    scored = []
    for c in corpus:
        n_c, roles_c, img_c = shape(c)
        if img_c != img_me:
            continue
        score = 2 * len(roles_me & roles_c) - len(roles_me ^ roles_c) - abs(n_me - n_c)
        scored.append((score, c))
    scored.sort(key=lambda s: -s[0])
    return [c for _, c in scored[:k]]


# ── judgment prompts — what a regex must NOT decide ──────────────────────────
def judgment(T):
    qs = []
    vis = outside(T)
    for m in re.finditer(r"<b(?:\s[^>]*)?>([\s\S]*?)</b>", vis):
        term = _text_only(m.group(1)).strip()
        if term:
            qs.append(f"'{term}' is a VISIBLE bold subject. Is it a named term the student must "
                      f"produce (then cloze it), or the general frame of the question (then leave "
                      f"it visible)? Both answers are legitimate — decide for this card.")
    for num, body, hint in clozes(T):
        val = _text_only(body).strip()
        if not val:
            continue
        if hint:
            qs.append(f"c{num}: read the sentence with '[{hint}]' in place of '{val}'. Does it read "
                      f"as natural English?")
        else:
            qs.append(f"c{num} ('{val}') has NO hint. {ANSWER_HINTLESS}")
    if len(clozes(T)) > 1:
        qs.append("Hide each cloze in turn: does any answer give away another (self-answering)?")
    qs.append("Does the <i> answer span cover the WHOLE value tested, or is part of it "
              "left as trailing prose?")
    return qs


ANSWER_HINTLESS = ("That is allowed — 40 of 84 corpus cards leave an <i> answer hintless. Add one "
                   "only if the blank is ambiguous without it.")


# ── the report ───────────────────────────────────────────────────────────────
def check(T, corpus=None):
    corpus = load_corpus() if corpus is None else corpus
    rules = derive(corpus)
    blocking, unusual = [], []
    for key, label, fn, fix, hits, n, tier in rules:
        if tier == "allowed" or not fn(T):
            continue
        rec = {"rule": key, "problem": label, "fix": fix,
               "corpus": f"{hits} of {n} corpus cards do this"}
        (blocking if tier == "BLOCKING" else unusual).append(rec)
    return {"blocking": blocking, "unusual": unusual,
            "comparable": comparable(T, corpus), "judgment": judgment(T),
            "corpus_size": len(corpus)}


def render(T, corpus=None):
    """The report as the text the reviewer actually reads."""
    r = check(T, corpus)
    L = [f"STYLE CHECK — measured against {r['corpus_size']} owner-accepted corpus cards", ""]
    if r["blocking"]:
        L.append("BLOCKING — the corpus NEVER does these. This card cannot be approved as written:")
        for v in r["blocking"]:
            L += [f"  x {v['problem']}", f"      ({v['corpus']})", f"      fix: {v['fix']}"]
    else:
        L.append("BLOCKING — none. No invariant of the corpus is broken.")
    if r["unusual"]:
        L += ["", "UNUSUAL — the corpus does this rarely. Justify or change:"]
        for v in r["unusual"]:
            L += [f"  ? {v['problem']}", f"      ({v['corpus']})", f"      fix: {v['fix']}"]
    L += ["", "COMPARABLE CORPUS CARDS — same structural shape as this card:"]
    L += [f"  {c}" for c in r["comparable"]] or ["  (none of this shape in the corpus)"]
    L += ["", "JUDGMENT — no checker can settle these; you must:"]
    L += [f"  - {q}" for q in r["judgment"]]
    return "\n".join(L)


# ── cli ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--derive", action="store_true", help="print the invariant table")
    g.add_argument("--card", help="check one card's Text")
    g.add_argument("--deck", help="audit a cards.jsonl")
    ap.add_argument("--status", default="approved", help="with --deck: which status to audit")
    a = ap.parse_args()
    corpus = load_corpus()
    if not corpus:
        sys.exit(f"no corpus at {CORPUS} — run: build_deck corpus")

    if a.derive:
        print(f"{len(corpus)} corpus cards\n")
        print(f"{'rule':26} {'corpus':>10}  tier")
        print("-" * 60)
        for key, label, fn, fix, hits, n, tier in derive(corpus):
            print(f"{key:26} {hits:>4}/{n:<5}  {tier}")
        return

    if a.card:
        print(render(a.card, corpus))
        return

    rows = [json.loads(l) for l in open(a.deck, encoding="utf-8") if l.strip()]
    rows = [r for r in rows if r.get("status") == a.status]
    bad = 0
    for r in rows:
        rep = check(r.get("text", ""), corpus)
        if rep["blocking"] or rep["unusual"]:
            bad += 1
            print(f"\n{r['id']}  [{r.get('status')}]")
            for v in rep["blocking"]:
                print(f"   BLOCKING  {v['problem']}  ({v['corpus']})")
            for v in rep["unusual"]:
                print(f"   UNUSUAL   {v['problem']}  ({v['corpus']})")
    print(f"\n{bad} of {len(rows)} '{a.status}' cards have a style finding.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
