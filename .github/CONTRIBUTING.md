# Contributing

Thanks for your interest. This project is early-stage, so expect some
rough edges — and expect your changes to be genuinely useful because
nothing here is over-engineered yet.

## Before you start

Read [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). It explains the
folder layout and the pipeline. Most "where do I put this?" questions
are answered there.

## Development setup

```bash
git clone <your-repo-url>
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

## Running things

Terminal — the fastest way to test:

```bash
python cli.py "What causes ocean warming?"
```

This runs the full pipeline and prints progress and the final answer
to the console. Use it for iterating.

Telegram:

```bash
python bot.py
```

Use this only when you're specifically testing the Telegram layer.

## Where to put your change

Use this table. If your change doesn't fit anywhere obvious, open an
issue first — the answer is often "add a new file, don't stuff it into
an existing one."

| If you're changing… | Edit this file |
|---|---|
| A prompt | `ai/prompts.py` |
| How Gemini is called | `ai/gemini.py` |
| Which provider is used | `core/providers.py` |
| Database schema | `core/models.py` + migration in `core/database.py` |
| A database query | `core/database.py` |
| Pipeline order or stage wiring | `core/worker.py` |
| A single pipeline stage | `stages/<stage>.py` |
| The confidence formula | `core/confidence.py` |
| The research package format | `core/package.py` |
| What the user sees on Telegram | `ui/format.py` or `bot.py` |
| The CLI | `cli.py` |
| Configuration defaults | `config.py` |
| The research request / depth profiles | `request.py` |

## Rules

These are not style preferences. Breaking them breaks the design.

- `bot.py` must stay thin. No research logic, no direct
  `providers.*` calls, no AI calls, no SQL.
- Only `core/database.py` talks to SQLite. No `sqlite3` imports
  outside that file.
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

## Testing

There is no automated test suite yet. Manual testing is the current
expectation:

```bash
python cli.py "<a real question>"
```

Watch the log lines. Every stage must complete.

Read the final answer. It must be coherent, cited, and not contain
leaked prompt artifacts (`CITATION FORMAT:`, `【…】`, markdown
headings from the model, etc.).

If the pipeline fails, check that the failure is explicit — status
`failed`, correct stage, non-empty error field in the research
table.

If you change a stage, run the pipeline at least twice. The AI is
non-deterministic; a change that works once may still fail on the
second run.

## Adding a database column

Add the column to the table definition in `core/models.py`.

Add a migration entry to the migrations list inside `init_db()`
in `core/database.py`:

```python
("column_name", "ALTER TABLE table_name ADD COLUMN column_name TYPE"),
```

Migrations are idempotent — you do not need to check whether the
column exists. Duplicate-column errors are caught and ignored.

Never edit an existing migration. Add a new one.

## Submitting changes

Keep pull requests small and focused.

- One change per PR. If you fix a bug and refactor two files, that's
  two PRs.
- Include a short description of what problem you're solving, not
  just what the diff does.
- If your change affects the pipeline, paste the output of a
  successful `cli.py` run in the PR.

## Reporting bugs

Open an issue. For research-quality bugs (wrong facts, missed
contradictions, sources not deduplicated), please include:

- The exact research question you used
- The terminal output
- The final answer, if produced
- The `research_id` from the log (so we can inspect the database)

## Code of conduct

See `CODE_OF_CONDUCT.md`. The short version:
don't be a jerk.