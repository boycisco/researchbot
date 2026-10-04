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

Early-stage. Works end-to-end but rough around the edges.

**What works today:**

- Full research pipeline from topic to cited answer
- Telegram interface with progress updates
- Terminal CLI (`cli.py`) for testing without Telegram
- Deterministic confidence scoring per claim
- Per-sentence fact-checking with an automatic revision loop
- Source deduplication by canonical URL
- Provider boundaries for AI, search, and fetching

**What does not work yet (or is weak):**

- Only one AI provider (Gemini) and one search provider
  (DuckDuckGo) are implemented
- No primary-source discovery
- No evidence graph / "why does it say this?" tracing UI
- Free tiers of both providers rate-limit aggressively
- DuckDuckGo sometimes returns no results or times out
- No web interface, no API, no research depth modes yet
- No automated test suite

If you self-host this, expect to babysit it.

## Pipeline

```text
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
Source verification (relevance, quality, bias, recency)
↓
Claim extraction (verbatim evidence stored)
↓
Claim comparison (supports, contradicts, qualifies, different context)
↓
Deterministic confidence scoring
↓
Research package
↓
Answer writing (AI, constrained to the package only)
↓
Per-sentence fact-checking
↓
Revision loop (max 2 attempts)
↓
Verified answer
```

Nothing reaches the user unless the fact checker says every factual
sentence is supported by the research package.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full
breakdown. In brief:

```text
researchbot/
├── bot.py, cli.py                  entry points (Telegram / terminal)
├── research.py                    application layer
├── request.py                     ResearchRequest dataclass
├── config.py, utils.py
│
├── core/                          orchestration + storage
│   ├── worker
│   ├── database
│   ├── models
│   ├── confidence
│   ├── package
│   └── providers
│
├── stages/                        pipeline stages
│   ├── search
│   ├── fetch
│   ├── verify
│   ├── claims
│   ├── compare
│   ├── writer
│   └── checker
│
├── ai/                           gemini, prompts
├── ui/                           format, history
│
├── docs/                         ARCHITECTURE.md
├── .github/                      CONTRIBUTING, CODE_OF_CONDUCT, SECURITY
└── ...
```

## Installation

Requires **Python 3.11+**.

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

## Configuration

Copy `.env.example` to `.env` and fill in two required keys:

```env
TELEGRAM_BOT_TOKEN=       # from @BotFather
GEMINI_API_KEY=           # from https://aistudio.google.com/apikey
```

Both are free to obtain.

Optional overrides (defaults shown):

```env
AI_PROVIDER=gemini
SEARCH_PROVIDER=duckduckgo
GEMINI_MODEL=gemini-1.5-flash
```

## Running

Terminal (recommended for testing):

```bash
python cli.py "What causes ocean warming?"
```

The CLI prints progress to the console and shows the final answer,
or the final failure reason if the pipeline failed.

Telegram:

```bash
python bot.py
```

Then message your bot:

- `/start` — welcome
- `/research <topic>` — start a research job
- `/research` — bot will ask for a topic in the next message
- `/history` — list your past research
- `/get <id>` — retrieve a completed answer
- `/cancel` — request cancellation of the active job

Progress is shown as a single edited message, not a stream of
updates.

## Limitations

Provider rate limits. Gemini's free tier is limited; the pipeline adds
retries and backoff but can still hit quota.

Search reliability. DuckDuckGo is free but flaky. Some queries return
zero results.

No tests. Verify changes manually via cli.py.

No persistence layer for retries. A failed research job stays failed;
restarting means starting a new job.

No primary-source prioritization yet. Secondary sources that reference
a study are treated similarly to the study itself.

Confidence scoring is a heuristic. It's deterministic and auditable,
but its weights have not been tuned against a benchmark.

## Contributing

See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

## Security

See [.github/SECURITY.md](.github/SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).