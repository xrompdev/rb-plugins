---
allowed-tools: Bash(git checkout -b:*), Bash(git add:*), Bash(git status:*), Bash(git push:*), Bash(git commit:*), Bash(git diff:*), Bash(git reset HEAD:*), Bash(git worktree list:*), Bash(cp -r:*), Bash(gh issue list:*), Bash(gh pr create:*), Write
description: Commit by intention, push, and open a PR with diagrams, sample input/output and scenarios
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`
- Recent commits: !`git log --oneline -10`
- PR template: !`cat .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null || echo "(none)"`

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
4. **Push** the branch with an explicit target: `git push -u origin <branch>:<branch>`
5. **Create a pull request**: write the body (see PR body) to a file, then `gh pr create --title "<concise title>" --body-file <file>`

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

### Git hooks in a worktree

Hooks run on every commit and push. When a hook fails with `cannot open .husky/_/husky.sh` inside a git worktree, copy `.husky/_` from the main checkout (the first path in `git worktree list`) into this worktree and retry, so the hooks run for real.

### PR body

When the PR template above exists, keep every one of its headings and fill each one; fold the sections below into the matching headings. With no template, use Summary, Evidence and Merge Danger as headings.

1. **Issue link** — `Part of #N` when the branch, the commits or an open issue (`gh issue list --search "<keywords>"`) matches the work; leave the line out when nothing fits.
2. **Summary** — one to three sentences: the problem, then what the change does about it.
3. **Diagrams** — one to three Mermaid diagrams of what changed: a before/after flow, a `sequenceDiagram` of where the new code runs, the decision logic. In Mermaid, `;` ends a statement, so write commas inside node and message text.
4. **Changes** — bullets grouped by component. With several commits, list each commit subject with one line on its intention.
5. **Sample input → expected output** — real values taken from a test or a run, saying which; tables for records, JSON for stored payloads. Label any value you made up as illustrative.
6. **Scenarios** — a table of `Scenario | Before | After`: the main case, the edge cases (empty, duplicate, concurrent, old or legacy data) and the paths that must stay the same.
7. **Evidence** — before and after: the test that failed and now passes, the command output, the counts of tests that actually ran.
8. **Merge Danger** — Door: two-way or one-way, and why. Blast Radius: one word. Then the release order, whether undoing the release is safe, and how someone would notice a problem.

Scale the body to the change: a one-line fix carries a summary, evidence and merge danger; diagrams, samples and scenarios earn their place when behaviour or data flow changes.

The body is public: it describes the change and its proof, with no mention of AI, Claude or how it was written, and no generated-by footer.

### Constraints

- You have the capability to call multiple tools in a single response. Use parallel calls where possible (e.g., staging files for the same commit), but commits must be sequential since each depends on the previous staging.
- Do not send any text or messages besides the tool calls.
