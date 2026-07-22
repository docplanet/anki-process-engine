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
    review_loop.py --deck "<name>" --apply                      # push reviewed fixes to Anki

Verdicts per card: pass · cut · hold · fix.
  * pass  — obeys the rules and looks like its same-shape corpus examples. Recorded to the
            per-deck ledger keyed by the card's CONTENT hash (+ the ruleset hash it was judged
            under). `build_deck commit` will only write a card that has such a signed pass.
  * fix   — a rule is violated in a correctable way; the reviewer returns corrected text, which
            is treated as NEW material and RE-ENTERS the loop (shape gate + a fresh review) under
            a new hash. A fix is never approved by the pass that produced it; it earns its own.
  * hold  — genuine uncertainty ("I cannot confidently judge this / needs a human"). Written to
            out/holds.jsonl with the reason. Uncertainty resolves to hold, NEVER to pass, and a
            held card does not reach the deck. A card unresolved after --max-rounds becomes hold.
  * cut   — should not exist; dropped from the committable set.

Outputs (next to the cards, in out/): cards.reviewed.jsonl (committable pass set, final text),
review.jsonl (every verdict, the log), holds.jsonl (held cards + reasons), .review_ledger.json.
"""
import argparse, concurrent.futures, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from strict_shape import classify_card                                   # noqa: E402
from check_cards import invoke, cards_from_jsonl, cards_from_anki        # noqa: E402
from _harness import card_hash, manifest_hash, read_ledger, write_ledger # noqa: E402

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
            "action": {"type": "string", "enum": ["pass", "fix", "cut", "hold"]},
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
             "EACH card. Report only real defects; if a construction appears in the accepted "
             "reference corpus, it is not a finding.\n"
             "GRADE STYLE STRICTLY AGAINST THE CORPUS, not on whether the card 'reads okay'. The "
             "house style is ONE bold <b> subject, ONE red <i> answer, an optional teal <u> facet — "
             "and the <i> answer ENDS the card. A card that does not match that shape is a defect "
             "even if it is true and readable.\n"
             "Choose exactly one action per card:\n"
             "  pass — obeys every rule AND matches its same-shape corpus examples. If you would "
             "change one mark, cloze, or word, it is NOT a pass.\n"
             "  fix  — the DEFAULT for any card that breaks a WRITTEN rule (two red answers, a "
             "buried answer, a facet left unmarked, an under-clozed testable role, a >3-item or "
             "fragmented enumeration, a decorative <u> that is really the <i> answer). The rules are "
             "decidable — APPLYING them is your job, so FIX, do not hold. Return corrected_text "
             "(and corrected_extra only if Extra must change); do NOT invent or remove facts. The "
             "fix re-enters review from scratch — you propose, you do not approve.\n"
             "    CHAIN FACTS ARE A DEFECT, NOT 'well-formed'. A card that tests two or more distinct "
             "ENTITIES — 'A is converted to B by C', 'X binds Y to activate Z', a <b> subject AND a "
             "<u> that is a second entity AND an <i> that is a third — is WRONG. It is NOT correct to "
             "'test all the nodes' in one card. FIX it to a SINGLE atomic card with ONE red <i> answer "
             "(the primary fact); the other nodes are separate cards' business (authoring covers them), "
             "not a second answer here. One card, one fact, one red answer — always.\n"
             "  cut  — the card should not exist: LOW YIELD (restates a slide bullet with no "
             "specific testable point; vacuous/hedge filler like 'X can happen in various ways' or "
             "'X is important'), a duplicate, or untestable. Prefer cut over hold for low yield.\n"
             "  hold — the LAST resort, for ONE case only: you believe the FACT stated on the card is "
             "factually wrong or contradicts the source, and a human must adjudicate the content. That "
             "is the only reason to hold. NEVER hold for a STYLE or SHAPE issue (that is a `fix`). "
             "NEVER hold because the Source quote is missing, placeholder ('[NEEDS SOURCE]'), or "
             "un-verifiable — a card that cannot be sourced is a `cut`, not a hold; do not defer the "
             "author's job to a human. When a rule applies, apply it; when a card can't stand, cut it. "
             "Hold almost nothing.\n"]
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
    for cid, text, extra, source, template, gate in chunk:
        block = f"\n--- id: {cid} (shape {template}) ---\nText: {text}\nExtra: {extra}\nSource: {source}"
        if gate:
            block += (f"\n!! The mechanical shape gate REJECTS this card for: {', '.join(gate)}. "
                      f"You MUST return action='fix' with corrected_text that resolves it "
                      f"(split a chain fact into linked single-answer cards; put the <i> answer LAST). "
                      f"Do not 'pass' or 'hold' — fix it.")
        lines.append(block)
    lines.append("\n\nFor each card choose pass / fix / cut / hold as defined in your instructions. "
                 "Give corrected_text (and corrected_extra if needed) whenever action='fix'. A STYLE "
                 "or SHAPE violation is always a 'fix' (apply the rule) — never a 'hold'; reserve "
                 "'hold' for a genuine doubt about whether the FACT is true/supported. Cut low-yield "
                 "cards rather than holding them. List every real violation with the rule. Catch what "
                 "the mechanical gate cannot: a testable role left as visible prose, a facet not "
                 "marked <u>, a fragment clozed instead of the whole answer, a cloze that gives away "
                 "another, a decorative <u> that is really the <i> answer, two red <i> answers, and "
                 "an enumeration of ≤3 items split across cards instead of one inline comma cloze.")
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


def review_cards(work, system_prompt, model, batch, workers):
    """One review pass over a list of card dicts (id/text/extra/source). Returns {id: verdict}
    and the pass's total cost. Batched and parallel exactly as before."""
    tagged = [(c["id"], c["text"], c.get("extra", ""), c.get("source", ""),
               classify_card({"type": "cloze", "text": c["text"]}).template or "??", c.get("_gate"))
              for c in work]
    batches = [tagged[i:i + batch] for i in range(0, len(tagged), batch)]
    results, total = {}, 0.0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(judge_batch, b, system_prompt, model): b for b in batches}
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            by_id, cost = fut.result(); total += cost; results.update(by_id)
            acts = [by_id[str(c[0])].get("action") for c in futs[fut]]
            print(f"  batch {i}/{len(batches)} — " + " ".join(acts))
    return results, total


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cards", nargs="?")
    ap.add_argument("--deck")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--batch", type=int, default=10, help="cards per model call (default 10)")
    ap.add_argument("--workers", type=int, default=5, help="parallel batch calls (default 5)")
    ap.add_argument("--max-rounds", type=int, default=3,
                    help="fix→re-review cycles before a still-unresolved card becomes hold (default 3)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", help="comma-separated ids")
    ap.add_argument("--resume", action="store_true",
                    help="skip cards that already have a matching pass in the ledger")
    ap.add_argument("--out")
    ap.add_argument("--apply", action="store_true",
                    help="with --deck: push the reviewed (corrected) text of passed cards to Anki")
    a = ap.parse_args()
    if not a.cards and not a.deck:
        ap.error("give a cards.jsonl or --deck")

    rows = list(cards_from_jsonl(a.cards) if a.cards else cards_from_anki(f'deck:"{a.deck}"'))
    if a.only:
        want = set(a.only.split(",")); rows = [r for r in rows if str(r[0]) in want]
    if a.limit:
        rows = rows[:a.limit]

    out_dir = (os.path.dirname(os.path.abspath(a.cards)) if a.cards else
               os.path.dirname(os.path.abspath(a.out)) if a.out else "/tmp")
    os.makedirs(out_dir, exist_ok=True)
    review_log = a.out or os.path.join(out_dir, "review.jsonl")

    ledger = read_ledger(out_dir)
    mh = manifest_hash()
    orig_text = {str(cid): text for cid, text, _e, _s in rows}   # to detect what a fix changed

    work = [{"id": str(cid), "text": text, "extra": extra, "source": source}
            for cid, text, extra, source in rows]
    if a.resume:
        skipped = [c for c in work if ledger.get(card_hash(c["text"], c["extra"], c["source"]),
                                                 {}).get("action") == "pass"]
        work = [c for c in work if c not in skipped]
        if skipped:
            print(f"resume: {len(skipped)} card(s) already have a matching pass — skipping them")

    system_prompt = load_rules() + examples_block(corpus_by_template())
    passed, held, cut, verdict_log, total_cost = {}, [], [], [], 0.0

    for rnd in range(1, a.max_rounds + 1):
        if not work:
            break
        batches = -(-len(work) // a.batch)
        print(f"\n── round {rnd}/{a.max_rounds}: reviewing {len(work)} card(s) in {batches} "
              f"batch(es) of ≤{a.batch}, {a.workers} parallel, model {a.model}")
        results, cost = review_cards(work, system_prompt, a.model, a.batch, a.workers)
        total_cost += cost
        next_work = []
        for c in work:
            v = results.get(c["id"]) or {"action": "error", "violations": [], "note": "no verdict returned"}
            act = v.get("action")
            verdict_log.append({"id": c["id"], "round": rnd, "action": act,
                                "template": classify_card({"type": "cloze", "text": c["text"]}).template or "??",
                                "violations": v.get("violations", []), "note": v.get("note", "")})
            if act == "pass":
                # COMPOSE THE GATE: a reviewer 'pass' is only a pass if it ALSO clears strict_shape.
                # Otherwise the reviewer approved a gate-illegal card (e.g. a chain fact) — send it
                # back into the fix loop with the gate reasons so it must be corrected, never approved.
                sr = classify_card({"type": "cloze", "text": c["text"]})
                if sr.ok:
                    h = card_hash(c["text"], c["extra"], c["source"])
                    passed[c["id"]] = c
                    ledger[h] = {"id": c["id"], "action": "pass", "card_hash": h, "manifest_hash": mh,
                                 "reviewer": "review_loop", "round": rnd, "note": v.get("note", "")}
                else:
                    verdict_log[-1]["action"] = "fix"
                    verdict_log[-1]["note"] = "reviewer passed but shape gate rejects: " + ", ".join(sr.reasons)
                    next_work.append({**c, "_gate": sr.reasons})
            elif act == "cut":
                cut.append((c, v))
            elif act == "fix" and v.get("corrected_text"):
                nc = dict(c); nc["text"] = v["corrected_text"]
                if v.get("corrected_extra"):
                    nc["extra"] = v["corrected_extra"]
                next_work.append(nc)                       # NEW material — re-enters the full loop
            else:
                # hold, error, or a 'fix' with no corrected_text → cannot confidently pass → HOLD
                reason = v.get("note") or ("uncertain / no verdict" if act in (None, "error")
                                           else "fix proposed without corrected_text")
                held.append((c, {**v, "action": "hold", "note": reason}))
        work = next_work

    # anything still unresolved after the last round: a card that still fails the shape gate is a
    # structural defect the reviewer couldn't fix — CUT it (do not hold a gate-illegal card); a
    # gate-clean card that just never converged is a genuine hold.
    for c in work:
        sr = classify_card({"type": "cloze", "text": c["text"]})
        if not sr.ok:
            cut.append((c, {"action": "cut", "note": f"shape gate unresolved after {a.max_rounds} "
                                                     f"round(s): {', '.join(sr.reasons)}"}))
        else:
            held.append((c, {"action": "hold", "note": f"unresolved after {a.max_rounds} fix round(s)"}))

    # ── write the four artifacts ──────────────────────────────────────────────────────────────
    write_ledger(out_dir, ledger)
    with open(review_log, "w", encoding="utf-8") as f:
        for rec in verdict_log:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    holds_path = os.path.join(out_dir, "holds.jsonl")
    with open(holds_path, "w", encoding="utf-8") as f:
        for c, v in held:
            f.write(json.dumps({**c, "reason": v.get("note", ""),
                                "violations": v.get("violations", [])}, ensure_ascii=False) + "\n")
    committable = os.path.join(out_dir, "cards.reviewed.jsonl")
    with open(committable, "w", encoding="utf-8") as f:
        for cid, c in passed.items():
            f.write(json.dumps({"id": cid, "text": c["text"], "extra": c.get("extra", ""),
                                "source": c.get("source", ""),
                                "tags": c.get("tags", [])}, ensure_ascii=False) + "\n")

    print(f"\n{len(passed)} pass · {len(cut)} cut · {len(held)} hold "
          f"| ${total_cost:.2f} this run")
    print(f"  committable set -> {committable}  (feed this to `build_deck commit`)")
    print(f"  verdict log     -> {review_log}")
    print(f"  ledger          -> {os.path.join(out_dir, '.review_ledger.json')}")
    if held:
        print(f"  HOLDS ({len(held)}) need a human -> {holds_path}")

    if a.apply:
        if not a.deck:
            print("\n--apply needs --deck. Skipping the push to Anki."); return 0
        applied = 0
        for cid, c in passed.items():
            if c["text"] == orig_text.get(cid):
                continue                                   # text unchanged by review — nothing to push
            fields = {"Text": c["text"]}
            if c.get("extra"):
                fields["Extra"] = c["extra"]
            try:
                invoke("updateNoteFields", note={"id": int(cid), "fields": fields}); applied += 1
            except (ValueError, RuntimeError) as e:
                print(f"  ! {cid}: could not apply ({e})")
        invoke("sync")
        print(f"\napplied {applied} reviewed fix(es) to {a.deck!r} and synced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
