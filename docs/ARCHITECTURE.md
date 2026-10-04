# Architecture

## Current Modules

| File | Responsibility |
|------|----------------|
| `bot.py` | Telegram interface; handles commands and user messages |
| `worker.py` | Research pipeline orchestration; manages stages and error handling |
| `database.py` | SQLite database operations (CRUD) |
| `models.py` | Database schema (tables and indexes) |
| `gemini.py` | Gemini AI provider (text/JSON generation, rate limiting, retries) |
| `search.py` | Query generation and web search via DuckDuckGo |
| `fetch.py` | Fetch and extract main content from URLs |
| `verify.py` | Batch source verification using Gemini |
| `claims.py` | Batch claim extraction from verified sources |
| `compare.py` | Claim comparison using deterministic similarity + Gemini |
| `package.py` | Build the research package JSON |
| `writer.py` | Generate the final answer from the research package |
| `checker.py` | Fact-check the answer against the package |
| `prompts.py` | Centralized AI prompts |
| `format.py` | Format progress messages and split long Telegram messages |
| `history.py` | (Placeholder) History formatting |
| `utils.py` | Logging, rate limiter, URL utilities, junk filter |
| `config.py` | Environment variables and concurrency limits |

## Pipeline

1. Topic analysis (Gemini)
2. Query generation (Gemini)
3. Web search (DuckDuckGo)
4. Source fetching (trafilatura)
5. Source verification (batch Gemini)
6. Claim extraction (batch Gemini)
7. Claim comparison (deterministic candidate matching + Gemini)
8. Research package building (Python)
9. Answer writing (Gemini)
10. Fact checking (Gemini)
11. Revision loop (max 2 revisions)
12. Completion or failure

## Database

Tables:
- users
- research
- queries
- sources
- claims
- relationships
- packages
- answers
- user_states

Foreign keys enforce referential integrity. Indexes exist on key fields.

## External Providers

- **AI**: Google Gemini (free tier)
- **Search**: DuckDuckGo (via `duckduckgo_search` package, no API key)
- **Fetcher**: `requests` + `trafilatura`

## Telegram Interface

Commands:
- `/start`
- `/research [topic]`
- `/history`
- `/get <id>`
- `/cancel`

## Known Limitations

- Free AI tier has rate limits; we added retry logic but may still hit quota.
- DuckDuckGo sometimes times out or returns few results.
- No primary-source discovery yet.
- Confidence scoring is simple (average of source quality and claim confidence).
- No job recovery; failed jobs remain failed.
- No API or CLI.
- History shows only last 10 items.
- Single-user focus (though database supports multiple users).