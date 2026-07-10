#!/usr/bin/env python3
"""process_engine_mcp — MCP server exposing the staged card-generation process engine.

A thin shim over process_engine.py (the brains). It hands an agent-driver ONE step at a time
and enforces the state machine: `process_next_step` is read-only and returns the monotonic
frontier; `process_submit_step` refuses any out-of-order submit. This is the semi-deterministic
flow engine — the process is a first-class, tracked state machine, not a bypassable convention.

Tools:
  - process_init         : parse a job.yaml, enumerate anchor units, start a run
  - process_next_step    : (read-only) the next step packet to hand an agent, or {done}
  - process_submit_step  : record an agent's result for a target+stage and advance
  - process_status       : where every unit/card is; escalated / blocked / zero-card units
  - process_gate         : (read-only) run-completeness report (the real ship gate stays lint+ledger)

Run (stdio):  python process_engine_mcp.py
"""
import asyncio
import io
import json
import os
import sys

import anyio
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

# process_engine.py lives beside this file — import the brains
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import process_engine as PE  # noqa: E402

mcp = FastMCP("process_engine_mcp")

# ── concurrency model (why this server survives parallel load) ─────────────────────────
# The engine's work is BLOCKING and heavy: process_init shells out to pdftotext/pdftoppm
# (seconds-to-minutes for a big deck) and every submit rewrites cards.jsonl + the state file.
# Running that on the asyncio event loop would starve the stdio transport — the client's
# heartbeat times out and severs the session pipe even though this process is still alive
# (the exact failure seen under a multi-deck batch). So EVERY tool offloads its blocking body
# to a worker thread via asyncio.to_thread, keeping the loop free to service stdio throughout.
#
# Mutations still have to be serialized per run so parallel chunk-workers can't lose updates
# or corrupt cards.jsonl. But a single global lock would make separate decks block each other
# (head-of-line stalls that made the parallel batch worse). Each run owns its own files, so we
# key the lock by cards_dir: same deck → serialized, different decks → fully concurrent.
_DIR_LOCKS: dict[str, asyncio.Lock] = {}
_DIR_LOCKS_GUARD = asyncio.Lock()


async def _dir_lock(cards_dir: str) -> asyncio.Lock:
    """Return the per-run mutation lock for cards_dir (created on first use). Keyed by realpath
    so different spellings of the same dir share one lock."""
    key = os.path.realpath(cards_dir)
    async with _DIR_LOCKS_GUARD:
        lock = _DIR_LOCKS.get(key)
        if lock is None:
            lock = _DIR_LOCKS[key] = asyncio.Lock()
    return lock


class InitInput(BaseModel):
    """Input for process_init."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    job_path: str = Field(..., description="Absolute path to the run's job.yaml", min_length=1)
    force: bool = Field(default=False, description="Reset an existing run at the same cards_dir")


class CardsDirInput(BaseModel):
    """Input for the read-only tools + gate."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    cards_dir: str = Field(..., description="Absolute path to the run's cards_dir (holds .process_state.json)", min_length=1)


