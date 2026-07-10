#!/usr/bin/env python3
"""GOLDEN REGRESSION TEST — the style linter must PASS the reference deck.

The house style is *measured from* the AnKing Neurogenetics deck (SKILL.md / MARKUP.md say so
explicitly). Therefore the linter must not hard-ERROR on the reference deck's own cards: if it
does, the linter — not the deck — is miscalibrated. This test is the anchor that would have caught
the linter drifting away from the real house style.

Fixture: tests/fixtures/neurogenetics_ref.jsonl — 368 cloze notes extracted from Neurogenetics.apkg
(regenerate with the extractor if the reference deck changes). The `source`/`tags` fields are
synthesized by the extractor, so this test asserts on SHAPE/MARKUP/STRUCTURE errors only.

Run:  .venv/bin/python -m unittest tests.test_reference_deck   (from repo root)
"""
import json, os, re, sys, unittest
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "classes", "ISF"))
import lint_cards  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "neurogenetics_ref.jsonl")
MAX_ERROR_RATE = 0.02   # <2% — one or two idiosyncratic AnKing cards may not match; the deck is the norm

# Synthetic-field errors come from the extractor fabricating source/tags — not real style defects.
_SYNTHETIC = ("missing source", "missing field", "tags missing", "tag has a space", "bad/missing type")


def _classify(err_msg):
    """Bucket an error line by rule, for the failure histogram."""
    m = err_msg.split(" ", 1)[1] if " " in err_msg else err_msg
    for key in ("distinct clozes", "distinct italic-answer", "TWO CONCEPTS", "unbalanced <b>",
                "unbalanced {{", "no {{c", "terminal period", "SUBJECT-FIRST"):
        if key in m:
            return key
    return m[:40]


class ReferenceDeckGolden(unittest.TestCase):
    def test_reference_deck_passes_linter(self):
        if not os.path.exists(FIXTURE):
            self.skipTest(f"fixture absent (it is copyrighted, gitignored) — regenerate with "
                          f"`python tests/extract_reference_fixture.py` from your Neurogenetics.apkg")
        with open(FIXTURE, encoding="utf-8") as fh:
            cards = [json.loads(l) for l in fh if l.strip()]
        self.assertEqual(len(cards), 368, "expected 368 reference cards")

        erroring, hist, examples = 0, Counter(), {}
        for i, c in enumerate(cards):
            errs = [e for e in lint_cards.lint_card(c, f"ref:{i}")[0]
                    if not any(s in e for s in _SYNTHETIC)]
            if errs:
                erroring += 1
                for e in errs:
                    k = _classify(e)
                    hist[k] += 1
                    examples.setdefault(k, []).append(lint_cards._strip(c["text"])[:80])

        rate = erroring / len(cards)
        if rate >= MAX_ERROR_RATE:
            report = [f"\nLINTER ERRORS ON {erroring}/{len(cards)} reference cards ({rate:.1%} >= {MAX_ERROR_RATE:.0%}):"]
            for k, n in hist.most_common():
                report.append(f"  {n:3}x  {k}")
                for ex in examples[k][:3]:
                    report.append(f"         e.g. {ex}")
            report.append("\nThese rules FALSE-POSITIVE on the house style — fix the linter, not the deck.")
            self.fail("\n".join(report))


if __name__ == "__main__":
    unittest.main(verbosity=2)
