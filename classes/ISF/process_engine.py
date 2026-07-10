#!/usr/bin/env python3
"""Process engine — a semi-deterministic staged state machine for card generation.

The engine holds the PROCESS as an explicit state machine and steps an agent through it
one unit at a time, keyed by a stable id. Skipping/reordering is structurally impossible:
`next_step()` is a PURE function returning the monotonic frontier; `submit_step()` refuses
any submit whose stage != the target's current stage. Crash-safety falls out — next_step
mutates nothing, submit_step writes atomically (temp + os.replace) and is idempotent.

Per anchor unit (e.g. one slide) the stages are:

  scaffold ─▶ emphasis ─▶ spec_propose ─▶ spec_verify ─▶ generate ─▶ (fan to cards)
  (capture   (transcript  (agent A:        (agent B:       (write N
   slide as   emphasis +   n_cards 0..4     AGREE → mint     JSONL cards
   reveal)    keywords)    + concepts)      DISAGREE →       id=<unit>::cK,
                                            escalate)        extra=slide)

Each minted card then runs the per-CARD stages:  accuracy ─▶ style ─▶ done
(both HARD gates that write a verdict to review_ledger — the ship gate).

Two state files live side by side in the cards dir, kept deliberately separate:
  .process_state.json  — WHERE every unit/card is (this engine).
  .review_ledger.json  — the ship VERDICTS (review_ledger.py). The engine feeds it; the
                         immutable lint+ledger gate at build/sync stays the real backstop.

Dual use, mirroring review_ledger.py: importable library + CLI (`python process_engine.py ...`).
The process_engine_mcp.py FastMCP shim wraps these same functions.
"""
import argparse, glob, hashlib, json, os, re, shutil, subprocess, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import review_ledger  # sibling — stages accuracy/style write ship verdicts here
import lint_cards     # sibling — the SHAPE linter; its errors mechanically force a 'flagged' verdict

STATE_NAME = ".process_state.json"
ANCHOR_DIR = ".anchor"                       # per-unit source text, extracted at init
# Per-card flow: generate the FACT (no markup) → verify accuracy + structure → apply markup roles →
# review style. Content and markup are authored by separate agents so each has ONE job; the two
# review stages (accuracy, style) are the higher-tier reviewers and each writes a ship verdict.
STAGES = ["scaffold", "emphasis", "spec_propose", "spec_verify", "generate", "accuracy", "markup", "style"]
UNIT_STAGES = ["scaffold", "emphasis", "spec_propose", "spec_verify", "generate"]
CARD_STAGES = ["accuracy", "markup", "style"]
# Suggested model tier per stage, surfaced to the driver so producers run cheap and reviewers run
# strong: producers (fact, markup) = sonnet; independent reviewers (structure, style) = opus.
STAGE_MODEL = {"scaffold": "sonnet", "emphasis": "sonnet", "spec_propose": "sonnet",
               "spec_verify": "opus", "generate": "sonnet", "accuracy": "opus",
               "markup": "sonnet", "style": "opus", "coverage": "opus"}
MAX_CARDS_CAP = 4

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", ".claude", "skills", "anki-cards"))
SKILL = os.path.join(_SKILL_DIR, "SKILL.md")
MARKUP = os.path.join(_SKILL_DIR, "MARKUP.md")
HIGHYIELD = os.path.join(_SKILL_DIR, "HIGH-YIELD.md")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def _mint_unit_id(deck, anchor_ref):
    return "u_" + hashlib.sha256(f"{deck}|{anchor_ref}".encode()).hexdigest()[:8]


def _mint_card_ids(unit_id, n):
    return [f"{unit_id}::c{k}" for k in range(1, n + 1)]


# ── state store I/O (mirror review_ledger load/save; save is atomic) ──────────────────
def state_path(cards_dir):
    return os.path.join(cards_dir, STATE_NAME)


def load_state(cards_dir):
    p = state_path(cards_dir)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(cards_dir, state):
    state["updated"] = _now()
    p = state_path(cards_dir)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, p)   # atomic


# ── anchor enumeration (MVP: unit == slide, one per PDF page / form-feed) ──────────────
def _pdf_pages(path):
    out = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"pdftotext failed on {path}: {out.stderr.strip()}")
    return out.stdout.split("\f")


def _render_page(pdf_path, page, out_prefix, dpi=120):
    """Render ONE PDF page to a PNG via pdftoppm (poppler) so image/diagram slides whose text
    layer is empty still carry their real content (figures, captions). Returns the PNG path or None."""
    if not shutil.which("pdftoppm"):
        return None
    try:
        subprocess.run(["pdftoppm", "-png", "-singlefile", "-r", str(dpi),
                        "-f", str(page), "-l", str(page), pdf_path, out_prefix],
                       check=True, capture_output=True)
    except Exception:
        return None
    png = out_prefix + ".png"
    return png if os.path.exists(png) else None


