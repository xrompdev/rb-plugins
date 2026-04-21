---
allowed-tools: Bash(git checkout -b:*), Bash(git add:*), Bash(git status:*), Bash(git push:*), Bash(git commit:*), Bash(git diff:*), Bash(git reset HEAD:*), Bash(gh pr create:*)
description: Commit by intention, push, and open a PR
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`

## Your task

Based on the above changes:

1. **Create a new branch** if needed:
   - If on `main` — always branch off
   - If on a **numbered-prefix branch** (e.g., `001-dashboard-analysis`, `056-report-statement-account`) — branch off with a proper name
   - Otherwise — stay on the current branch

   **Branch naming rules for numbered-prefix branches:**
   - Strip the leading number and separator (e.g., `001-`, `056-`)
   - Derive a conventional branch name using the dominant intention prefix and the remaining slug
   - Format: `<type>/<slug>` where type is `feat`, `fix`, `refactor`, `chore`, `docs`, or `test`
   - Examples:
     - On `001-dashboard-analysis` adding a feature → `feat/dashboard-analysis`
     - On `056-report-statement-account` fixing a bug → `fix/report-statement-account`
     - On `012-update-deps` doing chores → `chore/update-deps`

2. **Analyze all changes** and identify distinct intentions (bug fix, feature, refactor, config, tests, docs, etc.)
3. **Create separate commits for each intention group** — stage only the files belonging to each group, then commit with a clear message describing that group's purpose
4. **Push** the branch to origin
5. **Create a pull request** using `gh pr create` — the PR title should summarize the overall work, and the body should list the commits with a brief description of each intention group

### Intention grouping rules

- Read the diff carefully — which files changed together for the same reason?
- Separate concerns: a refactor mixed with a feature gets two commits
- If all changes share one intention, create one commit — don't force artificial splits
- Never create empty commits

### Commit message rules

- Match the style of recent commits shown above
- Be concise (subject line under 72 chars)
- Use conventional commit prefixes when the repo uses them (feat, fix, refactor, chore, docs, test, style)
- Do NOT include a Co-Authored-By line or any co-author attribution

### PR format

```
gh pr create --title "<concise title>" --body "$(cat <<'EOF'
## Summary
<1-2 sentence overview>

## Commits
- **<commit 1 subject>**: <brief description>
- **<commit 2 subject>**: <brief description>
- ...
EOF
)"
```

### Constraints

- You have the capability to call multiple tools in a single response. Use parallel calls where possible (e.g., staging files for the same commit), but commits must be sequential since each depends on the previous staging.
- Do not send any text or messages besides the tool calls.
