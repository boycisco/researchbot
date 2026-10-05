# Architecture

This document describes how the codebase is organized, how a research
job flows through it, and which modules own which responsibilities.

It is written for contributors. If you want to know *how to run it*,
read the README instead.

## Principles

1. **One module, one job.** A file either orchestrates, stores data,
   calls an AI, calls a search provider, or formats output — never
   several of these at once.
2. **Interfaces do not research.** Telegram (and the CLI) receive
   input and display output. They never touch the pipeline directly.
3. **Providers are replaceable.** The pipeline depends on capability
   boundaries (`generate_text`, `search_web`, `fetch_source`), not on
   a specific vendor. See `docs/providers.md`.
4. **Deterministic where possible, AI where necessary.** Scoring,
   deduplication, filtering, and relationship classification are
   computed in Python. AI is used for language understanding.
5. **Nothing reaches the user without a passing fact-check.** The
   pipeline fails loudly rather than delivering an unverified answer.

## Layout

```text
researchbot/
├── bot.py Telegram entry point
├── cli.py Terminal entry point
├── health.py Health check module
├── research.py Application layer (creates a job, starts the worker)
├── request.py ResearchRequest dataclass + DEPTH_PROFILES
├── config.py Environment variables
├── utils.py Logging, URL normalization, small helpers
│
├── core/
│   ├── worker.py Pipeline orchestrator (runs in a thread)
│   ├── database.py SQLite CRUD
│   ├── models.py Schema (tables, indexes, foreign keys)
│   ├── migrations.py Named, ordered, idempotent migrations
│   ├── package.py Builds the research package JSON
│   ├── confidence.py Deterministic confidence scoring
│   └── providers.py Provider boundary (AI, search, fetch)
│
├── stages/
│   ├── search.py Query generation + web search
│   ├── fetch.py Fetch and extract page content
│   ├── verify.py Source verification (batch AI call)
│   ├── claims.py Claim extraction (batch AI call)
│   ├── compare.py Claim relationship classification
│   ├── writer.py Final answer generation + artifact cleanup
│   └── checker.py Per-sentence fact-checker
│
├── ai/
│   ├── gemini.py Gemini implementation (rate-limited, retried)
│   └── prompts.py All AI prompts, centralized
│
├── ui/
│   ├── format.py Telegram formatting helpers
│   └── history.py History formatting
│
├── evaluation/ Curated cases + metrics + reports
├── tests/ pytest regression suite
├── docs/ This folder
└── .github/ Community health files + issue templates
```

## Layers

```text
┌────────────────────────────────────┐
│ Interface │
│ bot.py / cli.py / health.py │
└──────────────┬─────────────────────┘
│ ResearchRequest
▼
┌────────────────────────────────────┐
│ Application │
│ research.py │
└──────────────┬─────────────────────┘
│ research_id + depth profile
▼
┌────────────────────────────────────┐
│ Orchestration │
│ core/worker.py │
└──────────────┬─────────────────────┘
│
┌──────────────┴─────────────────────┐
│ Pipeline stages │
│ stages/* │
└──────────────┬─────────────────────┘
│
┌──────────────┴─────────────────────┐
│ Providers │
│ core/providers.py │
│ → ai/gemini.py │
│ → stages/search.py │
│ → stages/fetch.py │
└──────────────┬─────────────────────┘
│
┌──────────────┴─────────────────────┐
│ Storage │
│ core/database.py + SQLite │
└────────────────────────────────────┘
```

## Pipeline

A research job passes through these stages, in order. Each stage
updates `research.current_stage`, logs its duration, and writes its
output to the database before the next stage runs.

