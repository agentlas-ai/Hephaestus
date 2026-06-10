---
name: mode-classification
description: "Use before routing a /meta-agent request to choose single-agent-creator, team-builder, or agentlas-packager."
---

# Mode Classification

Choose `agentlas-packager` for existing agents, teams, repos, folders, ZIPs,
plugins, or adapters that need conversion, repair, cleanup, import, or release.

Choose `team-builder` for rosters, HQ, departments, multi-role workflows,
handoffs, policy, eval, QA, or parallel ownership.

Choose `single-agent-creator` for one installable worker.

Apply the `ontology-backed-agent` overlay (`ontology_backed: true`) on top of
the chosen mode when the request depends on knowledge search over user
documents or citation-attached generation (제안서/계약서/견적서, document
corpora). The overlay activates `bin/ontology`, injects contracts by rule from
`.agentlas/contract-injection-map.json`, and sets `loop_policy`
(none / self-correct / verified) from the risk tier — `verified` whenever the
agent performs external writes or sends.

If the choice would change files and the request is ambiguous, ask clarify
questions before generating.
