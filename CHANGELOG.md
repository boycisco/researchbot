# Changelog

All notable changes to this project are documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).
This project does not yet follow semantic versioning — it is pre-1.0
and things move as they need to.

## [Unreleased]

### Added

- **Research depth modes.** `quick`, `standard`, `deep`, `exhaustive`,
  each with its own query budget, source budget, claim-pair budget,
  key-findings threshold, and revision limit. Defined in
  `request.py → DEPTH_PROFILES`.
- **Deterministic, explainable confidence scoring** per claim
  (`core/confidence.py`). Score is computed from AI confidence, source
  quality, source independence, recency, primary-source bonus, and a
  contradiction penalty. An explanation string is stored with each
  claim.
- **Per-sentence fact-checker** with automatic revision loop
  (`stages/checker.py`, `stages/writer.py`). Unsupported or
  contradicted sentences trigger up to N revisions; if the answer
  still fails, the job is marked `failed` and nothing is delivered.
- **Expanded claim relationships**: `supports`, `partially_supports`,
  `contradicts`, `qualifies`, `different_context`, `related`,
  `unrelated`. True contradictions are separated from
  different-context cases (`stages/compare.py`).
- **Batched claim comparison.** All candidate pairs classified in one
  AI call by default; per-pair mode available via `COMPARE_MODE`.
- **Verbatim evidence** stored on every claim (`stages/claims.py`).
- **Canonical URL normalization** with tracking-parameter stripping
  and `www.` removal (`utils.normalize_url`). Database-level
  deduplication by canonical URL (`core/database.py`).
- **Batch verification and batch claim extraction** to reduce AI
  request volume (`stages/verify.py`, `stages/claims.py`).
- **Rate limiting, retry-with-backoff, request timeouts, and
  retry-delay parsing** on the Gemini provider (`ai/gemini.py`). A
  hard cap prevents multi-hour sleeps when the daily quota is
  exhausted.
- **AI call timing and per-stage timing** logged for every run.
- **Cooperative cancellation** with checkpoints between stages and
  inside search/fetch/comparison loops (`core/worker.py`).
- **Stale job recovery** on startup (`core/database.py →
  recover_stale_jobs`).
- **Migration system** with a `schema_migrations` table and a
  `MIGRATIONS` list in `core/migrations.py`.
- **Health check module** (`health.py`) covering database, search,
  fetch, and optionally the AI provider.
- **Evaluation framework** (`evaluation/`) with curated cases,
  per-case metrics, aggregate metrics, and report comparison.
- **pytest regression suite** covering URL normalization, request
  validation, confidence scoring, claim comparison, checker response
  handling, package building, cancellation helpers, and recovery
  logic.
- **CLI entry point** (`cli.py`) for testing without Telegram.
- **Documentation**: `README.md`, `docs/ARCHITECTURE.md`,
  `docs/ROADMAP.md`, `docs/providers.md`,
  `.github/CONTRIBUTING.md`, `.github/SECURITY.md`,
  `.github/CODE_OF_CONDUCT.md`, and five issue templates under
  `.github/ISSUE_TEMPLATE/`.

### Changed

- **Project layout reorganized into packages:**
  - `ai/` — Gemini + prompts
  - `core/` — orchestration, storage, confidence, package builder,
    providers, migrations
  - `stages/` — one module per pipeline stage
  - `ui/` — Telegram formatting
- **Writer prompt rewritten** to enforce per-sentence citations,
  renumber sources from 1, forbid leaked instructions, and align
  wording with confidence levels.
- **Writer output is post-processed** to strip leaked prompt
  artifacts (`stages/writer.py → clean_answer`).
- **Research package structure expanded** to include
  `search_strategy`, `source_claim_map`, per-claim `source_url`, and
  full confidence fields (`core/package.py`).
- **Fetch robustness.** The pipeline now fetches more sources than it
  plans to verify, so a few failed fetches don't cause the whole run
  to fail.
- **Concurrency limits are env-configurable** (`config.py`).
- **Model default** is `gemini-3.1-flash-lite` (the free-tier model
  with the highest quota).
- **`.github/` and `docs/` created**; community files moved into
  `.github/`.

### Fixed

- Duplicate sources being inserted when the same URL appeared in
  multiple search queries.
- `sqlite3.Row` objects failing on `.get()` calls in claim comparison
  and package building.
- Migrations previously only checked the `sources` table; migrations
  are now tracked in `schema_migrations` and applied without a
  table-specific pre-check.
- `bias_score` and `completeness_score` referenced by the verifier
  but missing from the database until migrations were added.
- `FutureWarning` from the deprecated `google.generativeai` package
  suppressed at import time.
- Noisy third-party loggers (`ddgs`, `primp`, `hickory_net`,
  `trafilatura`) silenced to `ERROR`.
- Channel posts (from Telegram channels the bot can see) no longer
  crash the handlers.
- `health.py` canary URL changed to a content-rich page so it isn't
  rejected by the extractor's minimum-length threshold.

### Known limitations

- Only Gemini (AI) and DuckDuckGo (search) are implemented.
- No primary-source discovery.
- No resumable jobs — a failed research job must be restarted.
- No evidence-graph UI.
- Confidence weights are heuristic, not tuned against a benchmark.
- No automated integration tests for the pipeline itself.

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