---
name: convention
description: Convention-aware PR review focused on critical issues using CLAUDE.md guidance
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Task
---

# Convention-Aware PR Review

Review the changes on the current branch using the repository's `CLAUDE.md` for style and convention guidance. Focus on identifying critical issues that must be addressed before merging. Be constructive and helpful.

## Workflow

### Step 1: Load Convention Context

Read the repository's `CLAUDE.md` to understand project-specific conventions:

```bash
find . -maxdepth 2 -name "CLAUDE.md" -not -path "*/node_modules/*" 2>/dev/null
```

Read all found `CLAUDE.md` files. These define the conventions and style expectations for this project.

### Step 2: Set Up Worktree

Determine the current branch name:

```bash
git rev-parse --abbrev-ref HEAD
```

Create a temporary worktree for the review:

```bash
git worktree add /tmp/review-convention-<branch-name> HEAD
```

If the worktree already exists, remove and recreate it:

```bash
git worktree remove /tmp/review-convention-<branch-name> --force
git worktree add /tmp/review-convention-<branch-name> HEAD
```

All file reads during the review MUST use the worktree path (`/tmp/review-convention-<branch-name>/...`), not the main working directory.

### Step 3: Identify Changed Files

Get the diff and changed files:

```bash
git -C /tmp/review-convention-<branch-name> diff main...HEAD --name-only --diff-filter=ACMR
```

Also capture the full diff for context:

```bash
git -C /tmp/review-convention-<branch-name> diff main...HEAD
```

Filter to reviewable source files:
- Include: `*.ts`, `*.tsx`, `*.js`, `*.jsx` files
- Exclude: `*.spec.ts`, `*.test.ts`, `*.e2e.spec.ts`, `*.integration.spec.ts`
- Exclude: `node_modules/`, `dist/`, `prisma/migrations/`

### Step 4: Review for Critical Issues

Read each changed file from the worktree and analyze the diff. Focus exclusively on:

- **Potential bugs, issues, or breaking changes** — Logic errors, null/undefined risks, race conditions, incorrect type handling, breaking API contracts
- **Performance** — N+1 queries, unbounded loops, missing pagination, expensive operations in hot paths, memory leaks
- **Security** — Injection vulnerabilities, exposed secrets, missing auth checks, unsafe deserialization, OWASP top 10
- **Correctness** — Wrong behavior vs intent, missing edge cases, incorrect error handling, data integrity issues

Use the `CLAUDE.md` conventions to inform what patterns are expected and which deviations represent real problems.

### Step 5: Clean Up Worktree

```bash
git worktree remove /tmp/review-convention-<branch-name> --force
```

### Step 6: Report

If **critical issues are found**, present them as concise bullet points:

```
## PR Review — <branch-name>

**Files reviewed:** X

### Critical Issues

- `path/to/file.ts:42` — **Bug**: Null check missing before accessing `user.email`, will throw if user is undefined
- `path/to/file.ts:87` — **Security**: User input passed directly to SQL query without parameterization
- `path/to/service.ts:15` — **Performance**: Database query inside a loop, will cause N+1 problem
```

If **no critical issues are found**:

```
## PR Review — <branch-name>

**Files reviewed:** X

Approved. No critical issues found related to bugs, performance, security, or correctness.
```

Use relative paths (not worktree paths) in the report.

## Important Rules

- Read the `CLAUDE.md` first — it defines what conventions matter for this project
- Only review lines that are new or modified on the branch (check the diff)
- Do not flag existing code that was not changed on this branch
- Do not modify any files — this is a read-only review
- Always clean up the worktree when done, even if an error occurs
- Keep feedback concise — only critical issues that must be addressed before merging
- Skip minor style or formatting suggestions unless they impact performance, security, or correctness
- Be constructive — explain why something is a problem and suggest a fix direction
