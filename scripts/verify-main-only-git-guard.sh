#!/bin/sh
set -eu

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
[ "$(git -C "$repo_root" config --local --get core.hooksPath || true)" = ".githooks" ]
[ "$(git -C "$repo_root" branch --show-current)" = "main" ]

extra_branches="$(git -C "$repo_root" for-each-ref --format='%(refname:short)' refs/heads | grep -v '^main$' || true)"
[ -z "$extra_branches" ] || {
  echo "Unexpected local branches:" >&2
  echo "$extra_branches" >&2
  exit 1
}

worktree_count="$(git -C "$repo_root" worktree list --porcelain | awk '$1 == "worktree" { count++ } END { print count + 0 }')"
[ "$worktree_count" -eq 1 ] || {
  echo "Expected one canonical worktree, found $worktree_count" >&2
  exit 1
}

echo "Agentlas main-only Git guard verified."