class SubmitInput(BaseModel):
    """Input for process_submit_step."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    cards_dir: str = Field(..., description="Absolute path to the run's cards_dir", min_length=1)
    target_id: str = Field(..., description="The unit_id or card_id from the step packet", min_length=1)
    stage: str = Field(..., description="The stage from the step packet — MUST match the target's current stage", min_length=1)
    result: dict = Field(default_factory=dict, description="The agent's structured result for this stage (stage-specific fields)")


def _load(cards_dir: str):
    state = PE.load_state(cards_dir)
    if state is None:
        raise RuntimeError(f"no process run at {cards_dir} — call process_init first")
    return state


# ── blocking bodies (each runs in a worker thread, never on the event loop) ────────────
# Read-only bodies take no lock: load_state reads the whole file in one shot and save_state
# swaps it in with os.replace (atomic), so a reader always sees a whole old-or-new state.
def _b_init(job_path: str, force: bool) -> dict:
    st = PE.init_run(job_path, force)
    return {"execution_id": st["execution_id"], "units": len(st["units"]), "cards_dir": st["cards_dir"]}


def _b_next_step(cards_dir: str) -> dict:
    return PE.next_step(_load(cards_dir))


def _b_next_batch(cards_dir: str) -> dict:
    return PE.next_batch(_load(cards_dir))


def _b_status(cards_dir: str) -> dict:
    return PE.status(_load(cards_dir))


def _b_gate(cards_dir: str) -> dict:
    rep = PE.status(_load(cards_dir))
    return {k: rep[k] for k in ("ok", "units_total", "cards_total", "escalated", "blocked")}


# Mutating bodies do load→mutate→save as one unit; the caller holds the per-dir lock.
def _b_submit(cards_dir: str, target_id: str, stage: str, result: dict) -> dict:
    state = _load(cards_dir)
    res = PE.submit_step(state, target_id, stage, result)
    PE.save_state(cards_dir, state)
    return res


def _b_submit_batch(cards_dir: str, results: list) -> list:
    state = _load(cards_dir)
    res = PE.submit_batch(state, results)
    PE.save_state(cards_dir, state)
    return res


@mcp.tool(
    name="process_init",
    annotations={"title": "Start a card-generation run", "readOnlyHint": False,
                 "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def process_init(params: InitInput) -> str:
    """Start a run: parse the job.yaml, enumerate the anchor units, and create the process state.

    Reads the job's documents + selectable anchor (unit: slide | summary_section | ...) and
    yield caps, enumerates one unit per anchor element, and writes .process_state.json in the
    run's cards_dir with every unit at stage 'scaffold'. Idempotent only with force=True (which
    resets an existing run).

    Args:
        params (InitInput): job_path (abs path to job.yaml); force (reset existing run).

    Returns:
        str: JSON {execution_id, units, cards_dir}. On failure: "Error: <message>".
    """
    try:
        out = await asyncio.to_thread(_b_init, params.job_path, params.force)
        return json.dumps(out, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="process_next_step",
    annotations={"title": "Get the next step to work", "readOnlyHint": True,
                 "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def process_next_step(params: CardsDirInput) -> str:
    """Return the next step packet to hand an agent — or {done}. READ-ONLY: state only advances
    on process_submit_step, so re-calling this (e.g. after a crash) re-hands the same work.

    The packet is {execution_id, target_id, target_kind: unit|card, stage, instructions, payload}.
    `instructions` is the stage's marching orders (pointing at SKILL.md / MARKUP.md / HIGH-YIELD.md);
    `payload` carries the source refs the agent needs. If nothing is ready but items are stuck,
    returns {done:false, halted:true, escalated:[...], blocked:[...]}.

    Args:
        params (CardsDirInput): cards_dir.

    Returns:
        str: the JSON step packet, {done:true}, or a halted report. On failure: "Error: <message>".
    """
    try:
        return json.dumps(await asyncio.to_thread(_b_next_step, params.cards_dir), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="process_submit_step",
    annotations={"title": "Submit a step result and advance", "readOnlyHint": False,
                 "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def process_submit_step(params: SubmitInput) -> str:
    """Record an agent's result for target_id at `stage` and advance the state machine.

    REFUSES any submit whose stage != the target's current stage (no skipping/reordering). By
    stage: spec_verify agree → mints card_ids (or marks the unit done at n_cards==0), disagree →
    escalates; generate → registers the unit's cards into the per-card accuracy→style pipeline;
    accuracy/style → also write a verdict to the review ledger (a flagged verdict blocks the card).
    Persists atomically.

    Args:
        params (SubmitInput): cards_dir; target_id; stage; result (stage-specific dict).

    Returns:
        str: JSON {target_id, kind, new_stage, status}. On out-of-order/unknown/invalid input: "Error: <message>".
    """
    try:
        async with await _dir_lock(params.cards_dir):
            res = await asyncio.to_thread(_b_submit, params.cards_dir, params.target_id,
                                          params.stage, params.result)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="process_status",
    annotations={"title": "Report where every unit/card is", "readOnlyHint": True,
                 "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def process_status(params: CardsDirInput) -> str:
    """Full run status: counts by stage, plus the escalated (consensus-disagreement), blocked
    (flagged), and zero-card units — the items needing a human decision. Use to see progress or
    to resolve what halted a run.

    Args:
        params (CardsDirInput): cards_dir.

    Returns:
        str: JSON {ok, units_total, cards_total, by_stage, escalated[], blocked[], zero_card_units[]}.
        On failure: "Error: <message>".
    """
    try:
        return json.dumps(await asyncio.to_thread(_b_status, params.cards_dir), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="process_gate",
    annotations={"title": "Run-completeness gate (advisory)", "readOnlyHint": True,
                 "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def process_gate(params: CardsDirInput) -> str:
    """Report whether the run is complete (every unit done, nothing escalated/blocked). This is
    ADVISORY — the real ship gate stays lint_cards.gate + review_ledger.gate at build/sync.

    Args:
        params (CardsDirInput): cards_dir.

    Returns:
        str: JSON {ok, units_total, cards_total, escalated[], blocked[]}. On failure: "Error: <message>".
    """
    try:
        return json.dumps(await asyncio.to_thread(_b_gate, params.cards_dir), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


class BatchSubmitInput(BaseModel):
    """Input for process_submit_batch."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    cards_dir: str = Field(..., description="Absolute path to the run's cards_dir", min_length=1)
    results: list = Field(..., description="One entry per item in the batch: {target_id, stage, result}")


