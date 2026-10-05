from utils import normalize_url


def test_lowercases_scheme_and_host():
    assert normalize_url("HTTPS://Example.COM/Path") == "https://example.com/Path"


def test_strips_www_prefix():
    assert normalize_url("https://www.example.com/article") == "https://example.com/article"


def test_removes_trailing_slash():
    assert normalize_url("https://example.com/article/") == "https://example.com/article"


def test_keeps_root_slash():
    assert normalize_url("https://example.com/") == "https://example.com/"


def test_strips_fragment():
    assert normalize_url("https://example.com/article#section-2") == "https://example.com/article"


def test_removes_utm_params():
    url = "https://example.com/article?utm_source=newsletter&utm_medium=email"
    assert normalize_url(url) == "https://example.com/article"


def test_removes_fbclid_and_gclid():
    url = "https://example.com/article?fbclid=abc123&gclid=xyz"
    assert normalize_url(url) == "https://example.com/article"


def test_keeps_meaningful_query_params():
    url = "https://example.com/search?q=python&page=2"
    assert normalize_url(url) == "https://example.com/search?q=python&page=2"


def test_mixed_tracking_and_meaningful_params():
    url = "https://example.com/search?q=python&utm_source=x&page=2"
    assert normalize_url(url) == "https://example.com/search?q=python&page=2"


def test_empty_string():
    assert normalize_url("") == ""


def test_invalid_input_returns_stripped_string():
    # urlparse tolerates almost anything, but this at least shouldn't crash
    result = normalize_url("   not a url   ")
    assert isinstance(result, str)


def test_combines_multiple_rules():
    url = "HTTPS://WWW.Example.COM/Article/?utm_source=x#frag"
    assert normalize_url(url) == "https://example.com/Article"