"""Regression tests for the style checker, the dedup pass, and --sources resolution.

This is the whole suite. It replaced `test_strict_shape.py`, which covered a module that had stopped
governing anything, against a fixture of the AnKing deck the project had deprecated — so nothing
tested the code that actually decides what ships.

The central property is SELF-CONSISTENCY: every rule the checker calls BLOCKING must be one the
corpus keeps perfectly. Add a predicate the corpus contradicts and
`test_blocking_rules_have_zero_corpus_violations` fails — which is precisely the bug that shipped
four times ("always cloze the subject", "always have hints", strict_shape's T1-T5 templates,
"never force-cloze it"). Rules are derived, so this test is what keeps them honest.

Corpus-dependent tests carry @needs_corpus and skip on CI, where the corpus is gitignored. The
dedup, --sources and judgment tests need no corpus and always run.
"""
import os
import sys

import pytest

ISF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "classes", "ISF")
sys.path.insert(0, ISF)

style_check = pytest.importorskip("style_check")

CORPUS = style_check.load_corpus()

# The corpus is pulled from the owner's Anki and gitignored, so anything measuring against it must
# skip on CI. Apply this PER TEST, not module-wide: a module-level skip made CI green while running
# nothing at all, and the dedup / --sources tests need no corpus and should always run.
needs_corpus = pytest.mark.skipif(
    not CORPUS, reason="no style_corpus.jsonl — run `build_deck corpus`")


# ── the self-consistency property that matters most ──────────────────────────
@needs_corpus
def test_blocking_rules_have_zero_corpus_violations():
    """A BLOCKING rule must have literally no counterexample in the owner's accepted cards."""
    for key, _label, fn, _fix, hits, _n, tier in style_check.derive(CORPUS):
        if tier == "BLOCKING":
            assert hits == 0, f"{key} is BLOCKING but {hits} corpus cards violate it"


@needs_corpus
def test_every_corpus_card_passes_the_blocking_tier():
    """The corpus is 'acceptable by definition' — no accepted card may be blocked."""
    for text in CORPUS:
        blocking = style_check.check(text, CORPUS)["blocking"]
        assert not blocking, f"corpus card blocked by {[b['rule'] for b in blocking]}: {text[:90]}"


@needs_corpus
def test_tiers_are_exhaustive_and_disjoint():
    tiers = {t for *_, t in style_check.derive(CORPUS)}
    assert tiers <= {"BLOCKING", "UNUSUAL", "allowed"}


# ── the defects that actually shipped, as regressions ────────────────────────
SHIPPED_DEFECTS = [
    # id,        text,                                                        expected rule
    ("bone-001", "The <u>principal functions</u> of <b>bone</b> are "
                 "{{c1::<i>support</i>::what four?}}", "u_before_b"),
    ("bone-008", "The <u>functional unit</u> of <b>compact bone</b> is the "
                 "{{c1::<i>osteon</i>::what?}}", "u_before_b"),
    ("bone-028", "{{c1::<b>PTH</b>::which hormone?}} causes {{c3::<b>osteoblasts</b>::which cells?}} "
                 "to {{c2::<i>stop producing osteoid</i>::what effect?}}", "two_bold_clozes"),
]


@pytest.mark.parametrize("cid,text,rule", SHIPPED_DEFECTS)
@needs_corpus
def test_shipped_defect_is_blocked(cid, text, rule):
    """Each of these was APPROVED by the tool-less reviewer and would have reached Anki."""
    blocking = style_check.check(text, CORPUS)["blocking"]
    assert rule in {b["rule"] for b in blocking}, f"{cid}: {rule} not caught"


@needs_corpus
def test_clean_card_is_not_blocked():
    clean = "{{c1::<b>Lacunae</b>::what structures?}} contain {{c2::<i>osteocytes</i>::what cells?}}"
    assert not style_check.check(clean, CORPUS)["blocking"]


