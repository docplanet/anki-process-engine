#!/usr/bin/env python3
"""_harness.py — the shared spine of the review harness.

Two jobs, both tiny and both deterministic, kept in ONE place so the reviewer and the
committer compute them identically:

  * card_hash(text, extra, source) — a stable fingerprint of a card's CONTENT. A review
    verdict is recorded against this hash; edit the card and the hash changes, so the old
    verdict no longer applies and the card must be reviewed again. This is what stops a
    card being edited after its `pass` and slipped into the deck as if reviewed.

  * the manifest — a SHA-256 of every file that defines "acceptable" (the gate scripts, the
    okf/ rulebook, the corpus). `manifest.lock` records the blessed hashes; verify_manifest()
    compares the current tree against it. If a check or a rule was edited, the manifest no
    longer matches and `commit` refuses until the change is deliberately re-blessed
    (`build_deck bless`). This is the backstop for the permission layer: a rule change can
    never silently reach output.

Nothing here talks to Anki or judges a card — it only hashes. `norm()` is reused from
check_cards so a card hashes the same way it is quote-checked (case/space/punctuation-insensitive).
"""
from __future__ import annotations
import glob
import hashlib
import json
import os

from check_cards import norm  # single source of truth for text normalization

HERE = os.path.dirname(os.path.abspath(__file__))
OKF = os.path.join(HERE, "okf")
CORPUS = os.path.join(HERE, "reference", "style_corpus.jsonl")
MANIFEST = os.path.join(HERE, "manifest.lock")

# The files that define "acceptable". Editing any of them changes the manifest and blocks
# commits until `build_deck bless`. Gate code + the whole okf/ rulebook + the style corpus.
_PROTECTED_SCRIPTS = ("strict_shape.py", "check_cards.py", "build_deck.py",
                      "review_loop.py", "content_check.py", "lint_cards.py", "_harness.py")


def protected_files() -> list[str]:
    files = [os.path.join(HERE, f) for f in _PROTECTED_SCRIPTS]
    files += sorted(glob.glob(os.path.join(OKF, "**", "*.md"), recursive=True))
    files.append(CORPUS)
    return [f for f in files if os.path.exists(f)]


def card_hash(text: str, extra: str = "", source: str = "") -> str:
    """Stable content fingerprint. Normalized so whitespace/punctuation reflow does not force a
    re-review, but any change to the words, the role tags, or the cloze structure does."""
    return hashlib.sha256(norm(f"{text} \x1f {extra} \x1f {source}").encode()).hexdigest()


def _file_sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_manifest() -> dict[str, str]:
    """{repo-relative path -> sha256} for every protected file present right now."""
    return {os.path.relpath(f, HERE): _file_sha(f) for f in protected_files()}


def manifest_hash(m: dict[str, str] | None = None) -> str:
    """One hash standing for the whole ruleset — recorded on each verdict so a verdict made
    under a since-edited ruleset is detectable."""
    m = compute_manifest() if m is None else m
    return hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()


def read_manifest() -> dict[str, str] | None:
    if not os.path.exists(MANIFEST):
        return None
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def write_manifest() -> dict[str, str]:
    m = compute_manifest()
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=2, sort_keys=True)
        f.write("\n")
    return m


# ── the verdict ledger ──────────────────────────────────────────────────────────
# A per-deck record of review verdicts, keyed by card_hash so a re-review of the same content
# overwrites cleanly and an edited card (new hash) has no entry until it is reviewed again.
# Only review_loop.py writes it; commit reads it and trusts a `pass` only when the recorded
# card_hash still matches the card AND the verdict was made under the current manifest.

def ledger_path(out_dir: str) -> str:
    return os.path.join(out_dir, ".review_ledger.json")


def read_ledger(out_dir: str) -> dict[str, dict]:
    p = ledger_path(out_dir)
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def write_ledger(out_dir: str, ledger: dict[str, dict]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(ledger_path(out_dir), "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


def verify_manifest() -> tuple[bool, list[tuple[str, str]]]:
    """(ok, changed). `changed` is [(path, 'modified'|'added'|'removed'), …]. ok iff nothing
    differs from the blessed manifest.lock."""
    locked = read_manifest()
    if locked is None:
        return False, [("manifest.lock", "missing — run `build_deck bless`")]
    current = compute_manifest()
    changed = []
    for path in sorted(set(locked) | set(current)):
        old, new = locked.get(path), current.get(path)
        if old != new:
            changed.append((path, "added" if old is None else
                                  "removed" if new is None else "modified"))
    return (not changed), changed
