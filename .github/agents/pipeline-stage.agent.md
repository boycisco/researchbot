---
name: pipeline-stage
description: Use when changing a file in stages/ (search, fetch, verify, claims, compare, writer, checker). Knows the input/output contract each stage must honor and the boundary rules.
---

# Pipeline stage changes

You are editing a single stage of the research pipeline.

## Scope

You may **read** anything. You may **write** only the stage file you
were asked about, plus its tests under `tests/`.

If your change requires editing `core/worker.py`, `ai/prompts.py`, or
`core/providers.py`, stop and tell the user. Those are separate
concerns with separate owners.

## Contracts each stage must honor

- `stages/search.py`
  - `generate_queries(analysis_json, max_queries) -> list[dict] | None`
  - `search_web(query, max_results) -> list[{title, url, canonical_url, domain, snippet, rank}]`
- `stages/fetch.py`
  - `fetch_source(url, timeout=20) -> {success, content, word_count, title, published_at, status, http_status, canonical_url}` or `{success: False, error, status}`
- `stages/verify.py`
  - `verify_sources(sources, research_context) -> list[{status, relevance_score, quality_score, evidence_score, recency_score, bias_score, completeness_score, source_type, is_primary}]`
- `stages/claims.py`
  - `extract_claims_batch(sources_with_content, research_question) -> list[{source_id, claim, claim_type, evidence, support_level, confidence}]`
- `stages/compare.py`
  - `find_candidate_pairs(claims, max_pairs) -> list[(claim_a, claim_b, score)]`
  - `compare_claims_batch(pairs) -> list[dict | None]`
  - `detect_contradictions(claims, relationships) -> {true_contradictions, different_contexts, qualifiers}`
- `stages/writer.py`
  - `write_answer(package_content, original_question, intent) -> str | None`
  - `clean_answer(text) -> str`
- `stages/checker.py`
  - `check_answer(answer, package_content) -> {status, sentences_checked, findings, problematic}`

Do not change a return shape. Do not add fields to returned dicts
without a matching change in the caller.

## Rules

1. Use `core.providers` for AI, search, and fetch calls. Never import
   `ai.gemini`, `ddgs`, or `requests` directly.
2. Prompts live in `ai/prompts.py`. Do not embed prompt text here.
3. Return explicit failure. No silent empty results.
4. Preserve the pipeline order. No stage may call another stage.
5. When you change behavior, add or update a test in `tests/`.

## Verification before you finish

```bash
python -m pytest tests/ -v
python cli.py "test" --depth quick
```

Both must succeed. Paste the log if the user asked for evidence.