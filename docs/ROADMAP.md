# Roadmap

This is where the project is heading, grouped by how committed we are to
each item. Nothing here is a promise with a date attached.

## Now

Things being actively worked on or recently shipped.

- **Provider reliability.** Gemini's free tier is slow and rate-limited.
  We've added timeouts, retries, retry-delay parsing, and request
  batching. Ongoing: reduce the number of AI calls per run.
- **Research quality.** More accurate source verification, better
  contradiction detection, and a transparent confidence model.
- **Tests and evaluation.** A pytest suite covering the deterministic
  parts of the pipeline, and an evaluation harness that runs real
  questions end-to-end and reports metrics.
- **Documentation.** README, architecture, contributing, security,
  provider guides, and issue templates.

## Next

Things we intend to do but that require design decisions.

- **Primary-source discovery.** When a secondary source references a
  study, policy, or dataset, attempt to locate the primary source.
- **Evidence graph.** A queryable representation of
  `Question → Claim → Evidence → Source` so that a report can answer
  "why does it say this?" and trace the answer back through the chain.
- **Additional providers.** OpenAI, Anthropic, and a second search
  provider, so the pipeline is not dependent on Gemini + DuckDuckGo.
- **Resumable jobs.** Allow a failed research job to resume from the
  last completed stage instead of starting over.
- **Web UI.** A small interface (Flask or FastAPI) that exposes the
  same research engine without going through Telegram.

## Later

Ideas we like but that would be premature to build.

- **Research monitoring.** Save a topic and have the system
  periodically re-research it, notifying when findings change.
- **Team features.** Shared research, per-workspace permissions,
  team usage limits.
- **Hosted service.** A managed version of the engine for users who
  don't want to self-host.
- **Public benchmark.** A set of representative research questions
  measured against each release, with results published.

## Experimental

Exploratory directions that may or may not pan out.

- **Fallback AI providers.** Automatic switching to a different
  provider when the primary is slow or rate-limited.
- **Local models.** Running smaller models via Ollama for the cheaper
  extraction and classification stages, reserving cloud AI for the
  writing and fact-checking stages.
- **Citation-linked UI.** Interactive source cards in the web UI that
  show the exact evidence behind each claim.

## Not doing

Things we've decided against, with reasons.

- **Fine-tuning a model.** The pipeline's job is not to make the model
  smarter; it's to constrain what the model can say.
- **Skipping the fact checker.** Every answer must be verified against
  the research package before delivery. No exceptions.
- **Storing user content beyond what's needed for research history.**
  If you delete your research, it goes.
- **Marketing-style metrics like "95% accurate".** Any accuracy claim
  must be backed by a published benchmark that anyone can reproduce.