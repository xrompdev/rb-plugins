# fix-pr

Diagnose and fix failing CI checks on a GitHub pull request.

## Usage

```
/fix-pr:fix-pr 123
```

Accepts a PR number, fetches failing check logs from GitHub, diagnoses each failure, applies fixes, and verifies locally.

## What it handles

- GitHub Actions CI pipeline failures
- Lint errors (ESLint, Biome, etc.)
- TypeScript type-check errors
- Unit/integration test failures
- Build failures

## Components

- **Command** `fix-pr` — entry point accepting a PR number
- **Skill** `fix-checks` — the diagnostic and fix workflow