@mcp.tool(
    name="process_next_batch",
    annotations={"title": "Get the whole next step (all items at one stage)", "readOnlyHint": True,
                 "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def process_next_batch(params: CardsDirInput) -> str:
    """Return EVERY ready item at the current frontier stage, so ONE agent can do the whole step at
    once (one agent per STEP, not per card). READ-ONLY. Seeing all items together is what lets a stage
    like spec detect cross-unit duplicates.

    Returns {stage, instructions, items:[{target_id, stage, payload}]} (do each item's work per the
    shared instructions, then process_submit_batch), or {done:true}, or a halted report.

    Args:
        params (CardsDirInput): cards_dir.

    Returns:
        str: JSON batch packet / {done:true} / halted. On failure: "Error: <message>".
    """
    try:
        return json.dumps(await asyncio.to_thread(_b_next_batch, params.cards_dir), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(
    name="process_submit_batch",
    annotations={"title": "Submit a whole step's results", "readOnlyHint": False,
                 "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
)
async def process_submit_batch(params: BatchSubmitInput) -> str:
    """Submit results for a whole stage at once: results = [{target_id, stage, result}, ...]. Each is
    stage-validated (out-of-order items are rejected individually, returned with an "error"; the rest
    still apply). Persists once, atomically. Pair with process_next_batch.

    Args:
        params (BatchSubmitInput): cards_dir; results (list of {target_id, stage, result}).

    Returns:
        str: JSON list of per-item outcomes. On failure: "Error: <message>".
    """
    try:
        async with await _dir_lock(params.cards_dir):
            res = await asyncio.to_thread(_b_submit_batch, params.cards_dir, params.results)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


async def _serve_stdio() -> None:
    """Serve over stdio, but hand the SDK a PRIVATE handle to the real stdout for JSON-RPC
    framing and repoint sys.stdout at stderr. The framing lives on fd 1; anything that prints
    to stdout — a stray print in engine code, a chatty dependency — would interleave into that
    stream and sever the session. Isolating them makes the protocol robust regardless of what
    the worker threads emit. (Mirrors FastMCP.run_stdio_async with an explicit stdout stream.)"""
    protocol = anyio.wrap_file(io.TextIOWrapper(os.fdopen(os.dup(sys.stdout.fileno()), "wb"),
                                                encoding="utf-8"))
    sys.stdout = sys.stderr
    server = mcp._mcp_server
    async with stdio_server(stdout=protocol) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(_serve_stdio)
