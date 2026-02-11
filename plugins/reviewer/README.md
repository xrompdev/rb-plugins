# reviewer

Light code review of current branch changes focused on anti-pattern detection.

## Commands

| Command | Description |
|---------|-------------|
| `/review` | Review changed files on the current branch vs `main` for anti-patterns |

## How it works

1. Creates a temporary git worktree for a clean checkout
2. Identifies changed `.ts`/`.tsx`/`.js`/`.jsx` files on the branch
3. Delegates scanning to the **typescript-architect** agent
4. Reports findings with file paths and line numbers
5. Cleans up the worktree when done

## Anti-patterns detected

| Pattern | Description |
|---------|-------------|
| Debug code | `console.log`, `debugger`, etc. |
| Empty catch blocks | Catch blocks with empty body or only a comment |
| Marker comments | `TODO`, `FIXME`, `HACK`, `XXX` in new/changed lines |
| Magic numbers | Numeric literals without named constants |
| Deep nesting | Code nested more than 4 levels |
| Long functions | Functions longer than 50 lines |
| Duplicate code | 3+ identical or near-identical lines |
| Dead code | Unreachable code, unused imports/variables, commented-out code |

## Components

| Type | Description |
|------|-------------|
| Command (`/review`) | Orchestrates the review workflow |
| Agent (`typescript-architect`) | Sonnet-powered agent that scans files for anti-patterns |