@needs_corpus
def test_the_tier_follows_the_corpus_not_a_hardcoded_list():
    """The point of deriving: a rule's tier is a FUNCTION of the reference deck, not a constant.

    This test used to assert that facet-without-answer was UNUSUAL, because the old hand-built
    corpus did it once in 84 cards. Swapping the reference deck to the LLM-authored Bone deck made
    it 0 of 37 — so it became BLOCKING and the old assertion failed, correctly. Pin the mechanism
    instead: every tier a rule can hold must be justified by its own measured count."""
    for key, _label, _fn, _fix, hits, n, tier in style_check.derive(CORPUS):
        if tier == "BLOCKING":
            assert hits == 0, f"{key} blocks on {hits}/{n}"
        elif tier == "UNUSUAL":
            assert 0 < hits <= style_check.UNUSUAL_MAX * n, f"{key} advises on {hits}/{n}"
        else:
            assert hits > style_check.UNUSUAL_MAX * n, f"{key} is silent on {hits}/{n}"


# ── trailing prose: the owner's "it must end on the answer" ──────────────────
TRAILING = [
    ("{{c1::<b>Volkmann's canals</b>::which?}} are {{c2::<i>perpendicular</i>::how?}} "
     "to Haversian canals"),
    ("<b>Immature bone</b> has {{c1::<i>randomly arranged</i>::what arrangement?}} collagen fibers"),
    ("{{c1::<b>PTH</b>::which hormone?}} acts on bone to {{c2::<i>raise</i>::raise or lower?}} "
     "low blood calcium levels to normal"),
]


@pytest.mark.parametrize("card", TRAILING)
@needs_corpus
def test_trailing_prose_is_blocked(card):
    """The answer is a fragment and the rest of the sentence dangles unstyled after it."""
    assert "trailing_prose" in {b["rule"] for b in style_check.check(card, CORPUS)["blocking"]}


@pytest.mark.parametrize("card", [
    "{{c1::<b>Lacunae</b>::what?}} contain {{c2::<i>osteocytes</i>::what cells?}}",
    ("{{c1::<b>Volkmann's canals</b>::which?}} are {{c2::<u>perpendicular</u>::how?}} to "
     "{{c3::<i>Haversian canals</i>::to what?}}"),
    "{{c1::<b>Five</b>::how many?}} amino acids are charged at {{c2::<i>physiological</i>::which?}} pH",
])
@needs_corpus
def test_card_ending_on_its_answer_is_clean(card):
    """Including the one-trailing-word shape the corpus itself uses ('... pH')."""
    assert "trailing_prose" not in {b["rule"] for b in style_check.check(card, CORPUS)["blocking"]}


@needs_corpus
def test_trailing_prose_ignores_the_hint():
    """A hint sits after </i> INSIDE the braces. Counting it as trailing prose flags ~79% of the
    corpus and is precisely the bug that made this rule look like it wasn't a rule."""
    hinted = "{{c1::<b>Lacunae</b>::what structures?}} contain {{c2::<i>osteocytes</i>::what cells?}}"
    assert not style_check.check(hinted, CORPUS)["blocking"]


# ── the tool's other two sections ────────────────────────────────────────────
@needs_corpus
def test_comparable_never_mixes_image_and_prose_cards():
    """Image cards are useless models for prose cards; this ranking bug shipped once."""
    prose = "{{c1::<b>Lacunae</b>::what structures?}} contain {{c2::<i>osteocytes</i>::what cells?}}"
    for c in style_check.comparable(prose, CORPUS):
        assert "<img" not in c


@needs_corpus
def test_comparable_returns_role_relevant_examples():
    """A card clozing {b,u} should be shown corpus cards that also cloze <u>."""
    card = ("{{c1::<b>Parathyroid hormone</b>::which hormone?}} acts on bone to "
            "{{c2::<u>raise</u>::raise or lower?}} low blood calcium")
    got = style_check.comparable(card, CORPUS)
    assert got, "no comparable cards returned"
    assert any("<u" in c for c in got), "none of the comparables cloze a <u> facet"


def test_judgment_asks_about_a_visible_bold_subject():
    """Whether a visible <b> is a term or a frame is the reviewer's call, never the checker's."""
    qs = style_check.judgment("<b>Bone</b> is {{c1::<i>hard</i>::how?}}")
    assert any("Bone" in q for q in qs)


def test_judgment_never_returns_a_verdict():
    for q in style_check.judgment("<b>Bone</b> is {{c1::<i>hard</i>::how?}}"):
        assert not q.lower().startswith(("violation", "error", "fail"))


