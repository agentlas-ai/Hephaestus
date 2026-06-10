#!/usr/bin/env bash
# C-1: keep runtime code adapters as exact mirrors of the canonical core.
#
# Code assets (ontology/, agentlas_cloud/, bin/hephaestus) must be
# byte-identical in every runtime adapter directory — adapters mirror the
# canonical core, they are never a second source. SKILL.md adapters are
# intentionally condensed per runtime and are NOT byte-checked here.
#
# Usage:
#   scripts/sync-adapters.sh           # render core into adapter mirrors
#   scripts/sync-adapters.sh --check   # fail on drift (CI / verify-package)
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

mode="${1:-sync}"

plugin_roots=(
  "claude/plugins/agentlas-core-engine-meta-agent"
  "codex/plugins/agentlas-core-engine-meta-agent"
)

code_dirs=(
  "ontology"
  "agentlas_cloud"
)

code_files=(
  "bin/hephaestus"
)

# Byte-mirrored skill copies at the repo root (.agents/skills); plugin skill
# files are condensed adapters and excluded on purpose.
skill_mirrors=(
  "skills/mode-classification/SKILL.md:.agents/skills/mode-classification/SKILL.md"
  "skills/clarify-question-loop/SKILL.md:.agents/skills/clarify-question-loop/SKILL.md"
  "skills/agentlas-auto-activation/SKILL.md:.agents/skills/agentlas-auto-activation/SKILL.md"
  "skills/skill-lifecycle-promotion/SKILL.md:.agents/skills/skill-lifecycle-promotion/SKILL.md"
)

drift=0

check_dir() {
  local src="$1" dest="$2"
  if ! diff -rq -x "__pycache__" -x ".DS_Store" "$src" "$dest" > /dev/null 2>&1; then
    echo "adapter drift: $dest != $src" >&2
    drift=1
  fi
}

check_file() {
  local src="$1" dest="$2"
  if ! diff -q "$src" "$dest" > /dev/null 2>&1; then
    echo "adapter drift: $dest != $src" >&2
    drift=1
  fi
}

sync_dir() {
  local src="$1" dest="$2"
  mkdir -p "$dest"
  rsync -a --delete --exclude "__pycache__" --exclude ".DS_Store" "$src/" "$dest/"
}

sync_file() {
  local src="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
}

for plugin in "${plugin_roots[@]}"; do
  for dir in "${code_dirs[@]}"; do
    if [[ "$mode" == "--check" ]]; then
      check_dir "$dir" "$plugin/$dir"
    else
      sync_dir "$dir" "$plugin/$dir"
    fi
  done
  for file in "${code_files[@]}"; do
    if [[ "$mode" == "--check" ]]; then
      check_file "$file" "$plugin/$file"
    else
      sync_file "$file" "$plugin/$file"
    fi
  done
done

for pair in "${skill_mirrors[@]}"; do
  src="${pair%%:*}"
  dest="${pair##*:}"
  if [[ "$mode" == "--check" ]]; then
    check_file "$src" "$dest"
  else
    sync_file "$src" "$dest"
  fi
done

if [[ "$mode" == "--check" ]]; then
  [[ "$drift" == "0" ]] || exit 1
  echo "sync-adapters: no drift."
else
  echo "sync-adapters: core rendered into adapter mirrors."
fi
