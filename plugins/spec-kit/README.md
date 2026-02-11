# spec-kit

Auto-installs and integrates GitHub [spec-kit](https://github.com/github/spec-kit) for spec-driven development workflows.

## How it works

A `SessionStart` hook checks if the `specify` CLI is installed. If not, it:

1. Installs [uv](https://docs.astral.sh/uv/) if not already available
2. Installs `specify-cli` from the spec-kit repository via `uv tool install`

## Components

| Type | Description |
|------|-------------|
| Hook (`SessionStart`) | Ensures spec-kit is installed at session start |
