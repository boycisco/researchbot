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
   a specific vendor.
4. **Deterministic where possible, AI where necessary.** Scoring,
   deduplication, filtering, and relationship classification are
   computed in Python. AI is used for language understanding.
5. **Nothing reaches the user without a passing fact-check.** The
   pipeline fails loudly rather than delivering an unverified answer.

## Layout

```text
researchbot/
├── bot.py                              Telegram entry point
├── cli.py                              Terminal entry point
├── research.py                         Application layer (creates a job, starts the worker)
├── request.py                          ResearchRequest dataclass + depth profiles
├── config.py                           Environment variables
├── utils.py                            Logging, URL normalization, small helpers
│
├── core/
│   ├── worker.py                       Pipeline orchestrator (runs in a thread)
│   ├── database.py                     SQLite CRUD
│   ├── models.py                       Schema (tables, indexes, foreign keys)
│   ├── package.py                      Builds the research package JSON
│   ├── confidence.py                  Deterministic confidence scoring
│   └── providers.py                    Provider boundary (AI, search, fetch)
│
├── stages/
│   ├── search.py                       Query generation + web search
│   ├── fetch.py                        Fetch and extract page content
│   ├── verify.py                       Source verification (batch AI call)
│   ├── claims.py                       Claim extraction (batch AI call)
│   ├── compare.py                      Claim relationship classification
│   ├── writer.py                       Final answer generation + artifact cleanup
│   └── checker.py                      Per-sentence fact-checker
│
├── ai/
│   ├── gemini.py                       Gemini implementation (rate-limited, retried)
│   └── prompts.py                      All AI prompts, centralized
│
├── ui/
│   ├── format.py                       Telegram formatting helpers
│   └── history.py                      History formatting
│
├── docs/                               This folder
└── .github/                            Community health files
```

## Layers

```text
┌────────────────────────────────────┐
│ Interface                          │
│ bot.py / cli.py                   │
└──────────────┬─────────────────────┘
               │
               │ ResearchRequest
               ▼
┌────────────────────────────────────┐
│ Application                       │
│ research.py                       │
└──────────────┬─────────────────────┘
               │
               │ research_id
               ▼
┌────────────────────────────────────┐
│ Orchestration                     │
│ core/worker.py                    │
└──────────────┬─────────────────────┘
               │
┌──────────────┴─────────────────────┐
│ Pipeline stages                   │
│ stages/*                          │
└──────────────┬─────────────────────┘
               │
┌──────────────┴─────────────────────┐
│ Providers                         │
│ core/providers.py                 │
│ → ai/gemini.py                    │
│ → stages/search.py                │
│ → stages/fetch.py                 │
└──────────────┬─────────────────────┘
               │
┌──────────────┴─────────────────────┐
│ Storage                           │
│ core/database.py + SQLite         │
└────────────────────────────────────┘
```

## Pipeline

A research job passes through these stages, in order. Each stage
updates `research.current_stage` and writes its output to the
database before the next stage runs.

| # | Stage | Module | AI call? |
|---|-------|--------|----------|
| 1 | Analysis | `stages/search.py` (via `ai/prompts.py`) | Yes — JSON |
| 2 | Query generation | `stages/search.py` | Yes — JSON |
| 3 | Web search | `stages/search.py` | No |
| 4 | Fetching | `stages/fetch.py` | No |
| 5 | Verification | `stages/verify.py` | Yes — batch JSON |
| 6 | Claim extraction | `stages/claims.py` | Yes — batch JSON |
| 7 | Claim comparison | `stages/compare.py` | Yes — per pair |
| 8 | Confidence scoring | `core/confidence.py` | No |
| 9 | Package building | `core/package.py` | No |
| 10 | Writing | `stages/writer.py` | Yes — text |
| 11 | Fact-checking | `stages/checker.py` | Yes — JSON |
| 12 | Revision (0–2×) | `stages/writer.py` + `ai/prompts.py` | Yes — text |

If any stage fails, the worker marks the job as `failed` with the
stage name and the error. It does not silently continue.

If the fact-checker fails after the maximum number of revisions, the
job is marked `failed` with `error='Fact check failed after max revisions'`.
The user does not receive an unverified answer.

## Database

SQLite, one file (`researchbot.db`). Schema in `core/models.py`.

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

Foreign keys and indexes are defined in the schema. Migrations are
additive and applied automatically at startup — the `init_db()`
function in `core/database.py` lists them; each is idempotent
(duplicate-column errors are caught and ignored).

**Never write to the database from anywhere except `core/database.py`.**
If you need a new query, add a helper there.

## Providers

`core/providers.py` is the only file that knows which concrete AI,
search, and fetch implementations exist. Everything else imports from
`core.providers`.

To add a new provider:

1. Implement the capability (e.g. `openai.generate_json`).
2. Register it in `core/providers.py` behind a config flag.
3. Do not touch `stages/*` or `core/worker.py`.

See `docs/providers.md` for details.

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

## Failure modes

| Failure | What happens |
|---------|--------------|
| AI provider error | Retry with backoff; if still failing, stage fails |
| Search returns zero results | Stage fails; job marked `failed` |
| Every source fetch fails | Stage fails; job marked `failed` |
| No sources verified | Stage fails; job marked `failed` |
| No claims extracted | Stage fails; job marked `failed` |
| Writer produces nothing | Stage fails; job marked `failed` |
| Fact checker errors | Job marked `failed` with `verification_error` |
| Fact checker fails 2× | Job marked `failed` with `fact_check_failed` |
| User cancels | Cooperative cancellation between stages |

## Concurrency

Bounded by process-wide semaphores:

- `research_semaphore` — max simultaneous research jobs
- `fetch_semaphore` — max simultaneous page fetches
- `search_semaphore` (in `stages/search.py`) — max simultaneous
  search queries
- Rate limiter in `ai/gemini.py` — max AI calls per minute

Limits are defined in `config.py` and can be overridden via `.env`.

## What this code deliberately does *not* do

- It does not trust any AI's summary.
- It does not use outside knowledge during writing or checking.
- It does not treat a blog the same as a government filing.
- It does not collapse contradictions into an average.
- It does not silently swallow exceptions.
- It does not deliver an answer that failed verification.

## Where to make common changes

| Task | File |
|------|------|
| Change how the AI writes the answer | `ai/prompts.py` → `writer_prompt` |
| Change what counts as a "true contradiction" | `ai/prompts.py` → `comparison_prompt` |
| Change the confidence formula | `core/confidence.py` → `WEIGHTS` |
| Change which sources get verified | `stages/verify.py` → `MIN_RELEVANCE`, `MIN_FINAL_SCORE` |
| Add a new AI provider | `core/providers.py` + new file under `ai/` |
| Add a new search provider | `core/providers.py` + new file under `stages/` |
| Add a new Telegram command | `bot.py` |
| Change how Telegram messages are formatted | `ui/format.py` |
| Add a database column | `core/models.py` + a new entry in `init_db()` migrations |
| Tune per-depth behavior | `request.py` → `DEPTH_PROFILES` |