def _text_pages(path):
    txt = open(path, encoding="utf-8").read()
    if "\f" in txt:
        return txt.split("\f")
    marks = re.split(r"(?im)^\s*slide\s+\d+\b.*$", txt)   # "Slide 12 ..." headers
    return marks if len(marks) > 1 else [txt]


def _enumerate_units(cfg, base_dir):
    """Return [{anchor_ref, content}] for the configured anchor. MVP supports unit=slide."""
    anchor = cfg["anchor"]
    kind = anchor["unit"]
    if kind != "slide":
        raise NotImplementedError(f"anchor.unit '{kind}' is an expansion item (MVP: slide only)")
    role = anchor.get("source_role", "slides")
    src = (next((s for s in cfg["sources"] if s.get("role") == role and s.get("anchor")), None)
           or next((s for s in cfg["sources"] if s.get("role") == role), None))
    if not src:
        raise RuntimeError(f"no anchor source with role '{role}' in job sources")
    src_path = os.path.join(base_dir, src["file"])
    if not os.path.exists(src_path):
        raise RuntimeError(f"anchor source not found: {src_path}")
    slug = _slug(os.path.splitext(os.path.basename(src["file"]))[0])
    is_pdf = src_path.lower().endswith(".pdf")
    pages = _pdf_pages(src_path) if is_pdf else _text_pages(src_path)
    units = []
    for n, content in enumerate(pages, 1):
        content = content.strip()
        if not content:                       # a truly empty page is nothing, not a 0-card decision
            continue
        units.append({"anchor_ref": f"{slug}/slide-{n}", "content": content,
                      "page": n, "src_pdf": src_path if is_pdf else None})
    if not units:
        raise RuntimeError(f"anchor '{src['file']}' yielded 0 units — is it page/slide-delimited?")
    return units


