# unit-tests

Update and create unit tests based on current branch changes.

## Commands

| Command | Description |
|---------|-------------|
| `/update [path]` | Analyze changed files and update or create corresponding unit tests |

## How it works

1. Identifies changed source files on the current branch vs `main`
2. For each file, checks if a colocated `*.spec.ts` test exists
3. Updates existing tests or creates new ones following project conventions
4. Runs the tests inside the `sail-graphql-1` Docker container
5. Fixes any failures and re-runs until all tests pass

## Skill

The **testing-conventions** skill provides guidance on:

- NestJS `TestingModule` setup with deep Prisma mocking
- Event sourcing test patterns
- Domain command test patterns
- `@faker-js/faker` for test data, `jest-mock-extended` for mocks
- `@responsibid/testing` factories for domain entities

## Components

| Type | Description |
|------|-------------|
| Command (`/update`) | Orchestrates the test update workflow |
| Skill (`testing-conventions`) | Provides testing patterns and conventions guidance |

## Requirements

- Tests run inside the `sail-graphql-1` Docker container
- Uses `yarn nx run <project>:test` with `--maxWorkers=7`
