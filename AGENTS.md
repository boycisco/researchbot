# AGENTS.md

Research assistant that runs as a Telegram bot and a terminal CLI.
It turns a topic into a cited answer by searching, fetching, verifying,
extracting claims, cross-checking, and fact-checking before delivery.

The AI is a component, not the authority. Nothing reaches the user
unless the fact-checker says every factual sentence is supported by
the research package.

## Commands

```bash
# Setup
python -m venv venv && venv\Scripts\activate    # Windows
pip install -r requirements.txt

# Tests (must pass before any commit)
python -m pytest tests/ -v

# Run
python cli.py "What causes ocean warming?" --depth quick
python bot.py                                    # Telegram

# Diagnostics
python -m health                                 # fast
python -m health --with-ai                       # uses AI quota
```

## Architecture

```text
bot.py, cli.py, health.py    entry points (thin — no pipeline logic)
research.py, request.py      application layer + ResearchRequest
core/                        worker, database, models, migrations,
                             confidence, package, providers
stages/                      search, fetch, verify, claims, compare,
                             writer, checker
ai/                          gemini, prompts
ui/                          format, history
```

Full detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Provider guide: [`docs/providers.md`](docs/providers.md).

## Hard rules

- `bot.py` stays thin. No SQL, no AI calls, no pipeline logic.
- Only `core/database.py` imports SQLite.
- Only `core/providers.py` imports concrete providers (`ai.gemini`,
  `stages.search`, `stages.fetch`).
- Only `ai/prompts.py` contains prompt strings.
- Never edit an existing migration. Add a new one in
  `core/migrations.py` with the next sequential name.
- `stages/writer.py` and `stages/checker.py` see only the research
  package. No outside knowledge.
- Failures are explicit. Never swallow exceptions or return `{}` on
  failure.
- Never fabricate sources, claims, evidence, or confidence scores.

## Where to look first

- Changing a pipeline stage → `.github/agents/pipeline-stage.agent.md`
- Adding an AI/search/fetch provider → `.github/agents/provider.agent.md`
- Changing prompts, checker, or confidence → `.github/agents/research-quality.agent.md`
- Documentation → `.github/agents/docs.agent.md`

## Gotchas

- The Gemini free tier is slow (5-15 RPM). Do not "fix" a slow test
  by removing timeouts or retries.
- `python cli.py` is the fastest way to test the full pipeline.
- Use `DB_PATH=researchbot-eval.db` for evaluation runs so you don't
  pollute the user's real history.