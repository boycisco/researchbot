# Providers

The research engine depends on three capabilities, not on specific
vendors:

| Capability | Interface | Default implementation |
|---|---|---|
| AI generation | `generate_text()`, `generate_json()` | Gemini (`ai/gemini.py`) |
| Web search | `search_web(query, max_results)` | DuckDuckGo (`stages/search.py`) |
| Content fetching | `fetch_source(url)` | `requests` + `trafilatura` (`stages/fetch.py`) |

`core/providers.py` is the **only** place that knows which concrete
implementation is active. Every other module imports from
`core.providers`, not from `ai.gemini`, `stages.search`, or
`stages.fetch` directly.

This means: **you can replace any provider without touching the
pipeline.**

## Selecting a provider

Providers are chosen via environment variables (see `config.py`):

```env
AI_PROVIDER=gemini
SEARCH_PROVIDER=duckduckgo
```

If the requested provider isn't implemented, `core/providers.py`
raises `NotImplementedError` at the first call, rather than silently
falling back.

## Adding a new AI provider

Let's say you want to add OpenAI.

1. Write the provider module.

Create `ai/openai.py`:

```python
import openai
from config import OPENAI_API_KEY, AI_REQUEST_TIMEOUT_S


def generate_text(prompt, temperature=None, max_output_tokens=None):
    """
    Returns one of:
      {"success": True,  "text": "..."}
      {"success": False, "error": "..."}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            timeout=AI_REQUEST_TIMEOUT_S,
        )
        return {"success": True, "text": response.choices[0].message.content}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_json(prompt, temperature=None, max_output_tokens=None):
    """
    Same contract as generate_text, but returns:
      {"success": True,  "data": {...}}
      {"success": False, "error": "..."}
    """
    # ... same call, but parse the response as JSON
    # (see ai/gemini.py for a robust extraction pattern)
```

2. Register it.

Open `core/providers.py` and add a branch:

```python
def generate_text(prompt, temperature=None, max_output_tokens=None):
    if config.AI_PROVIDER == "gemini":
        return gemini.generate_text(prompt, temperature, max_output_tokens)
    if config.AI_PROVIDER == "openai":
        from ai import openai as openai_provider
        return openai_provider.generate_text(prompt, temperature, max_output_tokens)
    raise NotImplementedError(f"AI provider '{config.AI_PROVIDER}' not implemented")
```

Do the same for `generate_json`.

3. Set the env var.

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

4. Run the health check.

```bash
python -m health --with-ai
```

5. Run an evaluation case.

```bash
python -m evaluation.run --case simple-factual
```

If that completes and produces a sensible answer, the provider is
wired correctly.

## Adding a new search provider

Same pattern. Create `stages/brave_search.py` (or add to
`stages/search.py`), then register it in `core/providers.py`.

The provider must normalize results to:

```python
{
    "title":   str,
    "url":     str,           # original URL
    "canonical_url": str,     # utils.normalize_url(url)
    "domain":  str,           # utils.get_domain(url)
    "snippet": str,
    "rank":    int,           # 1-based, search-engine order
}
```

Do not filter by domain extension (.gov, .edu, etc.). Let the
verification stage decide quality. Do not rank by snippet length.
Preserve the search engine's ranking.

## Adding a new fetcher

The fetcher is a bit different because it doesn't need provider
switching in practice — the extraction library is the only variable.
If you want to swap `trafilatura` for `readability-lxml` or similar,
edit `stages/fetch.py` directly and preserve the return contract:

```python
{
    "success":     bool,
    "content":     str,        # extracted main text
    "word_count":  int,
    "title":       str,
    "published_at": str,       # may be empty
    "status":      str,        # "fetched" on success
    "http_status": int,
    "canonical_url": str,
}
```

On failure:

```python
{
    "success": False,
    "error":   str,
    "status":  "timeout" | "http_error" | "extraction_failed"
             | "insufficient_content" | "network_error" | "unknown_error",
    "http_status": int,        # if available
}
```

## What not to do

Do not call `ai.gemini` or `stages.search` directly from
`core/worker.py`, `stages/*`, or anywhere else. Always go through
`core/providers`.

Do not implement fallbacks that silently swap providers. If the
primary provider fails, fail loudly. Provider selection happens in
configuration, not at runtime.

Do not add prompts to the provider module. Prompts live in
`ai/prompts.py` regardless of which provider is active.

Do not put provider-specific rate limiting anywhere except the
provider module itself. Gemini's rate limiter lives in
`ai/gemini.py`; another provider's limiter lives in its own file.