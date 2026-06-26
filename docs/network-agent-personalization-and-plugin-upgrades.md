# Network Agent Personalization And Plugin Upgrades

Status: design proposal for the `/hep-network` Cloud > Bookmark > Hub routing model.

## Problem

Network agents are currently borrowed as runtime bundles, but the useful unit is larger than the bundle itself:

- base skills and instructions;
- tool and plugin dependencies;
- hard rules and caller-specific operating rules;
- playbook experience from prior runs;
- workspace memory and preferences;
- self-evolution proposals gated by evidence.

Without the last four layers, a borrowed Hub agent behaves like a generic package. It can run, but it cannot steadily adapt to Mason's workspace, preferred constraints, or prior failures.

A second failure mode is plugin drift. A Hub agent may request plugins that are installed locally but stale, missing tools, or incompatible with the current Hub manifest. Today that often appears as a call failure instead of a recoverable update workflow.

## Routing Contract

`/hep-network` should search in this order:

1. Agent Cloud: the signed-in user's own saved Cloud packages.
2. Bookmarks: Hub agents or teams the signed-in user saved for frequent reuse.
3. Hub: public Agentlas Hub marketplace candidates.

`/hep-cloud` remains Cloud-only. It must not fall through to bookmarks or public Hub.

Cloud single-agent calls are priced as private reuse infrastructure: 1 credit per call. Public Hub single-agent calls remain public rental calls. Team calls remain team-priced.

## Personalization Overlay

Do not mutate a public Hub package for one user's preferences. Treat each selected agent as:

```text
effective_agent = immutable_base_bundle + workspace_personal_overlay
```

The overlay is account/workspace scoped and never uploaded back to public Hub unless the user explicitly publishes a derived agent.

Recommended identity:

```text
agent_instance_id =
  workspaceId + sourceScope(cloud|bookmark|hub) + slug + packageHash
```

Recommended stores:

- `agent_personalization_profiles`: custom rules, output preferences, allowed memory scopes.
- `agent_playbook_events`: compact run lessons, failure recoveries, successful recipes.
- `agent_memory_tickets`: proposed durable memory updates emitted after runs.
- `agent_rule_overrides`: workspace-specific soft rules and opt-out flags.
- `agent_plugin_locks`: resolved plugin slugs, versions, checksums, and permission snapshots.

Merge precedence:

1. Safety hard rules from Agentlas/Hephaestus.
2. Base bundle hard rules and denied paths.
3. Workspace policy and credential boundaries.
4. User personalization rules.
5. Promoted playbook lessons.
6. Episodic run memory summaries.

If a lower layer conflicts with a higher layer, higher layer wins and the conflict is logged as a memory/playbook ticket, not silently merged.

## Run Flow

1. Route the request: Cloud > Bookmark > Hub.
2. Fetch the base bundle from the chosen scope.
3. Resolve personalization overlay by `agent_instance_id`.
4. Resolve plugins from local inventory and Hub.
5. Compile the effective runtime context:
   - base instructions;
   - overlay rules;
   - selected playbook lessons;
   - bounded memory summary;
   - plugin lock/update plan.
6. Execute in the caller runtime.
7. Emit events:
   - `Memory Events` for candidate memory updates;
   - `Skill Trial Events` for reusable skill evidence;
   - `Plugin Update Events` for dependency drift.
8. Curator promotes or rejects updates. Public Hub packages are not mutated.

## Self-Evolution

Self-evolution should be a proposal pipeline, not automatic mutation:

1. The agent proposes a patch to rules, playbooks, skills, or setup docs.
2. The proposal is stored as a candidate overlay change.
3. A verifier runs regression prompts and permission checks.
4. Low-risk playbook additions can be auto-promoted under workspace policy.
5. Rule changes, new tools, wider permissions, or public package changes require explicit approval.
6. Public evolution is a fork or republish action, never an implicit edit to the original Hub package.

## Plugin Drift And Auto-Upgrade

Add a plugin preflight before runtime execution:

```text
agent needs -> local inventory -> Hub plugin catalog -> update plan -> smoke test -> lock
```

Recommended tool contract:

- `agentlas.resolve_plugins(needs, localInventory, lockfile?)`
  returns installed, missing, outdated, blocked, and suggested updates.
- `agentlas.plugins.preflight(updatePlan, policy)`
  checks version compatibility, permissions diff, signatures/checksums, and smoke tests.
- `agentlas.plugins.apply_update(updatePlanItem)`
  installs or upgrades only approved items.

Automation policy:

- Patch/minor updates with the same or narrower permissions can auto-upgrade.
- Major updates, permission widening, new credential scopes, paid connectors, or unsigned packages require approval.
- Failed smoke tests roll back to the previous locked version.
- Every update writes an event to `.agentlas/plugin-update-events.jsonl`.
- The current resolved state writes to `.agentlas/plugin-lock.json`.

Recommended automation agent:

`plugin-curator-agent`

Triggers:

- before `agentlas.get_runtime_bundle` execution when dependencies are stale;
- after a call failure that names a missing tool/plugin;
- scheduled daily/weekly for installed Agentlas plugins.

Responsibilities:

- compare local installed versions with Hub latest;
- classify permission diffs;
- run a minimal MCP tool-list and sample-call smoke test;
- auto-apply safe updates;
- create approval tickets for risky updates;
- write rollback evidence and update receipts.

This is better than manual one-by-one checks because the update decision is tied to the actual agent's declared needs, local inventory, and permission delta.

## Acceptance Criteria

- `/hep-network` returns Cloud candidates before Bookmark candidates before public Hub candidates.
- `/hep-cloud` only returns Cloud candidates.
- Agent Cloud page shows two sections: own Cloud packages and saved Hub bookmarks.
- Hub cards and profile pages expose a save/bookmark button.
- Bookmarks are searchable through authenticated MCP.
- Runtime bundle preparation includes overlay and plugin preflight metadata.
- Plugin update automation never widens permissions without approval and always records a rollback path.
