# OpenCode Adapter

OpenCode reads three Hephaestus surfaces — all installed by
`scripts/install-all-runtimes.sh`:

1. **Commands** — `commands/*.md` here are copied to
   `~/.config/opencode/commands/`, giving `/hep-build`,
   `/hep-network`, `/hep-local`, `/hep-cloud`, and `/hep-hub` in the OpenCode
   TUI.
2. **Skills** — OpenCode natively loads `~/.agents/skills/hephaestus-network/`
   and `~/.agents/skills/hephaestus-cloud/`, so routing also triggers
   implicitly via the `skill` tool.
3. **MCP** — for tool-level access (works with any model, including local
   Ollama models), register the stdio server in `opencode.json`:

```json
{
  "mcp": {
    "hephaestus-network": {
      "type": "local",
      "command": ["~/.agentlas/runtime/current/bin/hephaestus", "mcp", "serve"],
      "enabled": true
    }
  }
}
```

`hephaestus-network` is the only host-visible Workforce MCP. It exposes
`workforce.search_candidates`, `workforce.validate_selection`, and
`workforce.prepare_execution`; Core owns Cloud/Hub upstream calls. The
installer removes an old direct `agentlas` entry to prevent duplicate tools
from bypassing local federation and privacy governance.

The installed `/hep-*` OpenCode commands include the app-host auto-update
preflight. When OpenCode can run local shell commands, Hephaestus refreshes
`~/.agentlas/runtime/current` and existing adapters from inside the app before
resolving the runner.

Manual install without the one-touch script:

```bash
mkdir -p ~/.config/opencode/commands
cp opencode/commands/hep-build.md opencode/commands/hep-network.md opencode/commands/hep-local.md opencode/commands/hep-cloud.md opencode/commands/hep-hub.md ~/.config/opencode/commands/
mkdir -p ~/.agents/skills
cp -R skills/hephaestus-network ~/.agents/skills/
cp -R skills/hephaestus-cloud ~/.agents/skills/
```
