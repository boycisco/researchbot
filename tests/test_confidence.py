from core.confidence import compute_confidence


def make_claim(claim_id, source_id, conf=50):
    return {"id": claim_id, "source_id": source_id, "confidence": conf}


def make_source(source_id, domain, quality=50, recency=50, is_primary=0):
    return {
        "id": source_id,
        "domain": domain,
        "quality_score": quality,
        "recency_score": recency,
        "is_primary": is_primary,
    }


def test_single_source_no_relationships():
    claim = make_claim(1, 10, conf=50)
    sources = {10: make_source(10, "example.com", quality=50, recency=50)}
    result = compute_confidence(claim, [claim], [], sources)
    # 0.40*50 + 0.30*50 + 0.15*100 + 0.10*50 + 0.05*0 = 55.0
    assert result["score"] == 55.0
    assert result["level"] == "Moderate"
    assert result["supporting_source_count"] == 1
    assert result["contradicting_source_count"] == 0
    assert result["distinct_domains"] == 1


def test_multiple_supporting_sources_across_domains():
    claim_a = make_claim(1, 10, conf=80)
    claim_b = make_claim(2, 20, conf=80)
    sources = {
        10: make_source(10, "a.com",  quality=80, recency=80, is_primary=1),
        20: make_source(20, "b.com",  quality=80, recency=80, is_primary=0),
    }
    rels = [{"claim_a": 1, "claim_b": 2, "relationship": "supports"}]
    result = compute_confidence(claim_a, [claim_a, claim_b], rels, sources)
    # 0.40*80 + 0.30*80 + 0.15*100 + 0.10*80 + 0.05*100 = 84.0
    assert result["score"] == 84.0
    assert result["level"] == "High"
    assert result["supporting_source_count"] == 2
    assert result["distinct_domains"] == 2
    assert result["has_primary"] is True


def test_contradiction_penalty_applied():
    claim_a = make_claim(1, 10, conf=50)
    claim_b = make_claim(2, 20, conf=50)
    sources = {
        10: make_source(10, "a.com", quality=50, recency=50),
        20: make_source(20, "b.com", quality=50, recency=50),
    }
    rels = [{"claim_a": 1, "claim_b": 2, "relationship": "contradicts"}]
    result = compute_confidence(claim_a, [claim_a, claim_b], rels, sources)
    # base = 55.0, minus 20 = 35.0
    assert result["score"] == 35.0
    assert result["level"] == "Low"
    assert result["contradicting_source_count"] == 1
    # Only the own source supports the claim; the other contradicts it.
    assert result["supporting_source_count"] == 1


def test_score_is_clamped_to_0_100():
    claim = make_claim(1, 10, conf=100)
    sources = {10: make_source(10, "x.com", quality=100, recency=100, is_primary=1)}
    result = compute_confidence(claim, [claim], [], sources)
    assert result["score"] <= 100.0

    claim_low = make_claim(2, 20, conf=0)
    sources_low = {20: make_source(20, "y.com", quality=0, recency=0)}
    # Add several contradictions to try to drive below zero
    rels = []
    claims = [claim_low]
    for i in range(10):
        c = make_claim(100 + i, 200 + i, conf=0)
        sources_low[200 + i] = make_source(200 + i, f"z{i}.com", quality=0, recency=0)
        claims.append(c)
        rels.append({"claim_a": 2, "claim_b": 100 + i, "relationship": "contradicts"})
    result_low = compute_confidence(claim_low, claims, rels, sources_low)
    assert result_low["score"] >= 0.0


def test_qualifies_relationship_does_not_affect_score():
    claim_a = make_claim(1, 10, conf=50)
    claim_b = make_claim(2, 20, conf=50)
    sources = {
        10: make_source(10, "a.com"),
        20: make_source(20, "b.com"),
    }
    rels = [{"claim_a": 1, "claim_b": 2, "relationship": "qualifies"}]
    result = compute_confidence(claim_a, [claim_a, claim_b], rels, sources)
    # Same as single source, no penalty, no bonus
    assert result["score"] == 55.0
    assert result["supporting_source_count"] == 1
    assert result["contradicting_source_count"] == 0