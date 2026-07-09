#!/usr/bin/env python3
"""anki_style_mcp — MCP server exposing the house Anki card-style guide + linter.

A thin shim over lint_cards.py (the brains) and SKILL.md (the canonical guide), so any
agent — generation or review — can programmatically CONFIRM cards meet the style contract
instead of relying on being able to read a markdown file (which sandboxed subagents cannot
always do).

Tools:
  - anki_style_guide : return the canonical card-style contract (from SKILL.md)
  - anki_style_lint  : lint a cards dir/file → {errors[], warnings[]} per the contract

Run (stdio):  python anki_style_mcp.py
"""
import json
import os
import sys

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

# lint_cards.py lives beside this file — import its structured linter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lint_cards  # noqa: E402

mcp = FastMCP("anki_style_mcp")

# SKILL.md is the single source of truth for the style contract.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", ".claude", "skills", "anki-cards"))
SKILL_PATH = os.path.join(_SKILL_DIR, "SKILL.md")
MARKUP_PATH = os.path.join(_SKILL_DIR, "MARKUP.md")   # standalone visual-cue (color roles) spec


class StyleGuideInput(BaseModel):
    """Input for anki_style_guide."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    section: str = Field(
        default="contract",
        description="Which part to return: 'contract' = the Card-style contract section (default); 'markup' = the standalone MARKUP.md visual-cue/color-role spec; 'full' = the entire SKILL.md",
    )


class LintInput(BaseModel):
    """Input for anki_style_lint."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    path: str = Field(
        ...,
        description="Absolute path to a cards directory (lints every *.jsonl in it) or a single .jsonl file",
        min_length=1,
    )
    warnings: bool = Field(
        default=True,
        description="Include heuristic warnings (subject-first, two-concept, 3-cloze, multiple-italics) in addition to hard errors",
    )


def _extract_contract(md: str) -> str:
    """Return the '## Card-style contract' section of SKILL.md (up to the next top-level ---)."""
    lines = md.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("## Card-style contract")), None)
    if start is None:
        return md
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "---"), len(lines))
    return "\n".join(lines[start:end]).strip()


@mcp.tool(
    name="anki_style_guide",
    annotations={"title": "Get Anki card-style guide", "readOnlyHint": True,
                 "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def anki_style_guide(params: StyleGuideInput) -> str:
    """Return the canonical house card-style contract for Anki card authoring.

    Use this to confirm the exact current style rules (cloze-first, subject-first, one concept
    per card, the canonical shape (bold subject + italic answer + plain scaffold, ~2 clozes;
    3 rare, 4+ never), one italic answer per card, complete-answer spans, markup roles
    <b>/<u>/<i>, pointed ::hints, numbered lists, no terminal period) before writing or
    reviewing cards. Sourced live from SKILL.md so it is always current.

    Args:
        params (StyleGuideInput):
            - section (str): 'contract' (default) for the Card-style contract section, or 'full' for all of SKILL.md.

    Returns:
        str: the requested markdown. On failure: "Error: <message>".
    """
    if params.section == "markup":
        try:
            with open(MARKUP_PATH, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error: could not read markup spec at {MARKUP_PATH}: {e}"
    try:
        with open(SKILL_PATH, encoding="utf-8") as f:
            md = f.read()
    except Exception as e:
        return f"Error: could not read style guide at {SKILL_PATH}: {e}"
    return md if params.section == "full" else _extract_contract(md)


@mcp.tool(
    name="anki_style_lint",
    annotations={"title": "Lint Anki cards against the style contract", "readOnlyHint": True,
                 "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
)
async def anki_style_lint(params: LintInput) -> str:
    """Lint Anki card JSONL against the house style contract and return structured findings.

    Split into hard `errors` (mechanical rule violations that MUST be fixed) and heuristic
    `warnings` (judgment suspects a human/model adjudicates). Call after writing or restyling
    cards; fix every error and reconcile warnings, then re-lint until error_count == 0.

    Errors (mechanical, enforced): malformed JSON; missing type/fields/tags/source; tag with a
    space; unbalanced {{ }}; no cloze / not starting at c1; >4 distinct clozes (cloze cap);
    terminal period; unbalanced <b>/<i>/<u> markup.
    Warnings (heuristic, flagged): exactly 4 clozes (verify single-axis contrast, not two
    concepts); non-contiguous numbering; standalone cloze missing a ::hint; subject-first
    violation (circumstantial opener); two-concept smell ("whereas…"); over-long note.

    Args:
        params (LintInput):
            - path (str): absolute path to a cards dir (all *.jsonl) or one .jsonl file.
            - warnings (bool): include heuristic warnings (default True).

    Returns:
        str: JSON with schema:
        {
          "ok": bool,               # true iff error_count == 0
          "error_count": int,
          "warning_count": int,     # 0 if warnings=false
          "files": [ { "file": str, "errors": [str], "warnings": [str] } ]
        }
        On bad path: {"ok": false, "error": "not found: <path>", ...}
    """
    rep = lint_cards.lint_paths(params.path)
    if not params.warnings:
        for f in rep.get("files", []):
            f["warnings"] = []
        rep["warnings"] = []
        rep["warning_count"] = 0
    return json.dumps(rep, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
