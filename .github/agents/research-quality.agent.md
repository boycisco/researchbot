---
name: research-quality
description: Use when changing prompts, the fact-checker, confidence scoring, or claim-comparison logic. These changes affect whether answers can be trusted.
---

# Research-quality changes

You are working on the parts of the pipeline that determine whether
an answer is trustworthy. Treat every change here as high-risk.

## Scope

You may **read** anything. You may **write**:

- `ai/prompts.py`
- `stages/compare.py`
- `stages/checker.py`
- `stages/writer.py` (cleanup patterns only)
- `core/confidence.py`
- `core/package.py`
- `tests/`

Do not touch `core/worker.py` except to call a new function you added.

## The invariants you must not break

1. **The writer sees only the package.** No outside knowledge.
2. **The checker sees only the package.** No outside knowledge.
3. **Status is computed in Python, not trusted from the AI.** The
   model's `status: passed` summary is a hint; `problematic` is
   what decides.
4. **Confidence is deterministic.** Given the same inputs, it must
   produce the same score.
5. **Contradictions are preserved, not averaged.** Two conflicting
   claims remain separate and are linked with a relationship.
6. **"Contradicts" means same subject, timeframe, population, opposite
   conclusion.** Differences in population/method/timeframe are
   `different_context`, not `contradicts`.
7. **Explanations are stored with every score.** The user must be
   able to ask "why 78?" and get a sentence.

## Rules

1. Prompts live here, in `ai/prompts.py`. No exceptions.
2. Any prompt change must state its role, task, required output, and
   restrictions explicitly.
3. Any JSON prompt must specify the exact schema. Assume the model
   will deviate if not told.
4. Keep the prompts under a length that fits the context window.
   Trim before adding.
5. When the checker's logic changes, add a test in
   `tests/test_checker.py`. Same for `compare` and `confidence`.

## Verification

```bash
python -m pytest tests/ -v
python -m evaluation.run --case simple-factual
python -m evaluation.run --case conflicting-sources
python -m evaluation.report
```

Compare the newest report against the previous one with
`python -m evaluation.report --compare <old.json>`. Report the diff.