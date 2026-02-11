#!/bin/bash
set -euo pipefail

# Read hook input from stdin (PostToolUse provides JSON with tool_input)
input=$(cat)

# Extract file path from tool_input
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

# Skip if no file path
if [ -z "$file_path" ]; then
  exit 0
fi

# Check file extension - only process js, ts, json
case "$file_path" in
  *.ts|*.js|*.json) ;;
  *) exit 0 ;;
esac

# Determine project directory
project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Get relative path for scope check
relative_path="${file_path#"$project_dir"/}"

# Only process files in apps/ or libs/ (matching project's lint-staged scope)
case "$relative_path" in
  apps/*|libs/*) ;;
  *) exit 0 ;;
esac

# Verify the file exists (it should after Write/Edit)
if [ ! -f "$file_path" ]; then
  exit 0
fi

# Run biome check --write using the project's local installation
biome_bin="$project_dir/node_modules/.bin/biome"

if [ ! -x "$biome_bin" ]; then
  echo "Biome not found at $biome_bin" >&2
  exit 2
fi

if output=$("$biome_bin" check --write "$file_path" 2>&1); then
  # Biome succeeded (exit 0) - file is clean or was auto-fixed
  if echo "$output" | grep -q "Fixed"; then
    echo "Biome auto-fixed: $relative_path"
  fi
  exit 0
else
  # Biome returned non-zero - unfixable lint issues found
  echo "Biome found issues in $relative_path:" >&2
  echo "$output" >&2
  exit 2
fi
