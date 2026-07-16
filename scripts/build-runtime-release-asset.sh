#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

tag="${1:-${HEPHAESTUS_REF:-}}"
out_dir="${2:-dist/runtime-release}"

if [[ ! "$tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
  echo "usage: scripts/build-runtime-release-asset.sh vX.Y.Z [output-dir]" >&2
  exit 2
fi

git rev-parse --verify "${tag}^{commit}" >/dev/null
manifest_version="$(git show "${tag}:manifest.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')"
if [[ "v$manifest_version" != "$tag" ]]; then
  echo "release tag $tag does not match manifest.json version $manifest_version at that tag" >&2
  exit 2
fi
mkdir -p "$out_dir"

asset="hephaestus-runtime-${tag}.tar.gz"
archive="$out_dir/$asset"
checksum="$archive.sha256"
tmp="$archive.tmp.$$"
manifest_tmp="$archive.manifest.tmp.$$"
trap 'rm -f "$tmp" "$manifest_tmp"' EXIT

# Public releases are install/runtime artifacts, not repository snapshots.
# Keep this as an explicit allowlist: tests, benchmarks, internal docs, local
# state, credentials, signing material, and maintainer-only verification
# scripts must never enter the downloadable archive.
runtime_paths=(
  "AGENTS.md"
  "CLAUDE.md"
  "GEMINI.md"
  "CHANGELOG.md"
  "LICENSE"
  "README.md"
  "README.hi.md"
  "README.ja.md"
  "README.ko.md"
  "README.zh-CN.md"
  "SECURITY.md"
  "agent.md"
  "manifest.json"
  ".agents"
  ".claude"
  ".claude-plugin"
  ".gemini"
  "agentlas_cloud"
  "agents"
  "antigravity"
  "assets/model2vec/potion-base-8M-int8"
  "bin"
  "career_graph"
  "claude"
  "codex"
  "cursor"
  "gemini"
  "grok"
  "hermes"
  "hooks"
  "modes"
  "ontology"
  "openclaw"
  "opencode"
  "schemas"
  "skills"
  "templates"
  "scripts/install-all-runtimes.sh"
  "scripts/install-memory-hooks.py"
)

runtime_excludes=(
  ":(exclude)claude/plugins/agentlas-core-engine-meta-agent/benchmarks/**"
  ":(exclude)codex/plugins/agentlas-core-engine-meta-agent/benchmarks/**"
  ":(exclude)gemini/extension/benchmarks/**"
)

git archive \
  --format=tar.gz \
  --prefix="Agentlas-OS-${tag#v}/" \
  --output="$tmp" \
  "$tag" \
  "${runtime_paths[@]}" \
  "${runtime_excludes[@]}"
mv "$tmp" "$archive"

tar -tzf "$archive" > "$manifest_tmp"
prefix="Agentlas-OS-${tag#v}/"

if grep -E '(^|/)(tests?|benchmarks?|docs|credentials|signing)(/|$)|(^|/)\.env($|\.)|(^|/)([^/]+\.(pem|key|p12|pfx|crt|cer)|id_(rsa|dsa|ecdsa|ed25519))$|(^|/)(test_[^/]*\.py|[^/]*_test\.py)$' "$manifest_tmp" >/dev/null; then
  echo "release archive contains a forbidden internal/test/secret path" >&2
  grep -E '(^|/)(tests?|benchmarks?|docs|credentials|signing)(/|$)|(^|/)\.env($|\.)|(^|/)([^/]+\.(pem|key|p12|pfx|crt|cer)|id_(rsa|dsa|ecdsa|ed25519))$|(^|/)(test_[^/]*\.py|[^/]*_test\.py)$' "$manifest_tmp" >&2
  exit 2
fi

required_runtime_paths=(
  "manifest.json"
  "bin/hephaestus"
  "agentlas_cloud/mcp_stdio.py"
  "agentlas_cloud/workforce/contracts.py"
  "schemas/workforce-work-order.schema.json"
  "schemas/workforce-selection.schema.json"
  "assets/model2vec/potion-base-8M-int8/manifest.json"
  "scripts/install-all-runtimes.sh"
)
for required in "${required_runtime_paths[@]}"; do
  if ! grep -Fx "${prefix}${required}" "$manifest_tmp" >/dev/null; then
    echo "release archive is missing required runtime path: $required" >&2
    exit 2
  fi
done

if command -v shasum >/dev/null 2>&1; then
  digest="$(shasum -a 256 "$archive" | awk '{print $1}')"
elif command -v sha256sum >/dev/null 2>&1; then
  digest="$(sha256sum "$archive" | awk '{print $1}')"
else
  digest="$(openssl dgst -sha256 "$archive" | awk '{print $NF}')"
fi

printf '%s  %s\n' "$digest" "$asset" > "$checksum"
tar -tzf "$archive" >/dev/null
printf '%s\n' "$archive" "$checksum"
