#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

fail() {
  echo "verify-package: $*" >&2
  exit 1
}

required_files=(
  "AGENTS.md"
  "README.md"
  "ARCHITECTURE.md"
  "agent.md"
  "agents/10-single-agent-builder/agent.md"
  "agents/20-multi-agent-team-builder/agent.md"
  "agents/30-agentlas-packager/agent.md"
  "modes/single-agent-creator.md"
  "modes/team-builder.md"
  "modes/agentlas-packager.md"
  ".agents/agentlas-core-engine-meta-agent/agent.md"
  ".agents/plugins/marketplace.json"
  ".agentlas/mode-map.json"
  ".agentlas/agent-card.json"
  ".agentlas/company-blueprint.json"
  ".agentlas/sitemap.json"
  ".agentlas/memory-map.json"
  ".agentlas/memory-tickets.jsonl"
  ".agentlas/vault-references.json"
  "CLAUDE.md"
  "GEMINI.md"
  ".claude-plugin/marketplace.json"
  ".claude/commands/meta-agent.md"
  ".claude/agents/agentlas-core-engine-meta-agent.md"
  ".claude/skills/agentlas-core-engine-meta-agent/SKILL.md"
  "claude/.claude-plugin/marketplace.json"
  "claude/plugins/agentlas-core-engine-meta-agent/.claude-plugin/plugin.json"
  "claude/plugins/agentlas-core-engine-meta-agent/SKILL.md"
  ".gemini/GEMINI.md"
  "codex/plugins/agentlas-core-engine-meta-agent/.codex-plugin/plugin.json"
  "codex/.agents/plugins/marketplace.json"
  "codex/plugins/agentlas-core-engine-meta-agent/skills/agentlas-core-engine-meta-agent/SKILL.md"
)

for path in "${required_files[@]}"; do
  [[ -e "$path" ]] || fail "missing required file: $path"
done

agent_count="$(find agents -mindepth 2 -maxdepth 2 -name agent.md | wc -l | tr -d ' ')"
[[ "$agent_count" == "3" ]] || fail "expected exactly 3 visible core agents, found $agent_count"

python3 - <<'PY'
import json
from pathlib import Path

for path in Path(".").rglob("*.json"):
    if ".git" in path.parts:
        continue
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"invalid json: {path}: {exc}")

for path in list(Path("skills").glob("*/SKILL.md")) + list(Path(".agents/skills").glob("*/SKILL.md")):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise SystemExit(f"skill missing YAML frontmatter: {path}")
    if "\n---" not in text[4:]:
        raise SystemExit(f"skill frontmatter not closed: {path}")

mode_map = json.loads(Path(".agentlas/mode-map.json").read_text(encoding="utf-8"))
for mode, payload in mode_map["modes"].items():
    for key in ("contract", "agent", "primarySkill"):
        value = payload[key]
        if not Path(value).exists():
            raise SystemExit(f"mode {mode} references missing {key}: {value}")
PY

if grep -R -nE '00-meta|05-mode|10-agent-repo|20-runtime|30-memory|40-pm|50-policy|60-eval|70-sitemap|80-llm' \
  AGENTS.md README.md ARCHITECTURE.md agent.md agents modes docs skills .agents .agentlas templates >/tmp/agentlas-meta-old-ids.txt 2>/dev/null; then
  cat /tmp/agentlas-meta-old-ids.txt >&2
  fail "old concept-agent ids still present"
fi

echo "Package verification passed."
