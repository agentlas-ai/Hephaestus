#!/bin/sh
set -eu

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
git -C "$repo_root" config --local core.hooksPath .githooks
chmod +x "$repo_root/.githooks/reference-transaction" "$repo_root/.githooks/pre-push"
echo "Installed Agentlas main-only Git guard in $repo_root"
