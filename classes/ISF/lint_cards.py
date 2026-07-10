#!/usr/bin/env python3
"""Style-lint Anki card JSONL against the house style contract (SKILL.md).

This is the STYLE linter — a superset of validate_cards.py. It returns structured
findings split into:
  - errors:   hard, mechanical rule violations (must fix). Exit code 1 if any.
  - warnings: heuristic/judgment suspects (a human/model adjudicates).

Rules are CALIBRATED to the AnKing Neurogenetics reference deck (the golden test in
tests/test_reference_deck.py asserts the linter errors on <2% of those 368 real cards).

Mechanical rules ENFORCED (errors — validated to not false-positive on the reference deck):
  well-formed JSON; type+required fields; tags present, no spaces; source present;
  balanced {{ }}; a cloze exists; CLOZE CAP (>3 distinct clozes — measured norm is 2, 4+ never);
  no terminal period; balanced markup (attribute-aware); SELF-ANSWERING SHAPE — 2+ DISTINCT
  italic-answer clozes (sibling-reveal, non-list); TWO CONCEPTS (a contrast word with a DISTINCT
  cloze number on each side).
  NOTE: no "must start at c1" error (reference cards ship lone-c2).

Judgment rules FLAGGED (warnings — a human/model adjudicates, never ship-blocking):
  exactly 3 clozes; non-contiguous numbering; SUBJECT-FIRST (circumstantial opener);
  ONE-SIDED DEFINITIONAL (subject not clozed + definition exposed); under-marked / no-<i>;
  over-long NON-LIST note (>25 words; lists excluded).

Usage:
  python lint_cards.py "<cards dir or file>"          # human summary, exit 1 on errors
  python lint_cards.py "<...>" --json                  # structured JSON for agents
  python lint_cards.py "<...>" --errors-only           # ignore warnings for the exit code
"""
import argparse, glob, json, os, re, sys

REQUIRED = {"cloze": ["text"], "basic": ["front", "back"], "image": ["front", "image", "back"]}
CLOZE_RE = re.compile(r"\{\{c(\d+)::(.*?)\}\}", re.S)
LEAD_RE = re.compile(r"^(For|In order|When|Whenever|Prior to|Because|During|Before|After|To |As |If |Once|Upon|Through|Since|While|Given)\b", re.I)
CONTRAST_RE = re.compile(r"\b(whereas|while|in contrast|conversely|as opposed to)\b", re.I)
MAX_CLOZES = 3          # measured Neurogenetics: 2 is the norm, 3 rare, 4+ never. >3 = error; 3 = warn.
# Length WARNING threshold for NON-LIST cards. Measured Neurogenetics non-list cards: median 12,
# p90 20, max 29 words. Lists legitimately run to ~96 words, so they are excluded from this check.
LONG_NOTE_WORDS = 25
# Phrasing that signals a definition (used only to flag a likely one-sided definitional card).
DEFINITIONAL_RE = re.compile(r"\b(is|are|was|were|refers to|defined as|means|called)\b", re.I)


