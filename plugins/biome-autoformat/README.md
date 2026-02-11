# biome-autoformat

Automatically runs [Biome](https://biomejs.dev/) `check --write` after file modifications to enforce project lint and formatting standards.

## How it works

A `PostToolUse` hook triggers after every `Write` or `Edit` tool call. It runs `biome check --write` on the modified file if:

- The file has a `.ts`, `.js`, or `.json` extension
- The file is inside the `apps/` or `libs/` directories
- Biome is installed locally in the project (`node_modules/.bin/biome`)

If Biome auto-fixes issues, the hook reports what was fixed. If unfixable lint issues remain, the hook reports them as errors.

## Components

| Type | Description |
|------|-------------|
| Hook (`PostToolUse`) | Runs biome check on modified `.ts`, `.js`, `.json` files |

## Requirements

- Biome must be installed in the project (`node_modules/.bin/biome`)
- `jq` must be available on the system
