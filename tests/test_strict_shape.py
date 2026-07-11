#!/usr/bin/env python3
"""Validation for the STRICT shape gate (strict_shape.py) — the mechanical "mold".

Unlike test_reference_deck.py (which asserts the *legacy* linter stays PERMISSIVE, <2% error),
this asserts the strict checker is CORRECT both directions:
  - strict_accept.jsonl : one card per allowed template (T1–T5, LIST) — each must be accepted
    AND classified to the expected template.
  - strict_reject.jsonl : known-bad cards — each must be rejected with the expected reason code.
A third test asserts idempotence (a card yields exactly one template XOR >=1 reason), and a
reference-fidelity test guards that the mold keeps accepting the bulk of the real gold deck.

Run:  .venv/bin/python -m unittest tests.test_strict_shape   (from repo root)
"""
import json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "classes", "ISF"))
import strict_shape  # noqa: E402

ACCEPT = os.path.join(HERE, "fixtures", "strict_accept.jsonl")
REJECT = os.path.join(HERE, "fixtures", "strict_reject.jsonl")
REF = os.path.join(HERE, "fixtures", "neurogenetics_ref.jsonl")
REF_MIN_ACCEPT = 0.90   # the mold must accept >=90% of the real gold deck (rest = genuine oddities)


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


class StrictAccept(unittest.TestCase):
    def test_every_template_accepted_and_classified(self):
        for row in _load(ACCEPT):
            res = strict_shape.classify_card(row["card"])
            self.assertTrue(res.ok, f"{row['id']} wrongly REJECTED: {res.reasons}")
            self.assertEqual(res.template, row["expect_template"],
                             f"{row['id']} classified {res.template}, expected {row['expect_template']}")


class StrictReject(unittest.TestCase):
    def test_every_bad_card_rejected_with_reason(self):
        for row in _load(REJECT):
            res = strict_shape.classify_card(row["card"])
            self.assertFalse(res.ok, f"{row['id']} wrongly ACCEPTED as {res.template}")
            self.assertIn(row["expect_reason"], res.reasons,
                          f"{row['id']} rejected for {res.reasons}, expected {row['expect_reason']}")


class Idempotence(unittest.TestCase):
    def test_exactly_template_xor_reasons(self):
        for row in _load(ACCEPT) + _load(REJECT):
            res = strict_shape.classify_card(row["card"])
            has_tpl = res.template is not None
            has_reasons = len(res.reasons) > 0
            self.assertNotEqual(has_tpl, has_reasons,
                                f"{row['id']}: template={res.template} reasons={res.reasons} "
                                f"(must be exactly one)")
            self.assertEqual(res.ok, has_tpl)


class ReferenceFidelity(unittest.TestCase):
    def test_mold_accepts_bulk_of_gold_deck(self):
        if not os.path.exists(REF):
            self.skipTest("reference fixture absent (copyrighted, gitignored)")
        cards = _load(REF)
        ok = sum(1 for c in cards if strict_shape.classify_card(c).ok)
        rate = ok / len(cards)
        self.assertGreaterEqual(rate, REF_MIN_ACCEPT,
                                f"mold accepts only {rate:.1%} of the gold deck (<{REF_MIN_ACCEPT:.0%}) "
                                f"— it has drifted from the reference templates")


if __name__ == "__main__":
    unittest.main(verbosity=2)