# ── the write-path backstop ──────────────────────────────────────────────────
@needs_corpus
def test_backstop_refuses_a_blocking_card():
    import build_deck
    bad = [{"id": "x", "text": "The <u>facet</u> of <b>subj</b> is {{c1::<i>v</i>::what?}}"}]
    assert build_deck._style_backstop(bad), "backstop let a u-before-b card through"


@needs_corpus
def test_backstop_passes_clean_cards():
    import build_deck
    ok = [{"id": "y", "text": "{{c1::<b>Lacunae</b>::what?}} contain {{c2::<i>osteocytes</i>::what cells?}}"}]
    assert build_deck._style_backstop(ok) == []


# ── scope is STATED (--sources), not inferred ────────────────────────────────
def test_sources_matches_url_encoded_filenames(tmp_path):
    """Downloads arrive as 'Bone%20Histology%20Power%20Point%20Slides.ppt.txt' and nobody types
    that — 'powerpoint' has to find it."""
    import build_deck
    src = tmp_path / "out" / "sources"
    src.mkdir(parents=True)
    (src / "Bone%20Histology%20Power%20Point%20Slides.ppt.txt").write_text("x")
    (src / "slides-ocr.txt").write_text("x")
    got, missing = build_deck.resolve_sources(str(tmp_path), "powerpoint")
    assert not missing and len(got) == 1 and "Power%20Point" in got[0]


def test_sources_reports_a_named_source_that_is_absent(tmp_path):
    """A source you asked for and did not get is an error, never a silent omission."""
    import build_deck
    (tmp_path / "out" / "sources").mkdir(parents=True)
    (tmp_path / "out" / "sources" / "slides.txt").write_text("x")
    _got, missing = build_deck.resolve_sources(str(tmp_path), "slides,transcript,junqueira")
    assert missing == ["transcript", "junqueira"]


def test_no_sources_spec_means_every_extracted_source(tmp_path):
    import build_deck
    src = tmp_path / "out" / "sources"
    src.mkdir(parents=True)
    (src / "a.txt").write_text("x")
    (src / "b.txt").write_text("x")
    got, missing = build_deck.resolve_sources(str(tmp_path), "")
    assert len(got) == 2 and missing == []


# ── dedup ────────────────────────────────────────────────────────────────────
def test_dedup_catches_a_wordier_restatement():
    """The real duplicate shape. Jaccard scores this pair 0.60 and lets it through; containment
    scores it 1.00, because everything the first card teaches is already in the second."""
    import build_deck
    cards = [
        {"id": "a", "text": "{{c1::<b>Lacunae</b>::what?}} contain {{c2::<i>osteocytes</i>::what cells?}}"},
        {"id": "b", "text": "<b>Lacunae</b> are spaces that contain {{c1::<i>osteocytes</i>::what?}}"},
    ]
    assert build_deck.mark_duplicates(cards) == [("b", "a")]
    assert cards[1]["status"] == "duplicate"
    assert "a" in cards[1]["note"]


def test_dedup_leaves_distinct_facts_alone():
    import build_deck
    cards = [
        {"id": "c", "text": "{{c1::<b>Osteoclasts</b>::which cells?}} {{c2::<i>resorb bone</i>::do what?}}"},
        {"id": "d", "text": "{{c1::<b>Osteoblasts</b>::which cells?}} {{c2::<i>synthesize osteoid</i>::do what?}}"},
    ]
    assert build_deck.mark_duplicates(cards) == []
    assert all(c.get("status") != "duplicate" for c in cards)


def test_dedup_never_deletes():
    import build_deck
    cards = [{"id": "a", "text": "{{c1::<b>Lacunae</b>::what?}} contain {{c2::<i>osteocytes</i>::x?}}"},
             {"id": "b", "text": "<b>Lacunae</b> are spaces that contain {{c1::<i>osteocytes</i>::y?}}"}]
    build_deck.mark_duplicates(cards)
    assert len(cards) == 2, "a duplicate is flagged and kept, never dropped"


def test_dedup_ignores_markup_and_hints():
    """Two cards teaching one fact collide however differently they are marked up."""
    import build_deck
    cards = [{"id": "a", "text": "{{c1::<b>Osteon</b>::what?}} is the {{c2::<i>functional unit of compact bone</i>::what?}}"},
             {"id": "b", "text": "The <u>functional unit</u> of compact bone is the {{c1::<i>osteon</i>::which?}}"}]
    assert build_deck.mark_duplicates(cards) == [("b", "a")]
