import pytest
from request import ResearchRequest, DEPTH_PROFILES


def test_empty_topic_raises():
    with pytest.raises(ValueError):
        ResearchRequest(topic="")


def test_whitespace_topic_raises():
    with pytest.raises(ValueError):
        ResearchRequest(topic="   ")


def test_topic_is_stripped():
    r = ResearchRequest(topic="  hello  ")
    assert r.topic == "hello"


def test_invalid_depth_raises():
    with pytest.raises(ValueError):
        ResearchRequest(topic="x", depth="banana")


def test_default_depth_is_standard():
    r = ResearchRequest(topic="x")
    assert r.depth == "standard"


def test_all_depths_have_a_profile():
    for depth in DEPTH_PROFILES:
        r = ResearchRequest(topic="x", depth=depth)
        profile = r.profile()
        assert isinstance(profile, dict)
        assert "max_queries" in profile
        assert "max_revisions" in profile


def test_profile_returns_a_copy():
    r = ResearchRequest(topic="x", depth="quick")
    a = r.profile()
    a["max_queries"] = 999
    b = r.profile()
    assert b["max_queries"] != 999


def test_source_preferences_normalized_to_lowercase():
    r = ResearchRequest(topic="x", source_preferences=["GOV", "Edu"])
    assert r.source_preferences == ["gov", "edu"]


def test_invalid_output_format_falls_back_to_telegram():
    r = ResearchRequest(topic="x", output_format="pdf")
    assert r.output_format == "telegram"