# Agentlas Cloud Runtime Contract

Hephaestus now emits and repairs `agentlas.json` before an agent package is
allowed into Agentlas Cloud call flows.

## V1 Scope

- Generate or repair `agentlas.json`.
- Run local risk screening before private sync or public publish.
- Compile a runtime bundle instead of sending the whole ZIP to an LLM.
- Gate `agentlas.read_agent_file` through `allowRead` and `denyRead`.
- Keep private sync and public clean-copy behavior separate.
- Attach a workspace-scoped personalization overlay only after authentication.
  The overlay may include promoted memory summaries, promoted playbook cards,
  plugin locks, and retrieval receipt ids; it must not include raw prompts,
  transcripts, secrets, credential values, or private local files.

## CLI

```bash
bin/hephaestus wizard ./some-agent --name instagram-operator
bin/hephaestus security scan ./some-agent --strict
bin/hephaestus runtime bundle ./some-agent
bin/hephaestus runtime read-agent-file ./some-agent AGENTS.md
bin/hephaestus field-test
```

## Lazy File Read

`runtime bundle` sends the manifest, bounded file index, package hash, and risk
summary first. Full file contents are fetched only through
`runtime read-agent-file`, and only when `agentlas.json` allows the requested
path.

The security scan is risk screening, not a safety guarantee. It reports file
paths, risk types, and redaction status without printing secret values.

## Workspace Personalization

Agentlas Web treats a called Cloud/Hub agent as:

```text
effective_agent = immutable_base_bundle + workspace_personal_overlay
```

The durable identity is `agentBindingId = workspaceId + sourceScope + baseAgentId`.
`packageHash` is stored as compatibility metadata, not as the binding id, so a
workspace can keep one personal agent identity while filtering hints by package
version.

The runtime bundle may include:

- `personalization.binding`: binding id, base agent id, source scope, slug, and
  current package hash.
- `personalization.memoryItems`: promoted summaries only.
- `personalization.playbookCards`: promoted recipes only.
- `personalization.pluginLocks`: plugin slug/version/permission snapshots.
- `personalization.retrievalReceiptId`: audit id for what was included.

Candidate writes use separate MCP tools:

- `agentlas.record_agent_memory`
- `agentlas.record_agent_playbook`
- `agentlas.propose_agent_evolution`

These tools save candidate records for curator or explicit user promotion. They
do not mutate the public Hub package and do not self-apply rule or skill
changes.

## Non-Goals

- Cloud server-side model execution.
- User key or OAuth token storage.
- Vault snapshot upload.
- Web-based agent editing.
- Enterprise policy implementation.
