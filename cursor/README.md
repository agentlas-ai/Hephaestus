# Cursor Adapter

Since Cursor 2.5, plugins (`.cursor-plugin/plugin.json`) bundle commands,
skills, and rules. This adapter provides both the plugin layout and loose
files:

- `plugin/` — Cursor plugin: `/hephaestus-build`, `/hephaestus-network`, and
  `/hephaestus-cloud` commands + the `hephaestus-network` and
  `hephaestus-cloud` skills + the routing rule.
- `rules/hephaestus.mdc` — standalone rule for projects that copy rules
  directly into `.cursor/rules/`.

`scripts/install-all-runtimes.sh` installs the global surfaces:

- commands → `~/.cursor/commands/`
- skill → `~/.cursor/skills/hephaestus-network/` (and `~/.agents/skills/`,
  which Cursor also reads)

Manual install:

```bash
mkdir -p ~/.cursor/commands ~/.cursor/skills
cp cursor/plugin/commands/hephaestus-build.md cursor/plugin/commands/hephaestus-network.md cursor/plugin/commands/hephaestus-cloud.md ~/.cursor/commands/
cp -R skills/hephaestus-network ~/.cursor/skills/
cp -R skills/hephaestus-cloud ~/.cursor/skills/
```

The Cursor CLI (`agent`) reads the same rules, skills, AGENTS.md, and
`~/.cursor/mcp.json` — for MCP tool access see `docs/local-models.md`.
