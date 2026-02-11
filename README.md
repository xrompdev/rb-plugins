# rb-plugins

Claude Code plugin marketplace for the ResponsiBid team.

## Installation

Requires [Claude Code](https://claude.ai/code) v1.0.33 or later.

```bash
# Add the marketplace (once)
/plugin marketplace add xrompdev/rb-plugins

# Install a plugin
/plugin install db-query@rb-plugins
```

To use a plugin directly from the CLI:

```bash
claude --plugin rb-plugins/db-query
```

To update plugins after new releases:

```bash
/plugin marketplace update rb-plugins
```

## Plugins

| Plugin | Description |
|--------|-------------|
| [biome-autoformat](plugins/biome-autoformat) | Auto-runs Biome lint and format on file modifications |
| [commit-commands](plugins/commit-commands) | Git commit, push, and PR commands without co-author attribution |
| [db-query](plugins/db-query) | Read-only MySQL and PostgreSQL query tool |
| [reviewer](plugins/reviewer) | Anti-pattern detection on current branch changes |
| [spec-kit](plugins/spec-kit) | Auto-installs GitHub spec-kit for spec-driven development |
| [unit-tests](plugins/unit-tests) | Update and create unit tests from branch changes |

## Plugin details

### biome-autoformat

Automatically runs `biome check --write` after every `Write`/`Edit` on `.ts`, `.js`, `.json` files in `apps/` or `libs/`.

### commit-commands

| Command | Description |
|---------|-------------|
| `/commit` | Stage and commit with an AI-generated message |
| `/commit-push-pr` | Commit, push, and open a PR in one step |
| `/clean_gone` | Remove local branches deleted from the remote |

### db-query

| Command | Description |
|---------|-------------|
| `/db-query:query <mysql\|postgres> <SQL>` | Run a read-only SQL query |
| `/db-query:schema <mysql\|postgres> [table]` | Inspect table schema and indexes |
| `/db-query:tables [mysql\|postgres\|all]` | List all tables with row counts |

Also activates automatically when asking about database data.

### reviewer

| Command | Description |
|---------|-------------|
| `/review` | Review changed files for anti-patterns (debug code, empty catches, TODOs, magic numbers, deep nesting, long functions, duplicate/dead code) |

### spec-kit

Installs the `specify` CLI at session start if not already available.

### unit-tests

| Command | Description |
|---------|-------------|
| `/update [path]` | Analyze branch changes and update or create unit tests |

Includes a **testing-conventions** skill with NestJS/Prisma mocking patterns.
