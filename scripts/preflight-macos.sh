#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Hephaestus preflight: this check is only needed on macOS."
  exit 0
fi

if ! xcode-select -p >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Hephaestus preflight failed: macOS Command Line Tools are not installed.

Claude and Codex plugin marketplace commands clone the GitHub repo with git.
On a fresh Mac, git is provided by Apple's Command Line Tools.

Run this once:

  xcode-select --install

Finish the Apple installer popup, open a new Terminal window, then run:

  git --version

After git works, rerun the Hephaestus plugin install command.
EOF
  exit 2
fi

if ! git --version >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Hephaestus preflight failed: git is not available.

Run:

  xcode-select --install

Then open a new Terminal window and verify:

  git --version
EOF
  exit 2
fi

echo "Hephaestus preflight passed: macOS Command Line Tools and git are available."
