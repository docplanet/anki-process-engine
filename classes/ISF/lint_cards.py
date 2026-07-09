#!/usr/bin/env python3
"""Style-lint Anki card JSONL against the house style contract (SKILL.md).

This is the STYLE linter — a superset of validate_cards.py. It returns structured
findings split into:
  - errors:   hard, mechanical rule violations (must fix). Exit code 1 if any.
  - warnings: heuristic/judgment suspects (a human/model adjudicates).

Mechanical rules ENFORCED (errors):
  well-formed JSON; type+required fields; tags present, no spaces; source present;
  balanced {{ }}; a cloze exists and starts at c1; CLOZE CAP (>3 distinct clozes — the
  measured Neurogenetics norm is 2, 4+ never); no terminal period on cloze text; balanced markup.

Judgment rules FLAGGED (warnings — cannot be mechanically confirmed):
  exactly 3 clozes (verify not self-answering); 3+ italic answer spans ("italics all over",
  excluding memorized lists); non-contiguous cloze numbering; subject-first (circumstantial
  opener); two-concept smell ("whereas/while" pairing two full clauses); under-marked / no-<i>;
  over-long note.

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
LONG_NOTE_WORDS = 45


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
    for tag in ("b", "i", "u"):
        if text.count(f"<{tag}>") != text.count(f"</{tag}>"):
            return False
    return True


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
        if 1 not in nums:
            errors.append(f"{loc} cloze numbering must start at c1 (found c{min(nums)})")
        if len(nums) > MAX_CLOZES:
            errors.append(f"{loc} {len(nums)} distinct clozes — the reference deck is 2 clozes (64%), 3 rare (5%), 4+ NEVER. Split into a second card")
        if nums != list(range(1, len(nums) + 1)):
            warnings.append(f"{loc} non-contiguous cloze numbering {nums} — renumber c1..cN")
    if not _markup_balanced(text):
        errors.append(f"{loc} unbalanced <b>/<i>/<u> markup")
    if _strip(text).endswith("."):
        errors.append(f"{loc} terminal period — remove the trailing full stop")

    # --- judgment (warnings) ---
    if len(nums) == MAX_CLOZES:
        warnings.append(f"{loc} 3 clozes — 2 is the norm; verify all three are genuinely needed, else split. Check the blanks aren't mutually-inferable (self-answering)")
    # too many italic answer spans — but a memorized LIST legitimately has several (all sharing one cloze)
    from collections import Counter
    freq = Counter(n for n, *_ in cl)
    is_list = any(v >= 2 for v in freq.values())   # a cloze number used 2+ times = numbered list
    ital = len(re.findall(r"<i>", text))
    if ital >= 3 and not is_list:
        warnings.append(f"{loc} {ital} italic answer spans — the answer should usually be ONE <i> span. Multiple italic blanks = the 'italics all over' defect; fold into one answer or split the card")
    # subject-first: circumstantial opener burying the first cloze
    if cl:
        first = min(cl, key=lambda x: x[3])
        pre = _strip(text[: first[3]])
        if pre and LEAD_RE.match(pre) and _wc(pre) >= 6:
            warnings.append(f"{loc} SUBJECT-FIRST: opens with circumstance \"{pre[:40]}…\" before the first cloze — lead with the subject term")
    # two-concept smell
    if len(nums) >= 3 and CONTRAST_RE.search(_strip(text)):
        warnings.append(f"{loc} possible TWO CONCEPTS in one card (\"whereas/while…\") — if each side is a full standalone definition, split into two cards")
    # under-marked: no role color at all (see MARKUP.md)
    if not re.search(r"</?[biu]>", text):
        warnings.append(f"{loc} UNDER-MARKED: no <b>/<i>/<u> color roles — mark subject <b>, facet <u>, answer <i> (see MARKUP.md)")
    elif "<i>" not in text and nums:
        warnings.append(f"{loc} no <i> answer color — the answer/value should be wrapped <i> (see MARKUP.md)")
    if _wc(text) > LONG_NOTE_WORDS:
        warnings.append(f"{loc} long note ({_wc(text)} words) — likely over-packed; consider trimming or splitting")
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
