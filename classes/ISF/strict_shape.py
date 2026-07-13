#!/usr/bin/env python3
"""STRICT card-shape gate — the mechanical "mold".

Unlike lint_cards.py (which is calibrated to *accept* the reference deck at <2% error and
is deliberately permissive), this module is a hard PASS/FAIL classifier: it sorts a card into
exactly ONE allowed template (T1–T5 or LIST) or REJECTS it with enumerated reason codes. A card
"conforms" iff it matches exactly one template AND trips zero vetoes.

The allowed templates are the real shapes measured in the AnKing Neurogenetics deck (368 cards):
  T1  subject-clozed Q&A     — <b> subject clozed (lower c#) + <i> answer clozed
  T4  subject-second variant — <b> subject clozed (higher c#) + <i> answer clozed
  T2  visible subject        — <b> subject PLAIN (un-clozed), only <i> answer clozed
  T3  facet + answer         — bold plain, <u> facet clozed + <i> answer clozed
  T5  subject+facet+list     — <b> subject + <u> facet + numbered <i> list sharing one c#
  LIST                       — all <i> items share ONE c#, each a single <i> span; bold header

Everything else is rejected. Hints (::) are recorded as a soft flag, never a hard reject
(the reference itself hints only ~60% of cards, answer-weighted).

CLI:
  python strict_shape.py <dir-or-file>            # human histogram
  python strict_shape.py <dir-or-file> --json     # structured JSON
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# Reuse the exact parsing primitives from the legacy linter — no regex duplication.
from lint_cards import _strip, _clozes, _markup_balanced, _is_list, CLOZE_RE

ARROW_RE = re.compile(r"→|&rarr;|-&gt;|->")
MAKES_IT_RE = re.compile(r"\bmakes it (?:a |an |the )?\w+", re.I)
# a list item that bundles "term — a, b, c" (a dash/colon followed by a comma-separated example run)
BUNDLE_RE = re.compile(r".+\s[—–:-]\s+\S.*,\s*\S")


class Reason(str, Enum):
    NO_CLOZE              = "NO_CLOZE"
    FOUR_PLUS_CLOZE       = "FOUR_PLUS_CLOZE"
    NO_ITALIC_ANSWER      = "NO_ITALIC_ANSWER"
    UNCLOZED_ANSWER       = "UNCLOZED_ANSWER"
    TWO_ANSWER_CLOZES     = "TWO_ANSWER_CLOZES"
    CHOPPED_ANSWER        = "CHOPPED_ANSWER"        # one cloze mixing 2+ role tags (b/i/u)
    SUBJECT_NOT_LEADING   = "SUBJECT_NOT_LEADING"   # a <u> facet appears before the <b> subject
    ARROW                 = "ARROW"
    TWO_CONCEPT           = "TWO_CONCEPT"
    LIST_ITEM_MULTICLOZE  = "LIST_ITEM_MULTICLOZE"
    LIST_TERM_EXAMPLES    = "LIST_TERM_EXAMPLES"
    MAPPING_LABEL_UNCLOZED = "MAPPING_LABEL_UNCLOZED"  # a mapping list (>=2 un-clozed <u> row-labels)
    FLATTENED_MAPPING     = "FLATTENED_MAPPING"        # 2+ parallel multi-item clozes (a mapping flattened into blobs)
    TRAILING_FACT         = "TRAILING_FACT"            # a dangling 2nd fact appended after the last cloze
    BUNDLED_ANSWER        = "BUNDLED_ANSWER"           # a single cloze answer bundling two clauses (semicolon)
    TERMINAL_PERIOD       = "TERMINAL_PERIOD"
    UNBALANCED_MARKUP     = "UNBALANCED_MARKUP"
    NO_TEMPLATE_MATCH     = "NO_TEMPLATE_MATCH"


@dataclass
class ShapeResult:
    ok: bool
    template: Optional[str]              # one of T1..T5/LIST iff ok
    reasons: list[str] = field(default_factory=list)
    soft: list[str] = field(default_factory=list)   # advisory (e.g. MISSING_HINT), never blocks
    detail: str = ""


def _roles(s: str) -> set[str]:
    """Which role tags (b/i/u) appear in a string, attribute-aware."""
    return {t for t in ("b", "i", "u") if re.search(rf"<{t}(\s[^>]*)?>", s)}


def _analyze(text: str):
    cl = _clozes(text)                                   # [(num, answer, hint, start)]
    nums = sorted({n for n, *_ in cl})
    ital_nums = sorted({n for (n, a, _h, _s) in cl if "i" in _roles(a)})
    bold_nums = sorted({n for (n, a, _h, _s) in cl if "b" in _roles(a)})
    under_nums = sorted({n for (n, a, _h, _s) in cl if "u" in _roles(a)})
    outside = CLOZE_RE.sub(" ", text)                    # everything NOT inside a cloze
    out_roles = _roles(outside)
    return dict(cl=cl, nums=nums, ital_nums=ital_nums, bold_nums=bold_nums,
                under_nums=under_nums, out_roles=out_roles,
                is_list=_is_list(text))


def _vetoes(text: str, a: dict) -> list[str]:
    R, out = Reason, []
    if not a["cl"]:
        return [R.NO_CLOZE.value]
    if not _markup_balanced(text):
        out.append(R.UNBALANCED_MARKUP.value)
    if _strip(text).endswith("."):
        out.append(R.TERMINAL_PERIOD.value)
    if len(a["nums"]) > 3:
        out.append(R.FOUR_PLUS_CLOZE.value)
    if ARROW_RE.search(text):
        out.append(R.ARROW.value)
    # lead with the SUBJECT — a <u> facet must never precede the <b> subject (ref: 97.3% lead <b>)
    _b = re.search(r"<b(\s[^>]*)?>", text)
    _u = re.search(r"<u(\s[^>]*)?>", text)
    if _b and _u and _u.start() < _b.start():
        out.append(R.SUBJECT_NOT_LEADING.value)
    # answer must be a clozed <i> span. A stray <i> OUTSIDE a cloze is only a defect when it is
    # the ONLY italic (the answer is exposed) — the reference deck legitimately carries incidental
    # italics (species names, emphasis, empty <i>&nbsp;</i> artifacts) alongside a clozed answer.
    i_clozed = bool(a["ital_nums"])
    i_plain = "i" in a["out_roles"]
    if not i_clozed and not i_plain:
        out.append(R.NO_ITALIC_ANSWER.value)
    elif i_plain and not i_clozed:
        out.append(R.UNCLOZED_ANSWER.value)
    # exactly ONE italic-answer cloze number on a non-list card (else siblings self-answer)
    if len(a["ital_nums"]) >= 2 and not a["is_list"]:
        out.append(R.TWO_ANSWER_CLOZES.value)
    # a single cloze must carry ONE role, never mix (e.g. <i>100 g</i> <u>in the liver</u>)
    if any(len(_roles(ans)) >= 2 for (_n, ans, _h, _s) in a["cl"]):
        out.append(R.CHOPPED_ANSWER.value)
    # two concepts joined
    if not a["is_list"] and _two_concept(text, a):
        out.append(R.TWO_CONCEPT.value)
    # list-specific
    if a["is_list"]:
        if len(a["ital_nums"]) >= 2:
            out.append(R.LIST_ITEM_MULTICLOZE.value)
        if any("i" in _roles(ans) and BUNDLE_RE.match(_strip(ans))
               for (_n, ans, _h, _s) in a["cl"]):
            out.append(R.LIST_TERM_EXAMPLES.value)
        # a mapping list ("1. <u>label</u> — <i>value</i>") must CLOZE its row-labels; 2+ un-clozed
        # <u> facets = per-row labels left as context (a lone un-clozed <u> is a legit list HEADER).
        if len(re.findall(r"<u(\s[^>]*)?>", CLOZE_RE.sub(" ", text))) >= 2:
            out.append(R.MAPPING_LABEL_UNCLOZED.value)
    # ATOMICITY (non-list): one fact per card, one item per blank, no dangling second fact.
    if not a["is_list"]:
        # a comma-list inside ONE cloze is a legit memorized set; TWO parallel multi-item clozes
        # is a flattened mapping (ref: 0). Count items per cloze, ignoring commas inside (parens).
        def _items(ans):
            return len([x for x in re.sub(r"\([^)]*\)", "", _strip(ans)).split(",") if x.strip()])
        if sum(1 for (_n, ans, _h, _s) in a["cl"] if _items(ans) >= 2) >= 2:
            out.append(R.FLATTENED_MAPPING.value)
        # a dangling second fact APPENDED after the last cloze via a spaced dash / ; / : + >=2 words
        m = list(CLOZE_RE.finditer(text))
        if m and re.search(r"\s[—–;:]\s+\S+\s+\S", text[m[-1].end():]):
            out.append(R.TRAILING_FACT.value)
        # a semicolon INSIDE a cloze answer bundles two clauses into one blank (ref: ~0)
        if any(";" in _strip(ans) for (_n, ans, _h, _s) in a["cl"]):
            out.append(R.BUNDLED_ANSWER.value)
    # de-dup, preserve order
    seen, uniq = set(), []
    for r in out:
        if r not in seen:
            seen.add(r); uniq.append(r)
    return uniq


def _two_concept(text: str, a: dict) -> bool:
    """Two full concepts crammed into one card. High-precision only — a mere joiner between the
    subject cloze and the answer cloze is NOT two concepts (that's every two-sided card), so we
    fire only on the unambiguous tells the reference deck never uses:
      (1) the "X … makes it a Y" pattern (defines a second entity), or
      (2) a semicolon with a CLOZED <b> subject on BOTH sides (two definitions in one card)."""
    if MAKES_IT_RE.search(_strip(text)):
        return True
    for m in re.finditer(";", text):
        p = m.start()
        b_before = any(s < p and "b" in _roles(ans) for (_n, ans, _h, s) in a["cl"])
        b_after = any(s > p and "b" in _roles(ans) for (_n, ans, _h, s) in a["cl"])
        if b_before and b_after:
            return True
    return False


def _match_template(a: dict) -> Optional[str]:
    b_clozed = bool(a["bold_nums"]); b_plain = "b" in a["out_roles"]
    u_clozed = bool(a["under_nums"])
    i_clozed = bool(a["ital_nums"])
    if a["is_list"]:
        return "T5" if (u_clozed and len(a["nums"]) == 3) else "LIST"
    if not i_clozed:
        return None
    if b_clozed:                                     # subject is clozed -> T1 / T4 by order
        return "T1" if min(a["bold_nums"]) < min(a["ital_nums"]) else "T4"
    if u_clozed:                                     # bold plain + facet clozed -> T3
        return "T3"
    if b_plain:                                      # visible bold subject, answer clozed -> T2
        return "T2"
    return None


def classify_card(card: dict) -> ShapeResult:
    """Mechanical PASS/FAIL. Returns exactly one template (ok=True) OR >=1 reason (ok=False)."""
    if card.get("type") != "cloze":
        return ShapeResult(False, None, [Reason.NO_TEMPLATE_MATCH.value],
                           detail=f"type={card.get('type')!r} (only cloze is shape-gated)")
    text = card.get("text", "")
    a = _analyze(text)
    vetoes = _vetoes(text, a)
    if vetoes:
        return ShapeResult(False, None, vetoes, detail="veto")
    tpl = _match_template(a)
    if tpl is None:
        return ShapeResult(False, None, [Reason.NO_TEMPLATE_MATCH.value], detail="no template")
    # soft advisories (never block; a human decides): answer cloze should carry a hint, and a
    # <u> facet left as un-clozed context is a candidate to blank IF it is testworthy (judgment —
    # the reference leaves 65% of facets as context, so this is a surfaced choice, not a rule).
    soft = []
    ans_have_hint = any(("i" in _roles(ans)) and (h is not None)
                        for (_n, ans, h, _s) in a["cl"])
    if not ans_have_hint:
        soft.append("MISSING_HINT")
    if "u" in a["out_roles"]:
        soft.append("UNCLOZED_FACET")
    return ShapeResult(True, tpl, [], soft, detail=tpl)


def strict_verdict(card: dict) -> tuple[bool, str, list[str]]:
    """Convenience wrapper: (ok, human-readable verdict, reasons) for a single card."""
    r = classify_card(card)
    if r.ok:
        return True, f"shape OK ({r.template})" + (f"; soft={r.soft}" if r.soft else ""), []
    return False, "SHAPE REJECT: " + ", ".join(r.reasons), r.reasons


# ---- CLI -------------------------------------------------------------------
def _iter_cards(target):
    files = ([target] if target.endswith(".jsonl") else
             sorted(glob.glob(os.path.join(target, "*.jsonl"))))
    for fn in files:
        for i, line in enumerate(open(fn, encoding="utf-8")):
            line = line.strip()
            if line:
                yield fn, i + 1, json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="a cards.jsonl file or a dir of them")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows, tpl_hist, reason_hist = [], {}, {}
    n_ok = 0
    for fn, ln, card in _iter_cards(args.target):
        r = classify_card(card)
        rows.append({"id": card.get("id"), "ok": r.ok, "template": r.template,
                     "reasons": r.reasons, "soft": r.soft})
        if r.ok:
            n_ok += 1
            tpl_hist[r.template] = tpl_hist.get(r.template, 0) + 1
        for rc in r.reasons:
            reason_hist[rc] = reason_hist.get(rc, 0) + 1

    total = len(rows)
    if args.json:
        print(json.dumps({"total": total, "conforming": n_ok, "rejected": total - n_ok,
                          "templates": tpl_hist, "reasons": reason_hist, "cards": rows},
                         ensure_ascii=False, indent=2))
    else:
        print(f"{n_ok}/{total} conforming ({total - n_ok} rejected)")
        if tpl_hist:
            print("  templates:", ", ".join(f"{k}={v}" for k, v in sorted(tpl_hist.items())))
        if reason_hist:
            print("  rejections:")
            for k, v in sorted(reason_hist.items(), key=lambda kv: -kv[1]):
                print(f"    {v:3d}  {k}")
        for row in rows:
            if not row["ok"]:
                print(f"    ✗ {row['id']}: {', '.join(row['reasons'])}")
        facet = [r for r in rows if r["ok"] and "UNCLOZED_FACET" in r["soft"]]
        if facet:
            print(f"  facet worklist ({len(facet)} card(s) with a visible facet — cloze if testworthy):")
            for r in facet:
                print(f"    ~ {r['id']}")
    return 0 if n_ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
