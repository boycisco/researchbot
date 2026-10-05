---
name: docs
description: Use when editing README.md, CHANGELOG.md, docs/, .github/*.md, or AGENTS.md itself.
---

# Documentation changes

You are editing documentation. This is lower-risk than code, but
incorrect docs are worse than no docs.

## Scope

You may **write**:

- `README.md`
- `CHANGELOG.md`
- `AGENTS.md`, `CLAUDE.md`
- `docs/*.md`
- `.github/*.md`
- `.github/ISSUE_TEMPLATE/*.md`
- `.github/agents/*.md`

You may **read** anything (and should read the code you're documenting).

## Rules

1. **Do not describe behavior that does not exist.** Read the code
   first. If the code and the doc disagree, fix the doc or open an
   issue — do not guess.
2. **Do not duplicate the README in AGENTS.md.** AGENTS.md is for
   agents; README is for humans. Each has a distinct audience.
3. **Keep AGENTS.md under 60 lines.** Long AGENTS.md files measurably
   reduce agent performance. Split detail into
   `.github/agents/*.agent.md`.
4. **Relative links only.** Do not hardcode `github.com/...` URLs
   except in `ISSUE_TEMPLATE/config.yml`, where they're required.
5. **CHANGELOG entries go under `[Unreleased]`.** Do not invent version
   numbers.
6. **Never include real API keys, tokens, or personal information.**
   Placeholders only.

## Verification

```powershell
# All markdown links resolve
Get-ChildItem -Recurse -Filter "*.md" |
  Where-Object { $_.FullName -notmatch '\\venv\\' -and $_.FullName -notmatch '\\.pytest_cache\\' } |
  Select-String -Pattern '\]\(([^)]+)\)'

# No stray placeholders
Get-ChildItem -Recurse -Include "*.md","*.yml" |
  Select-String -Pattern "YOUR-USERNAME|your-repo-url|<your"
```

The first command lists every markdown link. The second must return
nothing.