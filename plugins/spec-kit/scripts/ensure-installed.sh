#!/usr/bin/env bash
set -euo pipefail

# Check if specify CLI is already installed
if command -v specify &>/dev/null; then
  exit 0
fi

# Check if uv is available, install if not
if ! command -v uv &>/dev/null; then
  echo "Installing uv package manager..." >&2
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1

  # Source the env so uv is available in this session
  if [ -f "$HOME/.local/bin/env" ]; then
    source "$HOME/.local/bin/env"
  elif [ -d "$HOME/.local/bin" ]; then
    export PATH="$HOME/.local/bin:$PATH"
  fi

  if ! command -v uv &>/dev/null; then
    echo "Failed to install uv. Please install manually: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 2
  fi
fi

# Install spec-kit via uv
echo "Installing spec-kit (specify CLI)..." >&2
uv tool install specify-cli --from "git+https://github.com/github/spec-kit.git" 2>&1

if command -v specify &>/dev/null; then
  echo "spec-kit installed successfully." >&2
else
  echo "spec-kit installation completed but 'specify' not found in PATH." >&2
  echo "You may need to add ~/.local/bin to your PATH." >&2
  exit 2
fi
