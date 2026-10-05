import sqlite3
from stages import compare


def make_claim(claim_id, source_id, text, evidence=""):
    return {
        "id": claim_id,
        "source_id": source_id,
        "claim": text,
        "evidence": evidence,
    }


def test_find_candidate_pairs_matches_similar_claims_from_different_sources():
    claims = [
        make_claim(1, 10, "Intermittent fasting reduces body weight."),
        make_claim(2, 20, "Intermittent fasting reduces body weight."),
    ]
    pairs = compare.find_candidate_pairs(claims)
    assert len(pairs) == 1


def test_find_candidate_pairs_skips_same_source():
    claims = [
        make_claim(1, 10, "Intermittent fasting reduces body weight."),
        make_claim(2, 10, "Intermittent fasting reduces body weight."),
    ]
    pairs = compare.find_candidate_pairs(claims)
    assert pairs == []


def test_find_candidate_pairs_skips_dissimilar_claims():
    claims = [
        make_claim(1, 10, "Intermittent fasting reduces body weight."),
        make_claim(2, 20, "The 2008 crisis began with mortgage defaults."),
    ]
    pairs = compare.find_candidate_pairs(claims)
    assert pairs == []


def test_find_candidate_pairs_respects_max_pairs():
    # Ten identical claims from ten different sources → many candidate pairs
    claims = [
        make_claim(i, i, "Same claim text repeated here.")
        for i in range(1, 11)
    ]
    pairs = compare.find_candidate_pairs(claims, max_pairs=3)
    assert len(pairs) <= 3


def test_sqlite3_row_input_is_supported():
    """The pipeline passes sqlite3.Row objects from the DB; make sure they work."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE claims (id INTEGER, source_id INTEGER, claim TEXT, evidence TEXT)")
    conn.execute("INSERT INTO claims VALUES (1, 10, 'X is true.', 'ev')")
    conn.execute("INSERT INTO claims VALUES (2, 20, 'X is true.', 'ev')")
    rows = conn.execute("SELECT * FROM claims").fetchall()
    pairs = compare.find_candidate_pairs(rows)
    assert len(pairs) == 1


def test_detect_contradictions_buckets_relationships():
    claims = [
        make_claim(1, 10, "A."),
        make_claim(2, 20, "B."),
        make_claim(3, 30, "C."),
        make_claim(4, 40, "D."),
    ]
    relationships = [
        {"claim_a": 1, "claim_b": 2, "relationship": "contradicts",
         "reason": "opposite results", "confidence": 80},
        {"claim_a": 1, "claim_b": 3, "relationship": "different_context",
         "reason": "different populations", "confidence": 70},
        {"claim_a": 1, "claim_b": 4, "relationship": "qualifies",
         "reason": "narrower scope", "confidence": 60},
    ]
    result = compare.detect_contradictions(claims, relationships)
    assert len(result["true_contradictions"]) == 1
    assert len(result["different_contexts"]) == 1
    assert len(result["qualifiers"]) == 1


def test_detect_contradictions_ignores_unknown_relationship():
    claims = [make_claim(1, 10, "A."), make_claim(2, 20, "B.")]
    relationships = [
        {"claim_a": 1, "claim_b": 2, "relationship": "supports",
         "reason": "", "confidence": 80},
    ]
    result = compare.detect_contradictions(claims, relationships)
    assert result["true_contradictions"] == []
    assert result["different_contexts"] == []
    assert result["qualifiers"] == []