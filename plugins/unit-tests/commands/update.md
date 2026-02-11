---
name: update
description: Analyze changed files on the current branch vs main and update or create unit tests
argument-hint: "<path to service, e.g. apps/server/src/entities/job>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
---

# Update Unit Tests from Branch Changes

Analyze all source file changes on the current branch compared to `main` and update or create corresponding unit tests.

## Workflow

### Step 1: Identify Changed Files

Run `git diff main...HEAD --name-only --diff-filter=ACMR` to get all added, copied, modified, or renamed files on the current branch.

If the user provided an argument, filter the file list to only include files whose paths contain the argument string.

Filter the results to only source files that should have unit tests:
- Include: `*.ts` files in `src/` directories (services, resolvers, commands, libs)
- Exclude: `*.spec.ts`, `*.integration.spec.ts`, `*.e2e.spec.ts` (test files themselves)
- Exclude: `*.module.ts`, `*.dto.ts`, `*.input.ts`, `*.enum.ts`, `*.interface.ts`, `*.type.ts`, `*.model.ts`, `*.entity.ts` (type-only files)
- Exclude: `index.ts`, `main.ts`, `*.config.ts` (entry points and config)
- Exclude: files in `prisma/`, `migrations/`, `test/` directories

### Step 2: Analyze Each Changed File

For each changed source file:

1. Read the full source file to understand current implementation
2. Run `git diff main...HEAD -- <file>` to see what specifically changed
3. Check if a corresponding `*.spec.ts` test file exists (colocated in same directory)
4. If test file exists, read it to understand current test coverage
5. If no test file exists, note it for creation

### Step 3: Update or Create Tests

For each file, determine the action:

**If test file exists — update it:**
- Identify new functions, methods, or code paths introduced by the diff
- Identify modified functions whose behavior changed
- Add new `describe`/`it` blocks for new functionality
- Update existing tests if the function signature or behavior changed
- Preserve all existing passing tests — never remove tests unless the tested code was deleted

**If no test file exists — create it:**
- Follow the testing-conventions skill patterns (NestJS TestingModule, Prisma mocking, etc.)
- Include `should be defined` baseline test
- Add tests covering all public methods and key code paths
- Use `@faker-js/faker` for test data and `jest-mock-extended` for mocks

### Step 4: Run the Updated Tests

After all test files are updated/created, run the affected tests inside the Docker container.

First, determine which Nx projects are affected by finding the nearest `project.json` for each changed file. Then run tests per project:

```bash
docker exec -it sail-graphql-1 bash -c "yarn nx run <project>:test --testPathPattern='<pattern>' --maxWorkers=7"
```

Use `--testPathPattern` with a regex matching the specific test files that were modified or created.

### Step 5: Fix Failures

If any tests fail:
1. Read the error output carefully
2. Determine if the failure is in the test (wrong mock setup, wrong assertion) or the source code
3. Fix the test — do not modify source code unless there is a clear bug
4. Re-run only the failing tests to verify the fix
5. Repeat until all tests pass

### Step 6: Summary

After all tests pass, provide a summary:
- Number of test files updated
- Number of test files created
- Number of new test cases added
- Any files skipped and why
- Final test run results (pass/fail counts)

## Important Rules

- Never modify source code — only test files
- Never remove existing passing tests
- Always use the project's established mocking patterns (see testing-conventions skill)
- Always run tests inside `sail-graphql-1` Docker container
- Use `--maxWorkers=7` for unit tests to prevent memory issues
- Match the existing code style and import patterns of neighboring test files
