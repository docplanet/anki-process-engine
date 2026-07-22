#!/usr/bin/env python3
"""review_loop.py — the per-card review loop, BATCHED and PARALLEL.

Checks each card against the rules and its same-shape corpus examples, returning pass/fix/cut per
card. To avoid paying the ~30k-token agent-startup tax once per card, cards are reviewed in BATCHES
(default 10/call) and the batches run in PARALLEL — so one deck is a handful of concurrent `claude`
calls, not one slow call per card. Every card still gets its own logged verdict; batching only
amortizes the fixed per-call overhead. Uses the authenticated `claude` CLI (no API key, no new dep).

    review_loop.py "<deck>/out/cards.jsonl"                     # judge -> out/review.jsonl
    review_loop.py --deck "ISF::Test 2::Biochemistry::Protein Structures"
    review_loop.py "<cards.jsonl>" --resume                     # skip cards already in the partial
    review_loop.py "<cards.jsonl>" --batch 10 --workers 5       # tune
    review_loop.py --deck "<name>" --apply                      # push fixes to Anki after judging
"""
import argparse, concurrent.futures, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from strict_shape import classify_card                                   # noqa: E402
from check_cards import invoke, cards_from_jsonl, cards_from_anki        # noqa: E402

OKF = os.path.join(HERE, "okf")
CORPUS = os.path.join(HERE, "reference", "style_corpus.jsonl")
DEFAULT_MODEL = "claude-sonnet-4-5"

# One batch call returns an array of per-card verdicts, each keyed by the card id.
BATCH_SCHEMA = {
    "type": "object",
    "properties": {"verdicts": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "action": {"type": "string", "enum": ["pass", "fix", "cut"]},
            "violations": {"type": "array", "items": {
                "type": "object",
                "properties": {"rule": {"type": "string"}, "problem": {"type": "string"}},
                "required": ["rule", "problem"], "additionalProperties": False}},
            "corrected_text": {"type": "string"},
            "corrected_extra": {"type": "string"},
            "note": {"type": "string"},
        },
        "required": ["id", "action", "violations", "note"], "additionalProperties": False}}},
    "required": ["verdicts"], "additionalProperties": False,
}


def load_rules():
    parts = ["You are a strict per-card reviewer for an Anki cloze deck. Apply the rules below to "
             "EACH card you are given. Report only real defects; if a construction appears in the "
             "accepted reference corpus, it is not a finding. When action is 'fix', return the "
             "corrected card text — do not invent or remove facts, only re-cloze / re-mark / "
             "re-word what the card already asserts.\n"]
    for rel in ("index.md", "style.md", "review-checklist.md", "rules/card-structure.md",
                "rules/yield.md", "rules/accuracy.md", "rules/no-duplicate.md"):
        parts.append(f"\n\n===== {rel} =====\n" + open(os.path.join(OKF, rel), encoding="utf-8").read())
    return "".join(parts)


def corpus_by_template():
    buckets = {}
    if not os.path.exists(CORPUS):
        return buckets
    for line in open(CORPUS, encoding="utf-8"):
        if line.strip():
            rec = json.loads(line)
            r = classify_card({"type": "cloze", "text": rec["fields"]["Text"]})
            if r.ok:
                buckets.setdefault(r.template, []).append(rec["fields"]["Text"])
    return buckets


def examples_block(buckets):
    out = ["\n\n===== reference-corpus examples, by shape (a card should look like these) ====="]
    for tpl in sorted(buckets):
        out.append(f"\n-- {tpl} --")
        out += ["  " + t.replace("\n", " ") for t in buckets[tpl][:3]]
    return "\n".join(out)