# ── lifecycle ─────────────────────────────────────────────────────────────────────────
def init_run(job_path, force=False):
    import yaml
    with open(job_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    base_dir = os.path.dirname(os.path.abspath(job_path))
    for s in cfg.get("sources", []):              # resolve source paths so agents can read them
        s["path"] = os.path.join(base_dir, s["file"])
    cards_dir = os.path.join(base_dir, cfg["run"]["cards_dir"])
    os.makedirs(cards_dir, exist_ok=True)
    if load_state(cards_dir) is not None and not force:
        raise RuntimeError(f"a run already exists at {state_path(cards_dir)} — pass force to reset")
    deck = cfg["run"]["deck"]
    units_raw = _enumerate_units(cfg, base_dir)

    anchor_dir = os.path.join(cards_dir, ANCHOR_DIR)
    os.makedirs(anchor_dir, exist_ok=True)
    state = {"version": 1, "execution_id": _slug(deck), "config": cfg,
             "base_dir": base_dir, "cards_dir": cards_dir, "cards_file": os.path.join(cards_dir, "cards.jsonl"),
             "stages": STAGES, "created": _now(), "updated": _now(), "units": {}, "cards": {}}
    for u in units_raw:
        uid = _mint_unit_id(deck, u["anchor_ref"])
        content_file = os.path.join(anchor_dir, uid + ".txt")
        with open(content_file, "w", encoding="utf-8") as f:
            f.write(u["content"])
        image_file = None
        if u.get("src_pdf"):                  # render the slide image — the real source for diagram slides
            image_file = _render_page(u["src_pdf"], u["page"], os.path.join(anchor_dir, uid))
        state["units"][uid] = {"unit_id": uid, "anchor_ref": u["anchor_ref"],
                               "content_file": content_file, "image_file": image_file,
                               "stage": "scaffold", "status": "ready",
                               "attempts": {}, "artifacts": {}, "card_ids": [], "history": []}
    obj_src = next((s for s in cfg["sources"] if s.get("role") == "objectives"), None)
    state["coverage"] = {"status": "pending" if obj_src else "n/a",
                         "objectives_path": obj_src.get("path") if obj_src else None, "map": None}
    save_state(cards_dir, state)
    return state


# ── the driver surface: next_step (PURE) / submit_step (mutating) ──────────────────────
def next_step(state):
    """PURE. Return the lowest-stage ready frontier item, or {done}/{blocked}. No mutation."""
    units, cards = state["units"], state["cards"]
    for stage in UNIT_STAGES:
        for uid, u in units.items():
            if u["stage"] == stage and u["status"] == "ready":
                return _packet(state, uid, "unit", stage, u)
    for stage in CARD_STAGES:
        for cid, c in cards.items():
            if c["stage"] == stage and c["status"] == "ready":
                return _packet(state, cid, "card", stage, c)
    escalated = [u["unit_id"] for u in units.values() if u["status"] == "escalated"]
    blocked = ([u["unit_id"] for u in units.values() if u["status"] == "blocked"]
               + [c["card_id"] for c in cards.values() if c["status"] == "blocked"])
    if escalated or blocked:
        return {"done": False, "halted": True, "escalated": escalated, "blocked": blocked,
                "message": "run halted — unresolved escalated/blocked items; see process_status"}
    if state.get("coverage", {}).get("status") == "pending":
        return _coverage_packet(state)
    return {"done": True}


def _read(path):
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        return ""


def _objectives_text(state):
    """The learning-objectives text (the CONTRACT), passed to spec so yield decisions see it.
    Empty when the job has no objectives source."""
    p = state.get("coverage", {}).get("objectives_path")
    return _read(p) if p else ""


def _packet(state, target_id, kind, stage, obj):
    return {"done": False, "execution_id": state["execution_id"], "target_id": target_id,
            "target_kind": kind, "stage": stage, "model": STAGE_MODEL.get(stage),
            "instructions": _instructions(state, stage),
            "payload": _payload(state, target_id, kind, stage, obj)}


def _coverage_packet(state):
    """Run-level COVERAGE step — fires once all units/cards are done. The objectives are the CONTRACT."""
    cov = state["coverage"]
    run_tag = re.sub(r"^cards[-_]?", "", os.path.basename(state["cards_dir"].rstrip("/"))) or "run"
    instr = (
        f"COVERAGE — the objectives are the CONTRACT. Read the learning OBJECTIVES at "
        f"{cov.get('objectives_path')} and ALL cards in {state['cards_file']}. Map every objective RELEVANT "
        f"to this deck to the card(s) that cover it; per objective, status is covered | deferred | uncovered "
        f"| out-of-scope. PRECEDENCE: an objective the professor DEFERRED ('not on the exam') is still COVERED "
        f"— if no card exists for it, DRAFT one and tag it flag::beyond-scope (NEVER drop an objective-backed "
        f"fact). For every UNCOVERED objective, draft the missing card(s) in the CANONICAL shape (see {MARKUP}), "
        f"each with a NEW id '{run_tag}-obj_<n>::c<k>' (the '{run_tag}-' prefix namespaces per-lecture objective numbers so multi-lecture decks don't collide), a `source`, and (if deferred) tags including flag::beyond-scope. "
        f"Return: mapping = list of {{objective, status, card_ids, note}}; gap_cards = list of new cards "
        f"{{id, type, text, extra, source, tags}} (empty if full coverage)."
    )
    return {"done": False, "execution_id": state["execution_id"], "target_id": "__coverage__",
            "target_kind": "run", "stage": "coverage", "instructions": instr,
            "payload": {"objectives_path": cov.get("objectives_path"), "cards_file": state["cards_file"],
                        "sources": state["config"]["sources"]}}


def _instructions(state, stage):
    cap = state["config"].get("yield", {}).get("max_cards_per_unit", MAX_CARDS_CAP)
    common = f"House method: read {SKILL} and {MARKUP} first. Ground every fact in the ASSIGNED source, not memory."
    return {
        "scaffold": f"SCAFFOLD. {common} READ THE SLIDE IMAGE at payload.content_image if present — it IS the slide (figures, captions, diagrams the text layer misses; for a diagram slide it is your PRIMARY source). Combine it with the extracted text and capture the unit's FULL content as clean, faithful HTML for the answer-side reveal (`extra`) — this reveal is the shared context EVERY card from this unit shows, so make it complete and accurate. NEVER invent beyond the slide/sources. Return {{extra_html}}. Do not write cards yet.",
        "emphasis": f"EMPHASIS. {common} LOCATE this unit's segment in the TRANSCRIPT: take the slide's title + key terms (from the reveal / slide image) and find where the teacher discusses them — lectures run in slide ORDER, so this segment follows the prior slide's. If NO clear segment matches, return stressed:false with empty keywords — do NOT invent emphasis. When found, judge whether/how the teacher STRESSED this unit and extract the keywords the teacher emphasized + a short VERBATIM quote. Return {{stressed:bool, keywords:[...], quote}}.",
        "spec_propose": f"SPEC — PROPOSE. Read {HIGHYIELD}. The learning OBJECTIVES in the payload are the CONTRACT (they may span several lectures — use ONLY those whose slide-number annotation or topic matches THIS unit, identified by its anchor_ref). STEP 1: list the objective(s) this unit is the SOURCE for. A fact this unit teaches that a matched objective NAMES is REQUIRED — it OVERRIDES restraint, so never propose 0 for an on-slide objective-backed fact. STEP 2: facts NOT tied to any objective get the normal HIGH-YIELD bar — RESTRAINT is the rule, 0 is first-class. Don't duplicate an objective another unit covers better. Propose n_cards (0..{cap}); per card give concept + type + the objective it serves (or 'none') + its HIGH-YIELD clause. Return {{n_cards, objectives_served:[...], concepts:[{{concept,type,objective,rationale}}], reason}}.",
        "spec_verify": f"SPEC — VERIFY. Read {HIGHYIELD}. INDEPENDENTLY, using this unit's content + the OBJECTIVES in the payload: (1) re-derive n_cards from the rubric; (2) list which objective(s) this unit is the SOURCE for and confirm the proposal COVERS each — an uncovered on-slide objective is grounds to DISAGREE even if the count looks right; (3) sanity-check each proposed concept is not a closed-identity / mutually-inferable / self-answering trap (that gets fixed here, at concept choice, not patched downstream). Return {{agree:bool, my_n_cards, missing_objectives:[...], concept_concerns:[...], reason}} — agree ONLY if the count is sound AND every on-slide objective is covered AND no concept is a leak risk.",
        "generate": f"GENERATE — THE FACT, one job. {common} Also read {HIGHYIELD}. Ground every card in the SLIDE IMAGE (payload.content_image, if present) + the unit reveal — for a diagram slide, card what the figure/caption actually shows; do NOT author from memory. Author the approved cards — one per card_id — as PLAIN cloze cards (NO <b>/<u>/<i> markup yet; a later stage applies role colors). MATCH THE REFERENCE DECK SHAPE (measured AnKing Neurogenetics): **TWO-SIDED, ~2 clozes, ~10-12 words revealed** (norm: 2 clozes = 64%, median ~11 words, terse). TWO-SIDED = blank BOTH the subject term (c1) AND its value/definition (c2), e.g. `{{c1::Osmosis}} is the {{c2::diffusion of water across a selectively permeable membrane}}` — this yields a card for EACH direction and is the house default; it is NOT self-answering (a subject↔its-own-definition pair is the DESIGN, not a leak). Lead with the SUBJECT; keep connectors ('is', 'secretes') plain; be terse — no long trailing prose clause. A card carries ONE answer VALUE (the c2 definition/value) — that is different from ONE cloze; the subject cloze and the value cloze are two roles. SELF-ANSWERING (the real defect to avoid) is narrow: (a) two INDEPENDENT facts split across clozes that reveal each other; (b) multiple synonym/co-implied values for one concept (eosin⟺acidic⟺acidophilic⟺pink); (c) a CLOSED IDENTITY A+B->C where two terms force the third (ADP+Pi->ATP — test the CONCEPT, don't cloze the equation); (d) a visible NON-CLOZE clause that gives away a blank. It is NOT the subject↔definition pairing. Give each card the given `id`, `extra` = unit reveal HTML, a `source`, and tags. Do NOT write files — RETURN {{cards:[{{id,type,text,extra,source,tags}}, ...]}}; the engine writes them.",
        "accuracy": f"ACCURACY + STRUCTURE. Read {SKILL} 'Review cards for accuracy'. TWO checks: (1) FACTS — verify against the SLIDE IMAGE (payload.content_image, if present) + the card's `extra` reveal and the ASSIGNED source (lecture/slide wins over textbook). (2) STRUCTURE vs the REFERENCE DECK: subject-first; **TWO-SIDED where the subject has a real value to trade against it** (subject clozed AND its value clozed — the house norm, 76% of 2-cloze reference cards — NOT a leak); ~2 clozes; TERSE (~10-12 words revealed; a long prose tail is a smell). A single-sided definitional card whose definition stays exposed should be made two-sided unless the clozed term is a bare label with nothing further to recall. Reject as SELF-ANSWERING only: two INDEPENDENT facts split across clozes, synonym/co-implied VALUES, a CLOSED IDENTITY, or a visible non-cloze clause giving away a blank — NOT a subject↔its-own-definition pair. This is the stage to fix structure, BEFORE markup. If contradicted or mis-structured, correct it and return the FULL corrected card as `fixed` (same id, still no markup). If untaught-but-true, KEEP + tag flag::beyond-scope (return the tagged card as `fixed`) — verdict 'clean'. Reserve 'flagged' ONLY for a real defect you could NOT fix. Do NOT edit files. Return {{verdict:'clean'|'flagged', resolution, note, fixed?}}.",
        "markup": f"MARKUP — apply role colors, one job. Read {MARKUP}. The card's FACT and STRUCTURE are already fixed; do NOT change the wording, the clozes, or which terms are blanked. Wrap the SUBJECT term <b> (mauve), the ANSWER/value <i> (red), and a scoping FACET <u> (teal, ONLY if a phrase genuinely narrows the question — ~44% of cards, most have none). Put the markup INSIDE the cloze braces: `{{c1::<b>subject</b>}}`. EXACTLY ONE <i> answer VALUE per card — but a TWO-SIDED card still has ONE <i>: its subject cloze is wrapped <b> (not <i>), so two-sidedness is NOT a second answer-blank and must be preserved, not collapsed. Do not restructure. Return the FULL card as `fixed` (same id) with markup applied. Do NOT edit files; the engine writes it. Return {{fixed}}.",
        "style": f"STYLE — final review. Read {SKILL} + {MARKUP}. Confirm against the REFERENCE DECK: roles correct (ONE <b> subject, ONE <i> answer VALUE, <u> only for a real facet); TWO-SIDED preserved where the subject has a real value (do NOT collapse a two-sided card to single-sided — that is the house shape, not a leak); TERSE (~10-12 words revealed; >25 words of non-list prose is a smell); leads with the subject. Flag a ONE-SIDED DEFINITIONAL card (definition exposed, subject not clozed) unless the term is a bare label. SELF-ANSWERING check is NARROW — flag only: two INDEPENDENT facts across clozes, synonym/co-implied VALUES, a CLOSED IDENTITY, or a visible non-cloze clause giving away a blank; a subject↔its-own-definition pair is CORRECT. The shape linter runs automatically on your verdict — a card with any lint ERROR is flagged regardless of what you return, so fix it here if you can. If you change the card, return the FULL corrected card as `fixed` (same id). Do NOT edit files. Return {{verdict:'clean'|'flagged', resolution, note, fixed?}}.",
    }[stage]


def _payload(state, target_id, kind, stage, obj):
    cfg = state["config"]
    if kind == "unit":
        p = {"anchor_ref": obj["anchor_ref"], "content_file": obj["content_file"],
             "content_image": obj.get("image_file"), "cards_file": state["cards_file"]}
        if stage in ("emphasis",):
            p["sources"] = cfg["sources"]
            p["scaffold"] = obj["artifacts"].get("scaffold", {})
        if stage == "spec_propose":
            p["scaffold"] = obj["artifacts"].get("scaffold", {})
            p["emphasis"] = obj["artifacts"].get("emphasis", {})
            p["cap"] = cfg.get("yield", {}).get("max_cards_per_unit", MAX_CARDS_CAP)
            p["objectives"] = _objectives_text(state)
        if stage == "spec_verify":
            p["proposal"] = obj["artifacts"].get("spec_propose", {})
            p["objectives"] = _objectives_text(state)
        if stage == "generate":
            p["spec"] = obj["artifacts"].get("spec_propose", {})
            p["card_ids"] = obj["card_ids"]
            p["extra_html"] = obj["artifacts"].get("scaffold", {}).get("extra_html", _read(obj["content_file"]))
            p["sources"] = cfg["sources"]
        return p
    # card
    cards_map = review_ledger.load_cards(state["cards_dir"])
    card_tuple = cards_map.get(target_id)
    unit = state["units"].get(obj["unit_id"], {})
    return {"card_id": target_id, "unit_id": obj["unit_id"],
            "card": card_tuple[0] if card_tuple else None,
            "content_image": unit.get("image_file"), "sources": cfg["sources"]}


def submit_step(state, target_id, stage, result):
    """Validate stage==current, run the stage handler, advance. Raises on out-of-order/unknown."""
    if target_id == "__coverage__":
        if stage != "coverage":
            raise ValueError(f"__coverage__ expects stage 'coverage', not '{stage}'")
        if state.get("coverage", {}).get("status") != "pending":
            raise ValueError("coverage is not pending")
        _h_coverage(state, result or {})
        return {"target_id": "__coverage__", "kind": "run", "new_stage": "done", "status": "done"}
    units, cards = state["units"], state["cards"]
    if target_id in units:
        obj, kind = units[target_id], "unit"
    elif target_id in cards:
        obj, kind = cards[target_id], "card"
    else:
        raise ValueError(f"unknown target '{target_id}'")
    if obj["stage"] != stage:
        raise ValueError(f"{target_id} is at stage '{obj['stage']}', not '{stage}' — out-of-order submit rejected")
    att = obj.setdefault("attempts", {})
    att[stage] = att.get(stage, 0) + 1
    _HANDLERS[stage](state, target_id, obj, result or {})
    obj.setdefault("history", []).append({"stage": stage, "at": _now(),
                                          "by": result.get("reviewer") or result.get("by")})
    return {"target_id": target_id, "kind": kind, "new_stage": obj["stage"], "status": obj["status"]}


def next_batch(state):
    """PURE. ALL ready items at the LOWEST frontier stage, so ONE agent can do the whole step
    (one agent per STEP, not per card). Cross-item awareness (e.g. dedup at spec) is why this beats
    stepping one at a time. Returns {stage, instructions, items:[{target_id, stage, payload}]} | {done} | {halted}."""
    units, cards = state["units"], state["cards"]
    for stage in UNIT_STAGES:
        ids = [uid for uid, u in units.items() if u["stage"] == stage and u["status"] == "ready"]
        if ids:
            return {"done": False, "stage": stage, "target_kind": "unit", "count": len(ids),
                    "model": STAGE_MODEL.get(stage),
                    "execution_id": state["execution_id"], "instructions": _instructions(state, stage),
                    "items": [{"target_id": uid, "stage": stage,
                               "payload": _payload(state, uid, "unit", stage, units[uid])} for uid in ids]}
    for stage in CARD_STAGES:
        ids = [cid for cid, c in cards.items() if c["stage"] == stage and c["status"] == "ready"]
        if ids:
            return {"done": False, "stage": stage, "target_kind": "card", "count": len(ids),
                    "model": STAGE_MODEL.get(stage),
                    "execution_id": state["execution_id"], "instructions": _instructions(state, stage),
                    "items": [{"target_id": cid, "stage": stage,
                               "payload": _payload(state, cid, "card", stage, cards[cid])} for cid in ids]}
    escalated = [u["unit_id"] for u in units.values() if u["status"] == "escalated"]
    blocked = ([u["unit_id"] for u in units.values() if u["status"] == "blocked"]
               + [c["card_id"] for c in cards.values() if c["status"] == "blocked"])
    if escalated or blocked:
        return {"done": False, "halted": True, "escalated": escalated, "blocked": blocked}
    if state.get("coverage", {}).get("status") == "pending":
        p = _coverage_packet(state)
        return {"done": False, "stage": "coverage", "target_kind": "run", "count": 1,
                "model": STAGE_MODEL.get("coverage"),
                "execution_id": state["execution_id"], "instructions": p["instructions"],
                "items": [{"target_id": "__coverage__", "stage": "coverage", "payload": p["payload"]}]}
    return {"done": True}


def submit_batch(state, results):
    """Apply [{target_id, stage, result}, ...] via submit_step (each stage-validated). Returns per-item
    outcomes (an error entry per item that failed; the rest still apply). Caller saves once, atomically."""
    out = []
    for r in results:
        try:
            out.append(submit_step(state, r["target_id"], r["stage"], r.get("result", {})))
        except Exception as e:
            out.append({"target_id": r.get("target_id"), "error": str(e)})
    return out


# ── stage handlers ────────────────────────────────────────────────────────────────────
def _h_scaffold(state, uid, u, r):
    u["artifacts"]["scaffold"] = {"extra_html": r.get("extra_html", ""), "at": _now()}
    u["stage"], u["status"] = "emphasis", "ready"


def _h_emphasis(state, uid, u, r):
    u["artifacts"]["emphasis"] = {k: r.get(k) for k in ("stressed", "keywords", "quote")}
    u["stage"], u["status"] = "spec_propose", "ready"


def _h_spec_propose(state, uid, u, r):
    cap = state["config"].get("yield", {}).get("max_cards_per_unit", MAX_CARDS_CAP)
    n = int(r.get("n_cards", 0))
    if n < 0 or n > cap:
        raise ValueError(f"spec proposed n_cards={n} outside 0..{cap}")
    u["artifacts"]["spec_propose"] = {"n_cards": n, "concepts": r.get("concepts", []), "reason": r.get("reason")}
    u["stage"], u["status"] = "spec_verify", "ready"


def _h_spec_verify(state, uid, u, r):
    prop = u["artifacts"].get("spec_propose", {})
    u["artifacts"]["spec_verify"] = {"agree": bool(r.get("agree")), "my_n_cards": r.get("my_n_cards"),
                                     "reason": r.get("reason")}
    if not r.get("agree"):
        u["status"] = "escalated"           # stays at spec_verify — human/tiebreak resolves
        return
    n = int(prop.get("n_cards", 0))
    if n == 0:
        u["card_ids"], u["stage"], u["status"] = [], "done", "done"
        return
    u["card_ids"] = _mint_card_ids(uid, n)
    u["stage"], u["status"] = "generate", "ready"


def _append_cards(cards_file, cards):
    if not cards:
        return
    with open(cards_file, "a", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def _replace_card(cards_file, card_id, new_card):
    """Replace the line whose card 'id' matches. Callers run under the MCP submit-lock, so
    parallel workers never corrupt the file — the engine owns every write to cards.jsonl."""
    if not os.path.exists(cards_file):
        return
    rows = []
    for line in open(cards_file, encoding="utf-8"):
        if not line.strip():
            continue
        c = json.loads(line)
        rows.append(new_card if c.get("id") == card_id else c)
    tmp = cards_file + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for c in rows:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    os.replace(tmp, cards_file)


def _h_generate(state, uid, u, r):
    _append_cards(state["cards_file"], r.get("cards", []) or [])   # engine owns the write (serialized)
    for cid in u["card_ids"]:
        state["cards"][cid] = {"card_id": cid, "unit_id": uid, "stage": "accuracy", "status": "ready",
                               "verdicts": {"accuracy": None, "style": None}}
    u["stage"], u["status"] = "done", "done"


def _current_card(state, cid, r):
    """The card as it stands after any fix this step applied — the object the verdict is about."""
    if r.get("fixed"):
        return r["fixed"]
    ct = review_ledger.load_cards(state["cards_dir"]).get(cid)
    return ct[0] if ct else None


def _card_verdict(state, cid, c, r, axis, next_stage):
    if r.get("fixed"):                              # engine applies any fix; agents never touch the file
        _replace_card(state["cards_file"], cid, r["fixed"])
    verdict = r.get("verdict", "flagged")
    note = r.get("note")
    # MECHANICAL BACKSTOP: the agent's verdict cannot override the linter. A card with any lint
    # ERROR is flagged no matter what the reviewer claimed — enforcement, not persuasion. (Warnings
    # stay advisory; the reviewer adjudicates those.)
    card = _current_card(state, cid, r)
    lint_errs = lint_cards.lint_card(card, cid)[0] if card else []
    if lint_errs:
        verdict = "flagged"
        note = ((note + " | ") if note else "") + "LINT: " + "; ".join(lint_errs)
    review_ledger.record(state["cards_dir"], cid, verdict,
                         resolution=r.get("resolution"), note=note,
                         reviewer=r.get("reviewer") or f"engine-{axis}")
    c["verdicts"][axis] = verdict
    if verdict == "clean":
        c["stage"], c["status"] = next_stage, ("done" if next_stage == "done" else "ready")
    else:
        c["status"] = "blocked"             # flagged — surfaced; must be resolved before ship


def _h_accuracy(state, cid, c, r):
    _card_verdict(state, cid, c, r, "accuracy", "markup")


def _h_markup(state, cid, c, r):
    """Producer stage — a dedicated agent applies <b>/<u>/<i> role colors and returns the full card
    as `fixed`. No verdict; the engine writes the file and routes the card to the style reviewer."""
    if r.get("fixed"):
        _replace_card(state["cards_file"], cid, r["fixed"])
    c["stage"], c["status"] = "style", "ready"


def _h_style(state, cid, c, r):
    _card_verdict(state, cid, c, r, "style", "done")


def _h_coverage(state, r):
    """Record the objective→card map; draft-in any gap cards and route them through accuracy→style."""
    cov = state["coverage"]
    mapping = r.get("mapping", []) or []
    gap = r.get("gap_cards", []) or []
    drafted_nums = {m.group(1) for c in gap if (m := re.search(r"obj_(\d+)", str(c.get("id", ""))))}
    for entry in mapping:              # an 'uncovered' objective that got a drafted card is now COVERED
        m = re.match(r"\s*(\d+)", str(entry.get("objective", "")))
        if entry.get("status") == "uncovered" and m and m.group(1) in drafted_nums:
            entry["status"] = "covered"
            entry["note"] = (entry.get("note") or "") + " [covered by drafted card]"
    cov["map"] = mapping
    if gap:
        with open(state["cards_file"], "a", encoding="utf-8") as f:
            for c in gap:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        for c in gap:
            cid = c.get("id")
            if cid:
                state["cards"][cid] = {"card_id": cid, "unit_id": "__objective__", "stage": "accuracy",
                                       "status": "ready", "verdicts": {"accuracy": None, "style": None}}
    cov["status"] = "done"


_HANDLERS = {"scaffold": _h_scaffold, "emphasis": _h_emphasis, "spec_propose": _h_spec_propose,
             "spec_verify": _h_spec_verify, "generate": _h_generate, "accuracy": _h_accuracy,
             "markup": _h_markup, "style": _h_style}


# ── reporting + advisory run-completeness gate ────────────────────────────────────────
def status(state):
    units, cards = state["units"], state["cards"]
    by_stage = {}
    for u in units.values():
        by_stage.setdefault("unit:" + u["stage"], 0)
        by_stage["unit:" + u["stage"]] += 1
    for c in cards.values():
        by_stage.setdefault("card:" + c["stage"], 0)
        by_stage["card:" + c["stage"]] += 1
    escalated = [{"unit_id": u["unit_id"], "anchor_ref": u["anchor_ref"],
                  "proposed": u["artifacts"].get("spec_propose", {}).get("n_cards"),
                  "verify": u["artifacts"].get("spec_verify", {})}
                 for u in units.values() if u["status"] == "escalated"]
    blocked = [t for t in
               [u["unit_id"] for u in units.values() if u["status"] == "blocked"]
               + [c["card_id"] for c in cards.values() if c["status"] == "blocked"]]
    zero = [u["anchor_ref"] for u in units.values() if u["status"] == "done" and not u["card_ids"]]
    units_done = all(u["status"] == "done" for u in units.values())
    cards_done = all(c["stage"] == "done" for c in cards.values())
    cov = state.get("coverage", {})
    cov_map = cov.get("map") or []
    uncovered = [m.get("objective") for m in cov_map if m.get("status") == "uncovered"]
    cov_ok = cov.get("status", "n/a") in ("done", "n/a") and not uncovered
    coverage = {"status": cov.get("status", "n/a"), "objectives_mapped": len(cov_map),
                "covered": sum(1 for m in cov_map if m.get("status") == "covered"),
                "deferred": sum(1 for m in cov_map if m.get("status") == "deferred"),
                "uncovered": uncovered}
    return {"ok": units_done and cards_done and cov_ok and not escalated and not blocked,
            "execution_id": state.get("execution_id"),
            "units_total": len(units), "cards_total": len(cards),
            "by_stage": by_stage, "escalated": escalated, "blocked": blocked, "zero_card_units": zero,
            "coverage": coverage}


def gate(cards_dir):
    state = load_state(cards_dir)
    if state is None:
        sys.exit(f"no process run at {cards_dir}")
    rep = status(state)
    if not rep["ok"]:
        print(f"PROCESS not complete — {len(rep['escalated'])} escalated, {len(rep['blocked'])} blocked; "
              f"stages: {rep['by_stage']}", file=sys.stderr)
        sys.exit(1)
    print(f"process complete — {rep['units_total']} units, {rep['cards_total']} cards, "
          f"{len(rep['zero_card_units'])} zero-card units")


# ── CLI (dual with the importable API; the MCP shim wraps the same functions) ──────────
def main():
    ap = argparse.ArgumentParser(description="Process engine — staged card-generation state machine")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("job"); p.add_argument("--force", action="store_true")
    for c in ("next", "next-batch", "status", "gate"):
        sub.add_parser(c).add_argument("cards_dir")
    p = sub.add_parser("submit")
    p.add_argument("cards_dir"); p.add_argument("target"); p.add_argument("stage"); p.add_argument("result_json")
    p = sub.add_parser("submit-batch"); p.add_argument("cards_dir"); p.add_argument("results_json")
    a = ap.parse_args()

    if a.cmd == "init":
        st = init_run(a.job, a.force)
        print(json.dumps({"execution_id": st["execution_id"], "units": len(st["units"]),
                          "cards_dir": st["cards_dir"]}, indent=2))
        return
    if a.cmd == "gate":
        gate(a.cards_dir); return
    state = load_state(a.cards_dir)
    if state is None:
        sys.exit(f"no process run at {a.cards_dir}")
    if a.cmd == "next":
        print(json.dumps(next_step(state), ensure_ascii=False, indent=2))
    elif a.cmd == "next-batch":
        print(json.dumps(next_batch(state), ensure_ascii=False, indent=2))
    elif a.cmd == "status":
        print(json.dumps(status(state), ensure_ascii=False, indent=2))
    elif a.cmd == "submit":
        res = submit_step(state, a.target, a.stage, json.loads(a.result_json))
        save_state(a.cards_dir, state)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif a.cmd == "submit-batch":
        res = submit_batch(state, json.loads(a.results_json))
        save_state(a.cards_dir, state)
        print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