| # | Stage | Module | AI call? | Cancellation checkpoint |
|---|-------|--------|----------|--------------------------|
| 1 | Analysis | `stages/search.py` (via `ai/prompts.py`) | Yes — JSON | After |
| 2 | Query generation | `stages/search.py` | Yes — JSON | — |
| 3 | Web search | `stages/search.py` | No | Per query |
| 4 | Fetching | `stages/fetch.py` | No | Per URL |
| 5 | Verification | `stages/verify.py` | Yes — batch JSON | Before |
| 6 | Claim extraction | `stages/claims.py` | Yes — batch JSON | Before |
| 7 | Claim comparison | `stages/compare.py` | Yes — batch or per-pair | Per pair |
| 8 | Confidence scoring | `core/confidence.py` | No | — |
| 9 | Package building | `core/package.py` | No | — |
| 10 | Writing | `stages/writer.py` | Yes — text | Before |
| 11 | Fact-checking | `stages/checker.py` | Yes — JSON | Before, per revision |
| 12 | Revision (0–N×) | `stages/writer.py` + `ai/prompts.py` | Yes — text | Per attempt |

The number of AI calls per run is controlled by depth (see
`DEPTH_PROFILES` in `request.py`) and by the `COMPARE_MODE` config
flag. `batch` mode collapses all claim-pair comparisons into one AI
call; `per_pair` fires one call per pair. `batch` is the default to
reduce rate-limit pressure.

If any stage fails, the worker marks the job as `failed` with the
stage name and the error. It does not silently continue.

If the fact-checker fails after the maximum number of revisions, the
job is marked `failed` with
`error='Fact check failed after max revisions'`. The user does not
receive an unverified answer.

## Cancellation

Cancellation is cooperative. The worker checks
`database.is_cancel_requested(research_id)` between stages and inside
the search, fetch, and comparison loops. When cancellation is
detected:

- `status = 'cancelled'`
- `current_stage = 'cancelled'`
- `completed_at` is set
- All partial data remains in the database

The helper `check_cancelled(stage_name)` inside `run_research`
centralizes this logic.

## Job recovery

Jobs left in an active state for longer than
`RECOVERY_MAX_AGE_MINUTES` are marked `failed` at startup with
`current_stage = 'recovered'` and `error = 'Abandoned (…)'`. See
`database.recover_stale_jobs()`.

This runs in both `bot.py` and `cli.py` entry points.

## Database

SQLite, one file (path from `config.DB_PATH`). Schema in
`core/models.py`.

Tables:

| Table | Purpose |
|-------|---------|
| `users` | One row per Telegram user |
| `research` | One row per research job |
| `queries` | Search queries generated for a job |
| `sources` | Every URL discovered or fetched |
| `claims` | Evidence-backed claims extracted from sources |
| `relationships` | Relationships between claims (supports, contradicts, etc.) |
| `packages` | The JSON package handed to the writer |
| `answers` | The final answer (verified, revised, or failed) |
| `user_states` | Pending Telegram conversation state |
| `schema_migrations` | Applied migrations (name + timestamp) |

Foreign keys and indexes are defined in the schema. Migrations are
additive, ordered, and idempotent. They live in `core/migrations.py`
as a `MIGRATIONS` list of `(name, body)` tuples. The runner records
each applied migration in `schema_migrations`; it never re-applies
one.

**Never write to the database from anywhere except
`core/database.py`.** If you need a new query, add a helper there.

### Adding a migration

1. Add a new entry to `MIGRATIONS` in `core/migrations.py` with the
   next sequential name (`012_…`, `013_…`, etc.).
2. Never edit an existing migration. Add a new one.
3. Never reorder migrations.
4. Migrations that aren't naturally idempotent (data migrations) only
   run once thanks to `schema_migrations`.

## Providers

`core/providers.py` is the only file that knows which concrete AI,
search, and fetch implementations exist. Everything else imports
from `core.providers`.

See `docs/providers.md` for how to add a new provider.

## Prompts

Every AI prompt lives in `ai/prompts.py`. Long prompt strings are
never embedded in `stages/*`. This makes prompts auditable in one
place and makes it possible to swap AI providers without rewriting
prompt logic.

## Confidence

`core/confidence.py` computes a deterministic score from:

- the AI's own claim-extraction confidence (0–100),
- the average `quality_score` of supporting sources,
- the independence ratio (distinct domains / total supporting),
- the average `recency_score` of supporting sources,
- a primary-source bonus,
- minus a penalty per true contradiction.