def judge_batch(chunk, system_prompt, model):
    """One `claude` call for a batch of cards. Returns {id: verdict} and the call's cost."""
    lines = ["Review EACH of these cards. Return one verdict per card, keyed by its id.\n"]
    for cid, text, extra, source, template in chunk:
        lines.append(f"\n--- id: {cid} (shape {template}) ---\nText: {text}\nExtra: {extra}\nSource: {source}")
    lines.append("\n\nFor each card: action='pass' if it obeys the rules and looks like its "
                 "same-shape corpus examples; 'fix' if a rule is violated in a way you can correct "
                 "by re-clozing / re-marking / re-wording the SAME facts (give corrected_text, and "
                 "corrected_extra only if Extra must change); 'cut' only if it should not exist. "
                 "List every real violation with the rule. Catch what the mechanical gate cannot: a "
                 "testable role left as visible prose, a facet not marked <u>, a fragment clozed "
                 "instead of the whole answer, a cloze that gives away another, a decorative <u> on "
                 "something that is really an <i> answer.")
    cmd = ["claude", "-p", "\n".join(lines),
           "--system-prompt", system_prompt, "--json-schema", json.dumps(BATCH_SCHEMA),
           "--output-format", "json", "--model", model, "--allowedTools", "", "--strict-mcp-config"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {c[0]: {"action": "error", "violations": [], "note": f"CLI failed: {r.stderr[:200]}"} for c in chunk}, 0.0
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {c[0]: {"action": "error", "violations": [], "note": "unparseable CLI output"} for c in chunk}, 0.0
    cost = d.get("total_cost_usd", 0.0) or 0.0
    payload = d.get("structured_output") or (json.loads(d["result"]) if d.get("result") else {})
    by_id = {str(v.get("id")): v for v in payload.get("verdicts", [])}
    # any card the model skipped -> mark error so it's visible, never silently dropped
    for cid, *_ in chunk:
        by_id.setdefault(str(cid), {"action": "error", "violations": [], "note": "no verdict returned"})
    return by_id, cost


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cards", nargs="?")
    ap.add_argument("--deck")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--batch", type=int, default=10, help="cards per model call (default 10)")
    ap.add_argument("--workers", type=int, default=5, help="parallel batch calls (default 5)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", help="comma-separated ids")
    ap.add_argument("--resume", action="store_true", help="skip ids already in <out>.partial.jsonl")
    ap.add_argument("--out")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if not a.cards and not a.deck:
        ap.error("give a cards.jsonl or --deck")

    rows = list(cards_from_jsonl(a.cards) if a.cards else cards_from_anki(f'deck:"{a.deck}"'))
    if a.only:
        want = set(a.only.split(",")); rows = [r for r in rows if str(r[0]) in want]
    if a.limit:
        rows = rows[:a.limit]

    out_path = a.out or (os.path.join(os.path.dirname(os.path.abspath(a.cards)), "review.jsonl")
                         if a.cards else "/tmp/review.jsonl")
    done = {}                                        # id -> prior verdict (from a saved partial)
    if a.resume:
        for cand in (out_path.replace(".jsonl", ".partial.jsonl"), out_path):
            if os.path.exists(cand):
                for l in open(cand):
                    if l.strip():
                        v = json.loads(l); done[str(v["id"])] = v
                break
    todo = [r for r in rows if str(r[0]) not in done]

    # attach each card's template, then split into batches
    tagged = [(cid, text, extra, source, classify_card({"type": "cloze", "text": text}).template or "??")
              for cid, text, extra, source in todo]
    batches = [tagged[i:i + a.batch] for i in range(0, len(tagged), a.batch)]
    system_prompt = load_rules() + examples_block(corpus_by_template())

    print(f"reviewing {len(todo)} card(s) ({len(done)} resumed) in {len(batches)} batch(es) of "
          f"≤{a.batch}, {a.workers} in parallel, model {a.model}\n")
    results, total_cost = {}, 0.0
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(judge_batch, b, system_prompt, a.model): b for b in batches}
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            by_id, cost = fut.result(); total_cost += cost; results.update(by_id)
            acts = [by_id[str(c[0])].get("action") for c in futs[fut]]
            print(f"  batch {i}/{len(batches)} done — " + " ".join(acts))

    # merge resumed + new, in original deck order; write per-card log
    merged = []
    for cid, text, extra, source in rows:
        v = results.get(str(cid)) or done.get(str(cid))
        if v is None:
            continue
        merged.append((cid, text, extra, v))
    with open(out_path, "w", encoding="utf-8") as log:
        for cid, text, extra, v in merged:
            rec = {"id": cid, "template": classify_card({"type": "cloze", "text": text}).template or "??", **v}
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")

    n = {k: sum(1 for _, _, _, v in merged if v.get("action") == k) for k in ("pass", "fix", "cut", "error")}
    print(f"\n{n['pass']} pass · {n['fix']} fix · {n['cut']} cut · {n['error']} error "
          f"| ${total_cost:.2f} this run | {len(merged)} verdicts -> {out_path}")

    fixes = [(cid, text, v) for cid, text, extra, v in merged
             if v.get("action") == "fix" and v.get("corrected_text")]
    if fixes:
        reviewed = os.path.splitext(out_path)[0] + ".cards.reviewed.jsonl"  # never clobber the log
        with open(reviewed, "w", encoding="utf-8") as f:
            for cid, _t, v in fixes:
                f.write(json.dumps({"id": cid, "type": "cloze", "text": v["corrected_text"]}) + "\n")
        print(f"\nre-gating {len(fixes)} proposed fix(es): {reviewed}")
        subprocess.run([sys.executable, os.path.join(HERE, "strict_shape.py"), reviewed])

    if a.apply and fixes:
        if not a.deck:
            print("\n--apply needs --deck. Skipping."); return 0
        live = {nn["fields"]["Text"]["value"]: nn["noteId"]
                for nn in invoke("notesInfo", notes=invoke("findNotes", query=f'deck:"{a.deck}"'))}
        applied = 0
        for cid, old_text, v in fixes:
            nid = live.get(old_text)
            if nid is None:
                print(f"  ! {cid}: no live note matches current text — skipped"); continue
            f = {"Text": v["corrected_text"]}
            if v.get("corrected_extra"):
                f["Extra"] = v["corrected_extra"]
            invoke("updateNoteFields", note={"id": nid, "fields": f}); applied += 1
        invoke("sync")
        print(f"\napplied {applied} fix(es) to {a.deck!r} and synced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
