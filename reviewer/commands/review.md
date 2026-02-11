---
name: review
description: Light review of current branch changes for anti-patterns using a git worktree
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Task
---

# Light Code Review — Anti-Pattern Detection

Review all changed files on the current branch vs `main` for common anti-patterns. Use a git worktree so the review runs against a clean checkout without affecting the working directory.

## Workflow

### Step 1: Set Up Worktree

Determine the current branch name:

```bash
git rev-parse --abbrev-ref HEAD
```

Create a temporary worktree for the review:

```bash
git worktree add /tmp/review-<branch-name> HEAD
```

If the worktree already exists, remove and recreate it:

```bash
git worktree remove /tmp/review-<branch-name> --force
git worktree add /tmp/review-<branch-name> HEAD
```

All file reads during the review MUST use the worktree path (`/tmp/review-<branch-name>/...`), not the main working directory.

### Step 2: Identify Changed Files

From the worktree directory, get all changed files on the branch:

```bash
git -C /tmp/review-<branch-name> diff main...HEAD --name-only --diff-filter=ACMR
```

Filter to reviewable source files:
- Include: `*.ts`, `*.tsx`, `*.js`, `*.jsx` files
- Exclude: `*.spec.ts`, `*.test.ts`, `*.e2e.spec.ts`, `*.integration.spec.ts`
- Exclude: `node_modules/`, `dist/`, `prisma/migrations/`

### Step 3: Review for Anti-Patterns

Delegate the review to the **typescript-architect** agent using the Task tool. Pass the agent:
- The list of changed files (full worktree paths)
- The git diff output: `git -C /tmp/review-<branch-name> diff main...HEAD`
- Instruction to scan for the anti-patterns listed below

#### Anti-Patterns to Detect

| Anti-Pattern | Detection |
|---|---|
| **Debug code** | `console.log`, `console.debug`, `console.warn`, `console.error` used for debugging (not logging utilities), `debugger` statements, `print` statements |
| **Empty catch blocks** | `catch` blocks with empty body or only a comment |
| **Marker comments** | `TODO`, `FIXME`, `HACK`, `XXX` comments in new/changed lines |
| **Magic numbers** | Numeric literals (other than 0, 1, -1) used directly in logic without a named constant |
| **Deep nesting** | Code nested more than 4 levels of indentation (if/for/while/switch) |
| **Long functions** | Functions or methods longer than 50 lines |
| **Duplicate code** | Repeated code blocks (3+ lines identical or near-identical) within or across changed files |
| **Dead code** | Unreachable code after return/throw, unused imports, unused variables, commented-out code blocks |

### Step 4: Clean Up Worktree

After the review completes, remove the worktree:

```bash
git worktree remove /tmp/review-<branch-name> --force
```

### Step 5: Report

Present a structured review report:

```
## Review Summary — <branch-name>

**Files reviewed:** X
**Issues found:** Y

### Issues by Category

#### Debug Code (N issues)
- `path/to/file.ts:42` — `console.log('debug value', x)`

#### Empty Catch Blocks (N issues)
- `path/to/file.ts:87` — empty catch block

...

### Clean Files
- `path/to/clean-file.ts` — no issues found
```

Use relative paths (not worktree paths) in the report so they map to the actual project files.

If no issues are found, report: "No anti-patterns detected. Branch looks clean."

## Important Rules

- Read files from the worktree, not the working directory
- Only review lines that are new or modified on the branch (check the diff)
- Do not flag existing code that was not changed on this branch
- Do not modify any files — this is a read-only review
- Always clean up the worktree when done, even if an error occurs
- Keep the review light — focus only on the listed anti-patterns, not style or architecture
