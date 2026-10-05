---
name: provider
description: Use when adding or editing an AI, search, or fetch provider under ai/, stages/search.py, or stages/fetch.py, or when changing core/providers.py.
---

# Provider changes

You are working on the boundary between the research engine and an
external capability (AI generation, web search, or content fetching).

## Scope

You may **read** anything. You may **write**:

- `ai/<provider>.py`
- `stages/search.py`, `stages/fetch.py`
- `core/providers.py`
- `config.py` (only to add a new env var)
- `.env.example`
- `docs/providers.md`
- `tests/` for the new provider

Do not touch `core/worker.py` or any stage other than the one whose
provider you are adding.

## Contracts

AI providers must implement:

```python
def generate_text(prompt, temperature=None, max_output_tokens=None):
    -> {"success": True, "text": str}
    | {"success": False, "error": str}


def generate_json(prompt, temperature=None, max_output_tokens=None):
    -> {"success": True, "data": dict}
    | {"success": False, "error": str}
```

Search providers must return a list of:

```python
{
  "title": str,
  "url": str,
  "canonical_url": str,   # utils.normalize_url(url)
  "domain": str,          # utils.get_domain(url)
  "snippet": str,
  "rank": int,            # 1-based, search-engine order
}
```

Preserve search-engine ranking. Do not filter by domain extension
(.gov, .edu). Do not sort by snippet length.

## Rules

- Register the provider in `core/providers.py`. Nowhere else.
- Read provider selection from config (`AI_PROVIDER`,
  `SEARCH_PROVIDER`). Never hardcode.
- Every provider enforces its own timeout and rate limit internally.
  Do not leak provider-specific throttling into `core/worker.py`.
- Never silently fall back to another provider. If the selected
  provider fails, return an explicit error.
- Do not put prompts in the provider module. Prompts live in
  `ai/prompts.py` regardless of provider.
- Add a doc row in `docs/providers.md`.

## Verification

```bash
python -m health --with-ai
python -m evaluation.run --case simple-factual
python -m pytest tests/ -v
```

All three must succeed for the new provider to be considered wired in.