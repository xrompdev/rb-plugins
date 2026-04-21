---
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git diff:*), Bash(git reset HEAD:*)
description: Create git commits grouped by intention
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

## Your task

Analyze the changes above and create **separate commits grouped by intention**. Each commit should contain only related changes that share a single purpose (e.g., a bug fix, a new feature, a refactor, a config change, test updates, documentation).

### Process

1. **Analyze all changes** — read the diff carefully and identify distinct intentions. Consider:
   - Which files changed together for the same reason?
   - Are there separable concerns (e.g., a refactor mixed with a feature addition)?
   - Do some changes represent cleanup vs. functional changes?

2. **Group changes by intention** — assign each changed file (or hunk within a file) to an intention group. If a single file contains changes serving multiple intentions, stage it with the most dominant one.

3. **Commit each group sequentially** — for each intention group:
   - `git add` only the files belonging to that group
   - `git commit` with a message that clearly describes that group's purpose
   - Move to the next group

### Commit message rules

- Match the style of recent commits shown above
- Be concise (subject line under 72 chars)
- Use conventional commit prefixes when the repo uses them (feat, fix, refactor, chore, docs, test, style)
- Do NOT include a Co-Authored-By line or any co-author attribution

### Examples of intention grouping

| Intention | Files |
|-----------|-------|
| feat: add user avatar upload | `src/avatar.ts`, `src/routes/upload.ts` |
| fix: correct date parsing in reports | `src/reports/parser.ts` |
| chore: update dependencies | `package.json`, `package-lock.json` |

### Constraints

- If all changes share a single intention, create one commit — don't force artificial splits.
- Never create empty commits.
- Do not send any text or messages besides the tool calls for staging and committing.
