#!/usr/bin/env python3
"""The style checker as an MCP tool, so the REVIEWER can call it per card.

Why a tool and not more prompt text: the guidelines are already in the reviewer's system prompt —
all of okf plus 84 corpus cards — and it still approved 13 of 42 cards with style defects. Holding
a rule in context and correctly evaluating a string against it is the step that fails. This tool
removes that step: it does not tell the reviewer that bold comes before underline, it tells the
reviewer that THIS card puts <u> before <b> and that NO corpus card does that.

It is deliberately the reviewer's ONLY tool — `review_all` passes --strict-mcp-config and allows
just this one, so a reviewer that used to be tool-less cannot now wander off reading files.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP          # noqa: E402
import style_check                              # noqa: E402

mcp = FastMCP("style")


@mcp.tool()
def check_card(text: str) -> str:
    """Check ONE card's Text field against the owner's reference corpus. Call this for every card
    before deciding its verdict, and again on any replacement text you are about to propose.

    Returns four sections:
      BLOCKING   - properties the reference corpus violates ZERO times. A card with any BLOCKING
                   finding is `needs-fix`, always. These are measured, not asserted.
      UNUSUAL    - properties the corpus violates rarely, with the rate. Justify or change.
      COMPARABLE - the corpus cards structurally closest to this one. Judge shape against these.
      JUDGMENT   - questions no checker can settle (is this bold span a term to recall or the
                   frame? does the hint read like English in the blank?). You must answer these.

    Args:
        text: the card's Text field, with its {{cN::...}} clozes and <b>/<i>/<u> markup intact.
    """
    return style_check.render(text)


@mcp.tool()
def invariants() -> str:
    """The current corpus-derived rule table: every checked property with its measured corpus rate
    and tier. Use it to understand what BLOCKING means; you do not need it per card."""
    rows = style_check.derive()
    n = rows[0][5] if rows else 0
    out = [f"Derived from {n} owner-accepted corpus cards:", ""]
    for key, label, _fn, _fix, hits, _n, tier in rows:
        out.append(f"  [{tier:8}] {label}  ({hits} of {n})")
    return "\n".join(out)


if __name__ == "__main__":
    mcp.run()
