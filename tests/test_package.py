import json
from core import package as pkg


def make_source(sid, url, domain, quality=80, relevance=80, primary=0):
    return {
        "id": sid,
        "url": url,
        "canonical_url": url,
        "title": f"Title {sid}",
        "domain": domain,
        "source_type": "news",
        "is_primary": primary,
        "quality_score": quality,
        "relevance_score": relevance,
        "verification_status": "verified",
    }


def make_claim(cid, sid, text, confidence=80, claim_type="factual"):
    return {
        "id": cid,
        "source_id": sid,
        "claim": text,
        "claim_type": claim_type,
        "evidence": f"Evidence for {cid}",
        "confidence": confidence,
        "confidence_score": confidence,
        "confidence_level": "High",
        "confidence_explanation": "test",
    }


def test_source_claim_map_groups_claims_by_source():
    sources = [
        make_source(10, "https://a.com/1", "a.com"),
        make_source(20, "https://b.com/1", "b.com"),
    ]
    claims = [
        make_claim(1, 10, "Claim A"),
        make_claim(2, 10, "Claim B"),
        make_claim(3, 20, "Claim C"),
    ]
    research = {"topic": "Q?", "intent": "informational"}
    queries = [{"query": "q", "purpose": "p", "priority": 1}]
    result = json.loads(pkg.build_package(research, sources, claims, [], queries))
    assert result["source_claim_map"]["10"] == [1, 2]
    assert result["source_claim_map"]["20"] == [3]


def test_key_findings_respect_min_confidence():
    sources = [make_source(10, "https://a.com/1", "a.com")]
    claims = [
        make_claim(1, 10, "Low confidence claim", confidence=40),
        make_claim(2, 10, "High confidence claim", confidence=90),
    ]
    research = {"topic": "Q?", "intent": ""}
    queries = []
    result = json.loads(pkg.build_package(
        research, sources, claims, [], queries,
        min_confidence_for_key_findings=70,
    ))
    assert "High confidence claim" in result["key_findings"]
    assert "Low confidence claim" not in result["key_findings"]


def test_claim_includes_source_url():
    sources = [make_source(10, "https://a.com/1", "a.com")]
    claims = [make_claim(1, 10, "Claim A")]
    research = {"topic": "Q?", "intent": ""}
    result = json.loads(pkg.build_package(research, sources, claims, [], []))
    assert result["claims"][0]["source_url"] == "https://a.com/1"


def test_statistics_extracted_from_statistic_claims():
    sources = [make_source(10, "https://a.com/1", "a.com")]
    claims = [
        make_claim(1, 10, "Growth was 3.5%.", claim_type="statistic"),
        make_claim(2, 10, "Some other claim.", claim_type="factual"),
    ]
    research = {"topic": "Q?", "intent": ""}
    result = json.loads(pkg.build_package(research, sources, claims, [], []))
    assert len(result["statistics"]) == 1
    assert result["statistics"][0]["claim"] == "Growth was 3.5%."