The score is clamped to 0–100 and mapped to `Low / Moderate / High /
Very High`. An explanation string is stored with every claim so the
writer can justify its wording.

## AI provider contract

`ai/gemini.py` implements the following contract for every AI call:

- **Timeout**: hard cap at `config.AI_REQUEST_TIMEOUT_S` (default
  30s), enforced with a `ThreadPoolExecutor` wrapper because the SDK
  does not honor `request_options={"timeout": …}` reliably.
- **Rate limiting**: rolling-window limiter at
  `config.MAX_AI_REQUESTS` per minute.
- **Retries**: up to 2 additional attempts, with exponential backoff
  capped at 60s per wait, and a hard cap of `MAX_RETRY_WAIT_S=120`
  for the `retry_delay` hint returned in rate-limit errors. If
  Google suggests waiting longer (daily quota exhausted), we fail
  fast with a clear message.
- **Error classification**: rate_limit, timeout, server_error,
  client_error, unknown. Only the first three are retried.
- **Timing**: every attempt logs `[ai] call ok attempt=N duration=Y.Ys`
  or a warning/error with the same information.

## Failure modes

| Failure | What happens |
|---------|--------------|
| AI provider error | Retry with backoff; if still failing, stage fails |
| AI call timeout | Abandon thread, retry; if still failing, stage fails |
| Search returns zero results | Stage fails; job marked `failed` |
| Every source fetch fails | Stage fails; job marked `failed` |
| No sources verified | Stage fails; job marked `failed` |
| No claims extracted | Stage fails; job marked `failed` |
| Writer produces nothing | Stage fails; job marked `failed` |
| Fact checker errors | Job marked `failed` with `verification_error` |
| Fact checker fails N× | Job marked `failed` with `fact_check_failed` |
| User cancels | Cooperative cancellation between checkpoints |
| Worker crashes mid-run | Job recovered as `failed` on next startup |

## Concurrency

Bounded by process-wide semaphores:

- `research_semaphore` — max simultaneous research jobs
- `fetch_semaphore` — max simultaneous page fetches
- `search_semaphore` (in `stages/search.py`) — max simultaneous
  search queries
- Rate limiter in `ai/gemini.py` — max AI calls per minute

Limits are defined in `config.py` and can be overridden via `.env`.

## Observability

Every stage logs its duration:

```text
[stage] research=42 stage=analysis duration=11.5s
[stage] research=42 stage=search duration=44.5s
```

Every AI call logs its duration and outcome:

```text
[ai] call ok attempt=1 duration=11.4s json=True
[ai] rate_limit (attempt 1, duration=0.3s); retrying in 33.0s
[ai] SDK call exceeded 30s; abandoning thread
```

Sensitive data (API keys, Telegram tokens) is redacted by a
`logging.Filter` in `utils.setup_logging()`.

## What this code deliberately does *not* do

- It does not trust any AI's summary.
- It does not use outside knowledge during writing or checking.
- It does not treat a blog the same as a government filing.
- It does not collapse contradictions into an average.
- It does not silently swallow exceptions.
- It does not deliver an answer that failed verification.
- It does not fall back to a secondary provider silently.

## Where to make common changes

| Task | File |
|------|------|
| Change how the AI writes the answer | `ai/prompts.py` → `writer_prompt` |
| Change what counts as a "true contradiction" | `ai/prompts.py` → `comparison_prompt` |
| Change the confidence formula | `core/confidence.py` → `WEIGHTS` |
| Change which sources get verified | `stages/verify.py` → `MIN_RELEVANCE`, `MIN_FINAL_SCORE` |
| Change depth behavior | `request.py` → `DEPTH_PROFILES` |
| Add a new AI provider | `core/providers.py` + new file under `ai/` |
| Add a new search provider | `core/providers.py` + new file under `stages/` |
| Add a new Telegram command | `bot.py` |
| Change how Telegram messages are formatted | `ui/format.py` |
| Add a database column | `core/models.py` + a new entry in `core/migrations.py` |
| Add a health check | `health.py` |
| Add an evaluation case | `evaluation/cases.py` |