# ResearchBot

A personal research assistant that runs as a Telegram bot (and a
terminal CLI). You give it a topic; it searches the web, fetches
sources, verifies them, extracts evidence-backed claims, cross-checks
them, writes a cited answer, and fact-checks the answer before
delivering it.

It is not a search engine, not an LLM chatbot, and not a news
aggregator. It is a pipeline that tries to be honest about what the
evidence actually says.

## Status

Early-stage. Works end-to-end. Rough around the edges.

**What works today:**

- Full research pipeline from topic to cited answer
- Telegram interface with progress updates via a single edited message
- Terminal CLI (`cli.py`) for testing without Telegram
- Research depth modes: `quick`, `standard`, `deep`, `exhaustive`
- Deterministic, explainable confidence scoring per claim
- Per-sentence fact-checking with automatic revision (up to N attempts)
- Source deduplication by canonical URL
- Cooperative cancellation with checkpoints between stages
- Startup recovery for stale jobs
- Health check (`python -m health`) covering database, search, fetch, and AI
- Evaluation harness that runs real questions and reports metrics
- 51 pytest regression tests covering the deterministic core
- Provider boundaries for AI, search, and fetching

**What does not work yet (or is weak):**

- Only Gemini (AI) and DuckDuckGo (search) are implemented
- No primary-source discovery
- No evidence-graph "why does it say this?" tracing UI
- Free-tier AI is slow and rate-limited; expect long pauses
- DuckDuckGo sometimes returns no results or times out
- No web interface, no public API
- No resumable jobs — a failed research job must be restarted

If you self-host this, expect to babysit it.

## Pipeline
Topic
↓
Analysis (what is the question actually asking?)
↓
Query planning
↓
Web search
↓
Source fetching
↓
Source verification (relevance, quality, evidence, recency, bias, completeness)
↓
Claim extraction (verbatim evidence stored)
↓
Claim comparison (supports / contradicts / qualifies / different_context)
↓
Deterministic confidence scoring
↓
Research package
↓
Answer writing (AI, constrained to the package only)
↓
Per-sentence fact-checking
↓
Revision loop (bounded)
↓
Verified answer

text

Nothing reaches the user unless the fact-checker says every factual
sentence is supported by the research package.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full
breakdown. In brief:

```text
researchbot/
├── bot.py, cli.py entry points (Telegram / terminal)
├── health.py health check
├── research.py application layer
├── request.py ResearchRequest + depth profiles
├── config.py, utils.py
│
├── core/ orchestration + storage
│   ├── worker, database, models, migrations,
│   ├── confidence, package, providers
│   └── ...
│
├── stages/ pipeline stages
│   ├── search, fetch, verify, claims, compare, writer, checker
│   └── ...
│
├── ai/ gemini, prompts
├── ui/ format, history
│
├── evaluation/ curated cases + metrics
├── tests/ pytest suite
├── docs/ ARCHITECTURE, ROADMAP, providers
└── .github/ CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, ISSUE_TEMPLATE
```

## Installation

Requires **Python 3.11+**.

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

### Configuration

Copy `.env.example` to `.env` and fill in two required keys:

```env
TELEGRAM_BOT_TOKEN=       # from @BotFather
GEMINI_API_KEY=           # from https://aistudio.google.com/apikey
```

Both are free to obtain.

Optional overrides (defaults shown):

```env
# Providers
AI_PROVIDER=gemini
SEARCH_PROVIDER=duckduckgo
GEMINI_MODEL=gemini-3.1-flash-lite

# Concurrency / rate limits
MAX_RESEARCH_JOBS=3
MAX_SOURCE_FETCHES=5
MAX_SEARCHES=5
MAX_AI_REQUESTS=12          # AI calls per minute (free tier allows 15)
AI_REQUEST_TIMEOUT_S=30     # per AI call

# Comparison strategy
COMPARE_MODE=batch          # "batch" (fewer AI calls) or "per_pair"

# Job recovery
RECOVERY_MAX_AGE_MINUTES=30

# Storage
DB_PATH=researchbot.db
```

### Running

Terminal — recommended for testing:

```bash
python cli.py "What causes ocean warming?"
python cli.py "Is intermittent fasting effective?" --depth quick
python cli.py "Does remote work increase productivity?" --depth deep
```

Telegram:

```bash
python bot.py
```

Then message your bot:

- `/start` — welcome
- `/research <topic>` — start a research job
- `/research --quick <topic> / --deep / --exhaustive` — depth modes
- `/research (no topic)` — bot will ask for one in the next message
- `/history` — list your past research
- `/get <id>` — retrieve a completed answer
- `/cancel` — request cancellation of the active job

Progress is shown as a single edited message, not a stream of
updates.

### Health check

```bash
python -m health              # database, search, fetch (fast)
python -m health --with-ai    # also tests the AI provider (uses quota)
```

### Regression tests

```bash
python -m pytest tests/ -v
```

### Evaluation harness

```bash
python -m evaluation.run --list                    # list cases
python -m evaluation.run --case simple-factual     # run one
python -m evaluation.report                        # show newest metrics
python -m evaluation.report --compare <report>     # compare two reports
```

Use a separate database for evaluation runs to avoid polluting your
real history:

```powershell
$env:DB_PATH="researchbot-eval.db"
python -m evaluation.run --case simple-factual
```

## Limitations

- AI free tier is slow. Gemini's free tier is rate-limited to a few
  requests per minute and can take 30+ seconds per call. The pipeline
  adds retries and timeouts, but a research run still takes minutes.
- Search reliability. DuckDuckGo is free but flaky.
- No resumable jobs. A failed research job stays failed.
- No primary-source prioritization. Secondary sources are treated
  similarly to the primaries they reference.
- Confidence scoring is a heuristic. Deterministic and auditable,
  but not yet tuned against a benchmark.
- No automated integration tests. The pytest suite covers
  deterministic modules; the pipeline itself is tested by hand and by
  the evaluation harness.

## Contributing

See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [.github/SECURITY.md](.github/SECURITY.md).

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT. See [LICENSE](LICENSE).