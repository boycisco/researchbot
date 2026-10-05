# Security Policy

## Supported Versions

This project is pre-1.0. Only the latest commit on the default branch
is supported. There are no maintained release branches yet.

## Reporting a Vulnerability

**Do not open a public issue for security problems.**

If you've found a vulnerability, please email:

> **boyciscox@gmail.com**

Include as much as you can:

- A clear description of the issue
- Steps to reproduce
- The potential impact (data exposure, credential leak, remote code
  execution, denial of service, etc.)
- Any proof-of-concept code or terminal output
- The version/commit you tested against
- Whether you want public credit once it's fixed

You'll get an acknowledgement as soon as possible. If you don't hear
back within a few days, feel free to send a follow-up.

Please give us a reasonable amount of time to fix the issue before
disclosing it publicly. We're a small project and we'd rather ship a
fix than a press release.

## What counts as a security issue

- Credential or API key exposure
- Injection vulnerabilities (SQL, prompt injection that leads to
  unwanted external effects, etc.)
- Path traversal or arbitrary file read/write
- Denial of service that affects other users
- Cross-user data leakage (a user reading another user's research)
- Dependency vulnerabilities that are exploitable in the default
  configuration

## What does *not* count as a security issue

- The AI producing factually wrong answers (that's a research-quality
  issue — open a normal issue using the research quality template)
- DuckDuckGo rate limiting you
- Gemini rate limiting you
- Free-tier quota exhaustion
- The bot not being reachable when your computer is off

## Secrets in the repository

This project stores credentials in `.env`, which is in `.gitignore`.
If you have ever committed `.env` by accident:

1. Rotate the affected keys immediately (Telegram bot token via
   @BotFather, Gemini key via Google AI Studio).
2. Remove the file from Git history using `git filter-repo` or BFG
   Repo-Cleaner.
3. Force-push the cleaned history.

Deleting `.env` in a new commit is not enough — the file is still in
the history and can be recovered.

## Scope

This is a self-hosted research assistant. There is no hosted service,
no shared infrastructure, and no user account system beyond the
Telegram user ID. The main threats are:

- Leaking your own API keys
- A malicious web page causing the fetcher to do something unexpected
- Prompt injection from source content steering the writer

The last one is a known, accepted limitation. The pipeline constrains
the writer to the research package, but a sufficiently adversarial
source could still bias the model's output. Fact-checking against the
package reduces but does not eliminate this risk.