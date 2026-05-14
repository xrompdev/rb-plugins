---
name: fix-checks
description: Diagnose and fix failing CI checks on a GitHub pull request. Use when the user says "fix PR", "fix checks", "CI is failing", "PR checks are red", or provides a PR number with failing checks.
version: 0.1.0
---

# Fix Failing PR Checks

Systematically diagnose and fix all failing checks on a GitHub pull request.

## Input

The PR number is passed as the skill argument (e.g. `123`).

## Workflow

### Phase 1: Gather Failure Context

1. **Fetch PR details and failing checks:**

```bash
gh pr view <PR_NUMBER> --json number,title,headRefName,baseRefName,statusCheckRollup
```

2. **List all check runs and their statuses:**

```bash
gh pr checks <PR_NUMBER>
```

3. **Identify which checks failed.** For each failing check, note the check name and status.

4. **Checkout the PR branch locally** (if not already on it):

```bash
gh pr checkout <PR_NUMBER>
```

### Phase 2: Diagnose Each Failure

For each failing check, diagnose the root cause using the appropriate strategy:

#### GitHub Actions CI Failures

Fetch the failed job logs:

```bash
gh run view <RUN_ID> --log-failed
```

To get the run ID from the PR checks output, use:

```bash
gh pr checks <PR_NUMBER> --json name,state,link | jq -r '.[] | select(.state == "FAILURE" or .state == "ERROR")'
```

If that doesn't give run IDs, extract them from the check links or list runs on the branch:

```bash
gh run list --branch <BRANCH_NAME> --limit 5 --json databaseId,status,conclusion,name
```

Then view the failed run:

```bash
gh run view <RUN_ID> --log-failed 2>/dev/null | tail -200
```

If the log is too long, narrow to the specific failed job:

```bash
gh run view <RUN_ID> --json jobs --jq '.jobs[] | select(.conclusion == "failure") | .name'
```

```bash
gh run view <RUN_ID> --log-failed --job <JOB_ID> 2>/dev/null | tail -150
```

#### Lint / Type Check Failures

Run the check locally to reproduce:

```bash
# For Node.js projects — check package.json for exact commands
npm run lint 2>&1 | head -100
npm run typecheck 2>&1 | head -100
npx tsc --noEmit 2>&1 | head -100

# For projects using Docker (like ResponsiBid)
docker exec -it <container> bash -c "yarn lint" 2>&1 | head -100
docker exec -it <container> bash -c "yarn tsc --noEmit" 2>&1 | head -100
```

#### Test Failures

Run the failing tests locally:

```bash
# Identify which test files failed from the CI logs, then run them
npm test -- --testPathPattern='<pattern>' 2>&1 | tail -100

# For Docker-based projects
docker exec -it <container> bash -c "yarn nx run <project>:test --testPathPattern='<pattern>' --maxWorkers=7" 2>&1 | tail -100
```

#### Build Failures

```bash
npm run build 2>&1 | tail -100
```

### Phase 3: Fix the Issues

For each diagnosed failure:

1. **Read the relevant source files** that contain errors
2. **Analyze the error messages** to understand what needs to change
3. **Apply fixes** using Edit/MultiEdit
4. **Verify locally** by re-running the failing check command

Fix categories and common solutions:

| Failure Type | Common Fixes |
|---|---|
| **Lint errors** | Auto-fix with `npx eslint --fix <file>`, or manually fix remaining issues |
| **Type errors** | Fix type mismatches, add missing imports, update interfaces |
| **Test failures** | Update assertions, fix mocks, adjust test data to match code changes |
| **Build errors** | Fix import paths, resolve missing dependencies, fix syntax errors |
| **CI config errors** | Fix workflow YAML, update action versions, fix environment variables |

### Phase 4: Verify All Fixes

After applying all fixes, verify each previously failing check passes locally:

```bash
# Run all checks that were failing
npm run lint 2>&1 | tail -20
npx tsc --noEmit 2>&1 | tail -20
npm test 2>&1 | tail -20
npm run build 2>&1 | tail -20
```

Adjust commands based on what the project actually uses (check `package.json` scripts).

### Phase 5: Report

Present a structured summary:

```
## PR #<NUMBER> — Fix Summary

**Branch:** <branch-name>
**Checks fixed:** X / Y

### Fixes Applied

#### <Check Name 1> — FIXED
- **Root cause:** <what was wrong>
- **Fix:** <what was changed>
- **Files modified:** `path/to/file.ts`

#### <Check Name 2> — FIXED
- **Root cause:** <what was wrong>
- **Fix:** <what was changed>
- **Files modified:** `path/to/file.ts`

### Verification
- Lint: PASS
- TypeCheck: PASS
- Tests: PASS
- Build: PASS

### Remaining (if any)
- <Check Name> — Could not fix: <reason>
```

## Important Rules

- Always fetch and read the actual CI failure logs before attempting fixes
- Reproduce failures locally when possible before fixing
- Never skip or disable tests to make checks pass
- Never add `// @ts-ignore`, `// eslint-disable`, or similar suppressions unless the suppression is the correct fix
- Fix root causes, not symptoms
- Verify fixes locally before reporting success
- If a check cannot be fixed (e.g., flaky infrastructure issue), say so clearly
- Do not commit or push changes — leave that to the user
