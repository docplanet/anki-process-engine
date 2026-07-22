#!/usr/bin/env python3
"""review_loop.py — the actual per-card review loop.

For EACH card, one at a time: classify its shape, and ask the model — via the already-authenticated
`claude` CLI in print mode, no API key, no new dependency — to check that one card against the rules
and same-shape example cards, returning a structured verdict {pass|fix|cut}. Every verdict is logged
to out/review.jsonl. Then the corrected cards are re-gated mechanically. `--apply` writes fixes to
the live Anki notes.

The point: "review" stops being an agent reading a batch and asserting "looks good". It is a
deterministic loop whose per-card output you can read, and nothing is called checked except what the
loop logged. The judgment is a model call because "is every testable role clozed / does this read
like the corpus" is reading comprehension, not a regex — but the loop around it is plain Python.

    review_loop.py "<deck>/out/cards.jsonl"                     # judge, write out/review.jsonl
    review_loop.py --deck "ISF::Test 2::Embryology::Week 4"     # judge live notes
    review_loop.py "<cards.jsonl>" --limit 5                    # cheap first pass
    review_loop.py "<cards.jsonl>" --apply                      # push fixes to Anki after judging

Needs the `claude` CLI on PATH and logged in (you already are, running Claude Code).
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from strict_shape import classify_card                                   # noqa: E402
from check_cards import invoke, cards_from_jsonl, cards_from_anki        # noqa: E402

OKF = os.path.join(HERE, "okf")
CORPUS = os.path.join(HERE, "reference", "style_corpus.jsonl")
DEFAULT_MODEL = "claude-sonnet-4-5"

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["pass", "fix", "cut"]},
        "violations": {"type": "array", "items": {
            "type": "object",
            "properties": {"rule": {"type": "string"}, "problem": {"type": "string"}},
            "required": ["rule", "problem"], "additionalProperties": False}},
        "corrected_text": {"type": "string"},
        "corrected_extra": {"type": "string"},
        "note": {"type": "string"},
    },
    "required": ["action", "violations", "note"],
    "additionalProperties": False,
}


def load_rules():
    """The stable system prompt: the governing principle + the rules the loop enforces, read live
    from okf/ so it never drifts from the docs. Identical every call → server-side prompt-cached."""
    parts = ["You are a strict per-card reviewer for an Anki cloze deck. Apply the rules below to "
             "ONE card at a time. Report only real defects; if a construction appears in the "
             "accepted reference corpus, it is not a finding. You REPORT and, when action is "
             "'fix', return the corrected card text — you do not invent new facts, you only "
             "re-cloze / re-mark / re-word within what the card already asserts.\n"]
    for rel in ("index.md", "style.md", "review-checklist.md",
                "rules/card-structure.md", "rules/yield.md",
                "rules/accuracy.md", "rules/no-duplicate.md"):
        p = os.path.join(OKF, rel)
        parts.append(f"\n\n===== {rel} =====\n" + open(p, encoding="utf-8").read())
    return "".join(parts)


def corpus_by_template():
    """Bucket the reference corpus by template so each card is judged against its OWN shape."""
    buckets = {}
    if not os.path.exists(CORPUS):
        return buckets
    for line in open(CORPUS, encoding="utf-8"):
        if not line.strip():
            continue
        rec = json.loads(line)
        text = rec["fields"]["Text"]
        r = classify_card({"type": "cloze", "text": text})
        if r.ok:
            buckets.setdefault(r.template, []).append(text)
    return buckets


def examples_block(buckets):
    """A few real corpus cards per template — the 'example deck' the card is checked against."""
    out = ["\n\n===== reference-corpus examples, by shape (the bar: a card should look like these) ====="]
    for tpl in sorted(buckets):
        out.append(f"\n-- {tpl} --")
        for t in buckets[tpl][:3]:
            out.append("  " + t.replace("\n", " "))
    return "\n".join(out)


def judge(card_id, text, extra, source, template, system_prompt, model):
    """One model call for one card. Returns the parsed verdict dict (+ cost)."""
    user = (f"Check this ONE card against the rules. Its mechanical shape template is {template}; "
            f"compare it to the {template} examples in the system prompt.\n\n"
            f"id: {card_id}\nsource: {source}\n"
            f"Text: {text}\nExtra: {extra}\n\n"
            "Return the structured verdict. action='pass' if it obeys the rules and looks like its "
            "same-shape corpus examples. action='fix' if a rule is violated in a way you can correct "
            "by re-clozing / re-marking / re-wording the SAME facts (give corrected_text, and "
            "corrected_extra only if Extra must change) — never add or remove facts. action='cut' "
            "only if the card should not exist. List every real violation with the rule it breaks. "
            "Chief things to catch that the mechanical gate cannot: a testable role left as visible "
            "prose (not clozed), a facet not marked <u>, a fragment clozed instead of the whole "
            "answer, a cloze that gives away another, a decorative <u> on something that is really "
            "an answer.")
    cmd = ["claude", "-p", user,
           "--system-prompt", system_prompt,
           "--json-schema", json.dumps(VERDICT_SCHEMA),
           "--output-format", "json",
           "--model", model,
           "--allowedTools", "",
           "--strict-mcp-config"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"action": "error", "violations": [], "note": f"claude CLI failed: {r.stderr[:300]}"}, 0.0
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"action": "error", "violations": [], "note": f"unparseable CLI output: {r.stdout[:200]}"}, 0.0
    cost = d.get("total_cost_usd", 0.0) or 0.0
    verdict = d.get("structured_output")
    if verdict is None:                              # fall back to the result string
        try:
            verdict = json.loads(d.get("result", "{}"))
        except json.JSONDecodeError:
            verdict = {"action": "error", "violations": [], "note": "no structured output"}
    return verdict, cost


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cards", nargs="?", help="a cards.jsonl to review (pre-insert)")
    ap.add_argument("--deck", help="review live notes in this Anki deck instead")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, help="review only the first N cards (cheap first pass)")
    ap.add_argument("--only", help="comma-separated card ids to review")
    ap.add_argument("--out", help="verdict log path (default: <cards dir>/review.jsonl or /tmp)")
    ap.add_argument("--apply", action="store_true", help="after judging, push fixes to live Anki notes")
    a = ap.parse_args()
    if not a.cards and not a.deck:
        ap.error("give a cards.jsonl or --deck")

    rows = list(cards_from_jsonl(a.cards) if a.cards else cards_from_anki(f'deck:"{a.deck}"'))
    if a.only:
        want = set(a.only.split(","))
        rows = [r for r in rows if str(r[0]) in want]
    if a.limit:
        rows = rows[:a.limit]

    system_prompt = load_rules() + examples_block(corpus_by_template())
    out_path = a.out or (os.path.join(os.path.dirname(os.path.abspath(a.cards)), "review.jsonl")
                         if a.cards else "/tmp/review.jsonl")

    print(f"reviewing {len(rows)} card(s) with {a.model}, one model call each — log -> {out_path}\n")
    verdicts, total_cost = [], 0.0
    with open(out_path, "w", encoding="utf-8") as log:
        for i, (cid, text, extra, source) in enumerate(rows, 1):
            r = classify_card({"type": "cloze", "text": text})
            template = r.template or "??"
            v, cost = judge(cid, text, extra, source, template, system_prompt, a.model)
            total_cost += cost
            rec = {"id": cid, "template": template, **v}
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log.flush()
            verdicts.append((cid, text, extra, v))
            mark = {"pass": "·", "fix": "✎", "cut": "✂", "error": "!"}.get(v.get("action"), "?")
            vio = "; ".join(x["rule"] for x in v.get("violations", []))
            print(f"  [{i:>2}/{len(rows)}] {mark} {cid:<8} {v.get('action',''):<4} {vio[:70]}")

    n_fix = sum(1 for _, _, _, v in verdicts if v.get("action") == "fix")
    n_cut = sum(1 for _, _, _, v in verdicts if v.get("action") == "cut")
    n_err = sum(1 for _, _, _, v in verdicts if v.get("action") == "error")
    print(f"\n{len(rows)-n_fix-n_cut-n_err} pass · {n_fix} fix · {n_cut} cut · {n_err} error "
          f"| ${total_cost:.2f} | verdicts: {out_path}")

    # re-gate the proposed fixes mechanically before anyone trusts them
    fixes = [(cid, text, v) for cid, text, extra, v in verdicts
             if v.get("action") == "fix" and v.get("corrected_text")]
    if fixes:
        reviewed = out_path.replace("review.jsonl", "cards.reviewed.jsonl")
        with open(reviewed, "w", encoding="utf-8") as f:
            for cid, _old, v in fixes:
                f.write(json.dumps({"id": cid, "type": "cloze", "text": v["corrected_text"]}) + "\n")
        print(f"\nre-gating {len(fixes)} proposed fix(es): {reviewed}")
        subprocess.run([sys.executable, os.path.join(HERE, "strict_shape.py"), reviewed])

    if a.apply and (fixes or n_cut):
        if not a.deck:
            print("\n--apply needs --deck (live notes to update). Skipping.")
            return 1 if n_err else 0
        live = {n["fields"]["Text"]["value"]: n["noteId"]
                for n in invoke("notesInfo", notes=invoke("findNotes", query=f'deck:"{a.deck}"'))}
        applied = 0
        for cid, old_text, v in fixes:
            nid = live.get(old_text)
            if nid is None:
                print(f"  ! {cid}: no live note matches current text — skipped")
                continue
            fields = {"Text": v["corrected_text"]}
            if v.get("corrected_extra"):
                fields["Extra"] = v["corrected_extra"]
            invoke("updateNoteFields", note={"id": nid, "fields": fields})
            applied += 1
        invoke("sync")
        print(f"\napplied {applied} fix(es) to {a.deck!r} and synced. "
              f"{n_cut} cut recommendation(s) left for you to action by hand.")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
