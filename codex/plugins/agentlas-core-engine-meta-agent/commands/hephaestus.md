# /hephaestus

Raw arguments:
`$ARGUMENTS`

## Route

If the first argument is `ontology`, open the project-local ontology GUI:

1. Find the first executable path from the shell snippet below.
2. Run:

```bash
RUNNER=""
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
for candidate in \
  "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/bin/hephaestus}" \
  "${CODEX_PLUGIN_ROOT:+$CODEX_PLUGIN_ROOT/bin/hephaestus}" \
  "${PLUGIN_ROOT:+$PLUGIN_ROOT/bin/hephaestus}" \
  "./bin/hephaestus" \
  "./claude/plugins/agentlas-core-engine-meta-agent/bin/hephaestus" \
  "./codex/plugins/agentlas-core-engine-meta-agent/bin/hephaestus"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    RUNNER="$candidate"
    break
  fi
done
if [ -z "$RUNNER" ]; then
  for cache in "$HOME/.claude/plugins/cache/agentlas-core-engine/hephaestus" \
               "${CODEX_HOME:-$HOME/.codex}/plugins/cache/agentlas-core-engine/hephaestus"; do
    newest="$(ls -d "$cache"/*/bin/hephaestus 2>/dev/null | sort -V | tail -1)"
    if [ -n "$newest" ] && [ -x "$newest" ]; then RUNNER="$newest"; break; fi
  done
fi
if [ -z "$RUNNER" ]; then
  echo "Hephaestus runtime not found. Install the plugin or run the standalone installer first." >&2
  exit 1
fi
"$RUNNER" ontology --gui .
```

3. Report the returned `gui_url`, `db_path`, `inbox_path`, and verification status.

If the first argument is not `ontology`, route to the Agentlas Core Engine
Meta-Agent team:

1. Read `AGENTS.md`.
2. Read `.agentlas/mode-map.json`.
3. Classify the request as single-agent builder, multi-agent team builder, or
   packager.
4. Load only the matching public skills.
5. Generate or repair `.agentlas/global-commands.json` and matching runtime
   command files or aliases.
6. Return `status`, `evidence`, `output`, `global_commands`, and `blockers`.
   The `global_commands` section must tell the user the exact Claude Code,
   Codex, Gemini CLI, generic AGENTS.md, and terminal commands for the generated
   agent.

## Examples

```text
/hephaestus ontology
/hephaestus create a self-evolving research agent
/hephaestus package this existing Codex workspace into Agentlas architecture
```