def _strip(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", s).strip()


def _wc(s):
    s = _strip(s)
    return len(s.split()) if s else 0


def _clozes(text):
    """Return [(num, answer, hint_or_None, span_start)] for each cloze occurrence."""
    out = []
    for m in CLOZE_RE.finditer(text):
        inner = m.group(2)
        parts = inner.split("::")
        answer = parts[0]
        hint = parts[-1] if len(parts) > 1 else None
        out.append((int(m.group(1)), answer, hint, m.start()))
    return out


def _markup_balanced(text):
    # Attribute-aware: real Anki markup carries attributes (<u style="">, <b class=...>), so an
    # opening tag is "<b>" OR "<b ...>". Counting only the bare "<b>" mis-flags valid HTML.
    for tag in ("b", "i", "u"):
        opens = len(re.findall(rf"<{tag}(\s[^>]*)?>", text))
        closes = text.count(f"</{tag}>")
        if opens != closes:
            return False
    return True


def _is_list(text):
    """A numbered/multi-line list card — legitimately long and multi-<i>, so length and
    (optionally) multi-italic checks skip it. Matches '1.'/'2)' item markers or 3+ line breaks."""
    return bool(re.search(r"(^|>)\s*\d+[.\)]\s", text)) or len(re.findall(r"<br", text)) >= 3


def lint_card(card, loc):
    """Return (errors, warnings) for one parsed card dict."""
    errors, warnings = [], []
    t = card.get("type")
    if t not in REQUIRED:
        return [f"{loc} bad/missing type: {t!r}"], []
    for k in REQUIRED[t]:
        if not card.get(k):
            errors.append(f"{loc} missing field {k!r}")
    tags = card.get("tags")
    if not isinstance(tags, list) or not tags:
        errors.append(f"{loc} tags missing/empty")
    else:
        for tg in tags:
            if " " in tg:
                errors.append(f"{loc} tag has a space (Anki splits on spaces): {tg!r}")
    if not card.get("source"):
        errors.append(f"{loc} missing source")
    if t == "basic":
        warnings.append(f"{loc} basic Q&A card — text facts must be cloze (two-sided); only image cards may be non-cloze")
    if t != "cloze":
        return errors, warnings

    text = card.get("text", "")
    # --- mechanical (errors) ---
    if text.count("{{") != text.count("}}"):
        errors.append(f"{loc} unbalanced {{{{ }}}}")
    cl = _clozes(text)
    nums = sorted({n for n, *_ in cl})
    if not nums:
        errors.append(f"{loc} no {{{{c#::...}}}} cloze deletion")
    else:
        # NOTE: no "must start at c1" ERROR — the reference deck legitimately ships lone-c2 cards
        # (a c1 sibling was deleted during authoring). Non-contiguity is only a WARNING below.
        if len(nums) > MAX_CLOZES:
            errors.append(f"{loc} {len(nums)} distinct clozes — the reference deck is 2 clozes (64%), 3 rare (5%), 4+ NEVER. Split into a second card")
        if nums != list(range(1, len(nums) + 1)):
            warnings.append(f"{loc} non-contiguous cloze numbering {nums} — number from c1 (a lone c{min(nums)} is OK)")
    if not _markup_balanced(text):
        errors.append(f"{loc} unbalanced <b>/<i>/<u> markup")
    if _strip(text).endswith("."):
        errors.append(f"{loc} terminal period — remove the trailing full stop")

    # --- self-answering SHAPE (errors — mechanically decidable structural leaks) ---
    # ONE-ANSWER rule: the canonical card carries exactly ONE <i> answer. Two+ DISTINCT cloze
    # numbers each wrapping an <i> answer are separate answer-blanks that reveal each other on
    # sibling fronts (the self-answering / "italics all over" defect). A memorized LIST shares ONE
    # cloze number, so it counts as a single italic-answer cloze here and is not flagged.
    italic_cloze_nums = sorted({n for (n, ans, _h, _s) in cl if "<i>" in ans})
    if len(italic_cloze_nums) >= 2 and not _is_list(text):   # a numbered LIST may carry several item values
        cs = ", c".join(str(n) for n in italic_cloze_nums)
        errors.append(f"{loc} {len(italic_cloze_nums)} distinct italic-answer clozes (c{cs}) — a card carries exactly ONE <i> answer; separate answer-blanks reveal each other on sibling fronts (SELF-ANSWERING). Split into atomic cards, or reduce to a single <i> answer")
    # TWO CONCEPTS: a contrast conjunction with a DISTINCT cloze number on each side pairs two
    # standalone facts whose blanks reveal each other across sibling fronts. Keyed on distinct cloze
    # NUMBERS (like the italic check): if both sides share ONE cloze number they are hidden and
    # revealed TOGETHER — a single atomic comparison (e.g. "cal raises {{c1}} whereas kcal raises
    # {{c1}}"), NOT the self-answering defect — so that does not fire. Fires on the canonical
    # two-blank contrast card (c1 one side, c2 the other), which the old len>=3 guard also missed.
    for m in CONTRAST_RE.finditer(text):
        nums_before = {n for (n, _a, _h, s) in cl if s < m.start()}
        nums_after = {n for (n, _a, _h, s) in cl if s > m.start()}
        if nums_before and nums_after and (nums_before ^ nums_after):
            errors.append(f"{loc} TWO CONCEPTS in one card — a contrast word (\"{m.group(0)}\") with a DISTINCT cloze on each side pairs two standalone facts (self-answering across siblings). Split into two atomic cards, or share one cloze number if it is a single comparison")
            break
    # --- judgment (warnings — heuristics a reviewer adjudicates; NOT ship-blocking) ---
    if len(nums) == MAX_CLOZES:
        warnings.append(f"{loc} 3 clozes — 2 is the norm; verify all three are genuinely needed, else split. Check the blanks aren't mutually-inferable (self-answering)")
    # SUBJECT-FIRST (warning): a circumstantial opener burying the first cloze behind ≥6 words of
    # scene-setting. A WARNING, not an error — LEAD_RE fires on a real reference card, so route to
    # review judgment rather than hard-blocking.
    if cl:
        first = min(cl, key=lambda x: x[3])
        pre = _strip(text[: first[3]])
        if pre and LEAD_RE.match(pre) and _wc(pre) >= 6:
            warnings.append(f"{loc} SUBJECT-FIRST: opens with circumstance \"{pre[:40]}…\" before the first cloze — prefer leading with the subject term")
    # ONE-SIDED DEFINITIONAL (warning): a single cloze whose <b> subject sits OUTSIDE every cloze,
    # with definitional phrasing — the definition stays exposed as a permanent giveaway and is never
    # retrieved. WARNING only: a bare label with nothing further to recall may legitimately stay
    # one-sided (the reference deck has many), so a human/model decides. (Lists excluded.)
    subject_outside_cloze = "<b>" in CLOZE_RE.sub("", text)
    if len(nums) == 1 and subject_outside_cloze and DEFINITIONAL_RE.search(_strip(text)) and not _is_list(text):
        warnings.append(f"{loc} ONE-SIDED DEFINITIONAL: <b>subject</b> is not clozed and the definition stays exposed — consider a two-sided cloze (blank the subject too) unless it's a bare label")
    # under-marked: no role color at all (see MARKUP.md)
    if not re.search(r"</?[biu]>", text):
        warnings.append(f"{loc} UNDER-MARKED: no <b>/<i>/<u> color roles — mark subject <b>, facet <u>, answer <i> (see MARKUP.md)")
    elif "<i>" not in text and nums:
        warnings.append(f"{loc} no <i> answer color — the answer/value should be wrapped <i> (see MARKUP.md)")
    # LENGTH (warning, list-aware): non-list cards past the measured p90 (~20 words) are likely
    # over-packed. Lists legitimately run long (~96 words), so skip them entirely.
    if not _is_list(text) and _wc(text) > LONG_NOTE_WORDS:
        warnings.append(f"{loc} long note ({_wc(text)} words) — reference non-list cards are ~10-12 words (p90 20); trim or split")
    return errors, warnings


def lint_paths(target):
    """Lint a dir (all *.jsonl) or a single .jsonl file. Returns a structured report."""
    if os.path.isdir(target):
        files = sorted(glob.glob(os.path.join(target, "*.jsonl")))
    elif os.path.isfile(target):
        files = [target]
    else:
        return {"ok": False, "error": f"not found: {target}", "files": [], "errors": [], "warnings": []}
    all_errors, all_warnings, per_file = [], [], []
    for path in files:
        fn = os.path.basename(path)
        fe, fw = [], []
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            loc = f"{fn}:{i}"
            try:
                card = json.loads(line)
            except Exception as e:
                fe.append(f"{loc} invalid JSON: {e}")
                continue
            e, w = lint_card(card, loc)
            fe += e
            fw += w
        per_file.append({"file": fn, "errors": fe, "warnings": fw})
        all_errors += fe
        all_warnings += fw
    return {"ok": not all_errors, "files": per_file,
            "errors": all_errors, "warnings": all_warnings,
            "error_count": len(all_errors), "warning_count": len(all_warnings)}


def gate(target, no_lint=False):
    """Hard STYLE GATE for sync/build. Prints and sys.exit(1) on any lint ERROR so
    non-conforming cards never reach Anki. Warnings are advisory (printed, not blocking).
    Pass no_lint=True (the caller's --no-lint) to override intentionally."""
    if no_lint:
        return
    rep = lint_paths(target)
    if rep.get("error_count", 0):
        print(f"\nSTYLE LINT FAILED — {rep['error_count']} error(s). Fix them, or pass "
              f"--no-lint to override:", file=sys.stderr)
        for f in rep.get("files", []):
            for e in f["errors"]:
                print("  ERROR " + e, file=sys.stderr)
        sys.exit(1)
    if rep.get("warning_count", 0):
        print(f"(lint gate: 0 errors, {rep['warning_count']} warning(s) — advisory)")


def main():
    ap = argparse.ArgumentParser(description="Style-lint Anki card JSONL against the house contract")
    ap.add_argument("target", help="cards dir or a single .jsonl file")
    ap.add_argument("--json", action="store_true", help="emit structured JSON")
    ap.add_argument("--errors-only", action="store_true", help="exit non-zero only on errors (ignore warnings)")
    a = ap.parse_args()
    rep = lint_paths(a.target)
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(f"lint: {rep.get('error_count', 0)} error(s), {rep.get('warning_count', 0)} warning(s)")
        for f in rep.get("files", []):
            if f["errors"] or f["warnings"]:
                print(f"\n## {f['file']}")
                for e in f["errors"]:
                    print(f"  ERROR  {e}")
                for w in f["warnings"]:
                    print(f"  warn   {w}")
        if rep.get("ok"):
            print("\nOK — no errors" + (f" ({rep['warning_count']} warnings to review)" if rep.get("warning_count") else ""))
    return 1 if rep.get("error_count", 0) else 0


if __name__ == "__main__":
    sys.exit(main())
