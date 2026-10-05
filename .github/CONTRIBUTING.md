# Contributing

Thanks for your interest. This project is early-stage, so expect some
rough edges — and expect your changes to be genuinely useful because
nothing here is over-engineered yet.

## Before you start

Read [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). It explains the
folder layout, the pipeline, and the design rules. Most "where do I
put this?" questions are answered there.

## Development setup

```bash
git clone https://github.com/boycisco/researchbot.git
cd researchbot

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add:

```env
TELEGRAM_BOT_TOKEN=   # only needed if you want to test the bot
GEMINI_API_KEY=       # needed for any research run
```

Both are free.

## Running things

Terminal — the fastest way to test:

```bash
python cli.py "What causes ocean warming?"
python cli.py "Is intermittent fasting effective?" --depth quick
```

This runs the full pipeline and prints progress and the final answer
to the console. Use it for iterating.

Telegram:

```bash
python bot.py
```

Use this only when you're specifically testing the Telegram layer.

### Health check

```bash
python -m health              # fast: database, search, fetch
python -m health --with-ai    # also tests the AI provider (uses quota)
```

Run this before opening a PR that touches providers.

### Evaluation harness

```bash
python -m evaluation.run --list
python -m evaluation.run --case simple-factual
python -m evaluation.report
```

The evaluation harness runs real questions end-to-end. Use a separate
database to avoid polluting your research history:

```powershell
# Windows
$env:DB_PATH="researchbot-eval.db"; python -m evaluation.run --case simple-factual
```

```bash
# macOS / Linux
DB_PATH=researchbot-eval.db python -m evaluation.run --case simple-factual
```

## Where to put your change

Use this table. If your change doesn't fit anywhere obvious, open an
issue first — the answer is often "add a new file, don't stuff it into
an existing one."

| If you're changing… | Edit this file |
|---|---|
| A prompt | `ai/prompts.py` |
| How the AI provider is called | `ai/gemini.py` |
| Which provider is used | `core/providers.py` |
| Database schema | `core/models.py` + a new migration in `core/migrations.py` |
| A database query | `core/database.py` |
| Pipeline order or stage wiring | `core/worker.py` |
| A single pipeline stage | `stages/<stage>.py` |
| The confidence formula | `core/confidence.py` |
| The research package format | `core/package.py` |
| What the user sees on Telegram | `ui/format.py` or `bot.py` |
| The CLI | `cli.py` |
| The health check | `health.py` |
| Configuration defaults | `config.py` |
| The research request / depth profiles | `request.py` |
| An evaluation case | `evaluation/cases.py` |
| Evaluation metrics | `evaluation/metrics.py` |

## Rules

These are not style preferences. Breaking them breaks the design.

- `bot.py` must stay thin. No research logic, no direct
  `providers.*` calls, no AI calls, no SQL.
- Only `core/database.py` talks to SQLite. No `sqlite3` imports
  outside that file (and `core/migrations.py`, which receives a
  connection).
- Only `core/providers.py` knows about concrete providers. No
  `import gemini` or `import search` anywhere else.
- Only `ai/prompts.py` contains prompt text. No multi-line
  prompt strings inside `stages/*` or `core/*`.
- Failures are explicit. Do not catch-and-ignore. Do not return
  `{}` when a call fails. Return an error the caller can act on.
- Do not fabricate fallbacks. If there's no data, say so.
- Do not use outside knowledge in `stages/writer.py` or
  `stages/checker.py`. They see only the research package.
- Every factual statement in the final answer must be traceable
  to a claim in the package.
- Never edit an existing migration. Add a new one.

## Testing

There are two layers of tests.

### Automated (fast, deterministic)

```bash
python -m pytest tests/ -v
```

These tests cover URL normalization, request validation, confidence
scoring, claim comparison, the fact-checker's response handling,
package building, cancellation helpers, and stale-job recovery. They
must all pass before you submit a PR.

### Manual (slow, non-deterministic)

The evaluation harness runs the pipeline end-to-end against real
search and real Gemini. It is not part of the PR check; run it when
you have changed a pipeline stage and want to see behavior on real
questions.

```bash
python -m evaluation.run --case simple-factual
python -m evaluation.report
```

If you change a stage, run the pipeline at least twice. The AI is
non-deterministic; a change that works once may still fail on the
second run.

## Adding a database migration

Add the column to the table definition in `core/models.py`.

Add a new entry to `MIGRATIONS` in `core/migrations.py`:

```python
("012_my_new_migration", _m012_my_new_migration),
```

Migrations are applied in list order and recorded in the
`schema_migrations` table. Each one runs at most once.

If your migration isn't naturally idempotent (e.g. a data
migration), the `schema_migrations` record makes it safe — it will
only run once.

Never edit an existing migration. Add a new one.

Never reorder migrations.

## Submitting changes

Keep pull requests small and focused.

- One change per PR. If you fix a bug and refactor two files, that's
  two PRs.
- Include a short description of what problem you're solving, not
  just what the diff does.
- If your change affects the pipeline, paste the output of a
  successful `cli.py` run in the PR.
- Run `python -m pytest tests/ -v` before opening the PR.

## Reporting bugs

Use the issue templates under `.github/ISSUE_TEMPLATE/`. There are
separate templates for:

- Bugs
- Feature requests
- Provider requests
- Research-quality issues (wrong answers, missed contradictions, etc.)

For research-quality bugs, please include:

- The exact research question
- The research depth (quick / standard / deep / exhaustive)
- The research ID (from the log)
- The final answer, if produced
- What you expected instead

The research ID lets us inspect the database directly.

## Code of conduct

See `CODE_OF_CONDUCT.md`. The short version: don't be a jerk.