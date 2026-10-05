from stages import checker


def test_returns_verification_error_on_ai_failure(monkeypatch):
    def fake_generate_json(prompt, **kwargs):
        return {"success": False, "error": "boom"}

    monkeypatch.setattr("stages.checker.providers.generate_json", fake_generate_json)
    result = checker.check_answer("Some answer.", "{}")
    assert result["status"] == "verification_error"
    assert result["findings"] == []
    assert result["problematic"] == []


def test_does_not_trust_the_ai_summary(monkeypatch):
    """If the AI says 'passed' but includes an unsupported sentence, we still fail."""
    def fake_generate_json(prompt, **kwargs):
        return {
            "success": True,
            "data": {
                "status": "passed",  # lie
                "sentences_checked": 2,
                "findings": [
                    {"sentence": "A.", "classification": "supported", "reason": ""},
                    {"sentence": "B.", "classification": "unsupported",
                     "reason": "not in package"},
                ],
            },
        }

    monkeypatch.setattr("stages.checker.providers.generate_json", fake_generate_json)
    result = checker.check_answer("Some answer.", "{}")
    assert result["status"] == "failed"
    assert len(result["problematic"]) == 1
    assert result["problematic"][0]["classification"] == "unsupported"


def test_unknown_classification_defaults_to_uncertain(monkeypatch):
    def fake_generate_json(prompt, **kwargs):
        return {
            "success": True,
            "data": {
                "status": "failed",
                "sentences_checked": 1,
                "findings": [
                    {"sentence": "A.", "classification": "banana", "reason": ""},
                ],
            },
        }

    monkeypatch.setattr("stages.checker.providers.generate_json", fake_generate_json)
    result = checker.check_answer("Some answer.", "{}")
    assert result["findings"][0]["classification"] == "uncertain"


def test_all_supported_sentences_pass(monkeypatch):
    def fake_generate_json(prompt, **kwargs):
        return {
            "success": True,
            "data": {
                "status": "passed",
                "sentences_checked": 2,
                "findings": [
                    {"sentence": "A.", "classification": "supported", "reason": ""},
                    {"sentence": "B.", "classification": "supported", "reason": ""},
                ],
            },
        }

    monkeypatch.setattr("stages.checker.providers.generate_json", fake_generate_json)
    result = checker.check_answer("Some answer.", "{}")
    assert result["status"] == "passed"
    assert result["problematic"] == []
    assert result["sentences_checked"] == 2


def test_malformed_findings_are_dropped(monkeypatch):
    def fake_generate_json(prompt, **kwargs):
        return {
            "success": True,
            "data": {
                "status": "passed",
                "findings": [
                    {"sentence": "A.", "classification": "supported"},
                    {"classification": "supported"},   # missing sentence
                    "not a dict",
                    None,
                ],
            },
        }

    monkeypatch.setattr("stages.checker.providers.generate_json", fake_generate_json)
    result = checker.check_answer("Some answer.", "{}")
    assert result["sentences_checked"] == 1