# Changelog

All notable changes to this project are documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).
This project does not yet follow semantic versioning — it is pre-1.0
and things move as they need to.

## [Unreleased]

### Added

- `ResearchRequest` dataclass for validating topics before they enter
  the pipeline (`request.py`).
- Provider boundary (`core/providers.py`) so the pipeline depends on
  capabilities, not vendors. Currently only Gemini (AI), DuckDuckGo
  (search), and `requests` + `trafilatura` (fetch) are implemented.
- Deterministic, explainable confidence scoring per claim
  (`core/confidence.py`). Score is computed from AI confidence, source
  quality, source independence, recency, primary-source bonus, and a
  contradiction penalty. An explanation string is stored with each
  claim.
- Per-sentence fact-checker with an automatic revision loop
  (`stages/checker.py`, `stages/writer.py`). Unsupported or
  contradicted sentences trigger up to two revisions; if the answer
  still fails, the job is marked `failed` and nothing is delivered.
- Expanded claim relationships: `supports`, `partially_supports`,
  `contradicts`, `qualifies`, `different_context`, `related`,
  `unrelated`. True contradictions are now separated from
  different-context cases (`stages/compare.py`).
- Verbatim evidence is stored on every claim (`stages/claims.py`).
- Canonical URL normalization with tracking-parameter stripping and
  `www.` removal (`utils.normalize_url`). Database-level deduplication
  by canonical URL (`core/database.py`).
- Batch verification and batch claim-extraction calls to reduce AI
  request volume (`stages/verify.py`, `stages/claims.py`).
- Rate limiting, retry-with-backoff, and JSON extraction on the Gemini
  provider (`ai/gemini.py`).
- Migration system in `init_db()` — additive and idempotent
  (`core/database.py`).
- CLI entry point for testing without Telegram (`cli.py`).
- Documentation: `README.md`, `docs/ARCHITECTURE.md`,
  `.github/CONTRIBUTING.md`, `.github/SECURITY.md`,
  `.github/CODE_OF_CONDUCT.md`.

### Changed

- Project layout reorganized into packages:
  - `ai/` — Gemini + prompts
  - `core/` — orchestration, storage, confidence, package builder
  - `stages/` — one module per pipeline stage
  - `ui/` — Telegram formatting
- Writer prompt rewritten to enforce per-sentence citations,
  renumber sources from 1, forbid leaked instructions, and align
  wording with confidence levels.
- Writer output is post-processed to strip leaked prompt artifacts
  (`stages/writer.py` → `clean_answer`).
- Research package structure expanded to include `search_strategy`,
  `source_claim_map`, per-claim `source_url`, and full confidence
  fields (`core/package.py`).
- `.github/` and `docs/` created; community files moved into
  `.github/`.

### Fixed

- Duplicate sources being inserted when the same URL appeared in
  multiple search queries.
- `sqlite3.Row` objects failing on `.get()` calls in claim comparison
  and package building.
- Migrations previously only checked the `sources` table; now
  migrations are applied without a table-specific pre-check, so
  `claims` migrations actually run.
- `bias_score` and `completeness_score` were referenced by the
  verifier but not present in the database until a migration was
  added.
- FutureWarning from the deprecated `google.generativeai` package is
  suppressed at import time.
- Noisy third-party loggers (`ddgs`, `primp`, `hickory_net`,
  `trafilatura`) silenced to `ERROR`.

### Known limitations

- Only Gemini and DuckDuckGo are implemented.
- No primary-source discovery.
- No research depth modes yet (planned: quick / standard / deep /
  exhaustive).
- No automated test suite.
- No job recovery after a crash; failed jobs stay failed.
- No evidence-graph UI.
- Confidence weights are heuristic, not tuned against a benchmark.

## [0.0.1] — Initial scaffold

### Added

- First working end-to-end pipeline: analysis → query generation →
  search → fetch → verify → claims → compare → package → write →
  check.
- SQLite schema for users, research, queries, sources, claims,
  relationships, packages, answers, user states.
- Telegram interface with `/start`, `/research`, `/history`, `/get`,
  `/cancel`.
- Progress updates delivered by editing a single Telegram message.