---
name: hephaestus-network
description: "Use when the user types /hep-network, mentions @Hephaestus, or asks Agentlas to staff a task from registered Local, owner Cloud, and public Hub agents or teams. The active host LLM is the temporary orchestrator."
---

# Hephaestus Agent Workforce Network

The active host LLM staffs the task. Agentlas Core federates content menus from
registered Local, owner Cloud, and public Hub inventory. No source and no
deterministic layer is the decision-maker or a server-side LLM executor.

Source scopes are exact:

- `network`: Local + Cloud + Hub;
- `local`: registered Local packages only;
- `cloud`: the signed-in owner's Cloud packages only;
- `hub`: public Hub packages only.

Public demos and distribution proof use explicit `hub` scope. They must not use
private Local/Cloud inventory as evidence of public availability.

## Required MCP sequence

Use the Agentlas Core Workforce contracts in this order:

```text
workforce.search_candidates(sourceScope="network")
workforce.validate_selection(workOrder=..., candidateSet=federationResult.candidateSet, selection=..., federationResult=...)
workforce.prepare_execution(workOrder=..., candidateSet=federationResult.candidateSet, selection=..., federationResult=..., federatedSelection=...)
```

The source-internal `workforce.fetch_runtime_bundle` call is performed by Core
from the pinned original source session/digest. The host must not call it
directly or replace it with a slug/`latest` lookup.

The current CLI equivalent is `workforce search --scope network`. A host adapter
that does not yet expose typed `sourceScope` must report that wiring gap; it
must not silently call public Hub-only search and label it Network. Do not call
the legacy lexical router first. Do not turn install count, ratings, invocation
history, source precedence, or a deterministic top score into the staffing
decision. If a source is unavailable, preserve its finite failure receipt.

## 1. Perform job analysis

Act as the temporary top-level orchestrator. Convert the user's task into one
redacted `agentlas.workforce-work-order.v1` object. Keep raw local files,
secrets, memory, and private prompt details on the host. Create one `roleSlots`
entry per materially distinct responsibility. Each slot identifies:

- role/community and required skill or knowledge concepts;
- required MCP/tool capabilities;
- consumed and produced artifact kinds;
- runtime, language, modality, and entity-kind constraints;
- required and forbidden authority;
- cardinality, criticality, and collaboration edges;
- the minimum evidence level: declared, checked, demonstrated, or attested.

Do not create decorative roles. A single specialist is valid for a genuinely
single-role task; a composite task should become a real temporary task force.
Executable slots allow only `agent` or `team`; `group` is discovery-only until
an authoritative group execution contract exists.

## 2. Retrieve the menu, then make the LLM decision

Before calling any remote source, run the installed deterministic WorkOrder
boundary over every schema-declared string and structured identifier, including
nested roles, skills, tools, authorities, artifacts, edges, runtime/language,
and policy fields—not only prose fields. A path, personal/account identifier,
credential URL, private concept identifier, or secret-like value returns only
path/class repair evidence with `hubCalls=0` and a null rejected-object digest;
never trust the model's `redacted=true` assertion, mutate the object, echo the
rejected value, or compute/display a digest over rejected data. Ask Core for
`sourceScope="network"` only after that boundary accepts. Each source returns a broad content-only menu;
Core validates and unions them using canonical identity ordering. It performs
no semantic rerank. Read the exact roles,
skills, MCP tools, inputs/outputs, authority, eval evidence, communities,
release version, package hash, content digest, source receipt, and provenance.

Source precedence is not ranking. It applies only when the same
`agentDefinitionId` has verified identical lineage issuer/digest and the exact
same release version, package hash, content digest, and entity kind at multiple
sources. Then and only then shadow Local > Cloud > Hub. Similar names/slugs are
never deduplicated. Missing lineage or different releases fail closed for that
collided identity: Core quarantines the ambiguous definition and preserves
unrelated Local/Cloud/Hub candidates with finite aggregate conflict evidence.

You, the active host LLM, choose the ideal roster. Consider complementary
coverage and handoffs, not a scalar top-1 score. Return
`agentlas.workforce-selection.v1` with `decisionAuthor.kind = "host_llm"`, the
real host model id, exact slot/release assignments, graph edges, alternatives,
and short reason codes. Some nondeterminism in final judgment is intentional;
hard constraints are not.

If a required slot has inadequate coverage, use at most two same-host semantic
WorkOrder refinements across the whole decision. A provisional Selection may
request content expansion through `requestExpansionForSlots`; the adapter gives
the host only aggregate slot/count/gap data, never candidate identities. Never
fill a post with a semantically unrelated agent or repeat an exhausted request.

## 3. Validate and pin exact releases

Validate the selection in Core with the WorkOrder, federated CandidateSet,
federation receipt, and selection. Re-plan on rejection. The validator may
reject constraints, cardinality, cycles, drift, out-of-menu releases, or a
source-pin mismatch; it must never pick for you.

Do not send the merged CandidateSet to remote Hub/Cloud validation or
preparation: it is not one of their source sessions. Core pins every assignment
to the original source's selection session and candidate-set digest, then
fetches the exact release/package/content claims from that source. Call Core
federated preparation only after acceptance. Preparation must
return `agentlas.workforce-execution-plan.v5`, status `prepared`, an exact
`preparationReceiptId`, and an `executionRoster` whose release version,
package hash, and content digest match the candidate set. It returns BYOM
`directiveBundle` records. Every row must declare
`bundleDigestSchema=agentlas.workforce-runtime-bundle-digest.v4`; recompute its
canonical digest before execution and fail closed on mismatch. Digest values
allow only Unicode-scalar strings, booleans, null, arrays, and ASCII-keyed
objects; numbers, invalid keys, and `__proto__`/`prototype`/`constructor` fail
closed. A row must also carry a nonblank top-level `systemPrompt`,
`instructions`, or `agentMd`, a first-class digest-bound `permissionPolicy`,
and an agent-null/team-authoritative `executionGraph`. Missing permission
declarations become an explicit deny-all policy, never inherited host access;
incomplete claimed allowlists fail. The plan's digest-bound `executionContext`
must preserve every validated slot demand, WorkOrder/Selection edge and
artifact kind, assignment and reason code. Missing or
changed releases create unfilled posts; there is no silent substitution.

## 4. Execute the real task force

Run the prepared roster through the current host runtime:

1. planner/manager creates structured worker assignments;
2. each selected worker runs in a distinct model invocation with its exact
   release directive and only the needed local grounding;
3. workers emit explicit handoff artifacts;
4. synthesis runs after dependencies complete;
5. an independent verifier checks the requested result.

When a prepared release is itself a Team, honor its authoritative
manager/worker/synthesis graph; do not flatten it into one prompt. Follow the
row policy intersected with the host policy for all side effects. Unsupported
enforcement blocks execution. `zero-tools` requires an actually empty tool
inventory; a residual primitive isolated by forced read-only/no-filesystem is
`no-authority-sandbox`, not zero-tools.

Snapshot the just-in-time policy-filtered local tool menu as a private
`agentlas.workforce-tool-inventory.v1` artifact and give only that menu to the
executor planner. Never send the snapshot to Hub. The host LLM, not Hub or a
lexical rule, records the pair-scoped `capabilityBindingPlan`; its context,
tool-inventory, and planner-bound digests must validate before execution. Every
required tool capability maps to an exact snapshot entry and permitted tool.
A package policy mentioning a tool is not inventory proof, and a required
binding cannot run under no-authority enforcement.

If the host cannot create distinct child invocations, stop at `prepared` and
say so. A route id, bundle id, process exit code, or prose that imitates several
roles is not execution proof.

## 5. Truthful receipts

For an executed task force, retain one joined
`agentlas.workforce-execution-receipt.v2` joined to the exact v5 plan containing:

- selection and preparation receipt ids;
- orchestrator and planner model/invocation ids;
- `planner.parseSuccess`, `planner.fallbackUsed`, `toolInventoryDigest`, and
  `capabilityBindingPlanDigest`;
- every roster row's exact release/package/content/bundle/policy/graph digests,
  capability bindings, and handoff artifact refs;
- either one real direct invocation or a nested receipt proving manager-plan
  parse/no-fallback, exact declared workers in graph order, and
  manager-synthesis; never fabricate one aggregate team invocation;
- every actual model/provider/runtime, requested/applied effort with evidence,
  globally unique invocation id, and permission-enforcement evidence whose
  exact granted tool ids and inventory digest match the binding plan;
- synthesis and verifier invocation ids and verifier verdict.

Never report success when planner JSON fell back, child receipts are missing,
or verification did not pass. In the user-facing summary, name the actual
workers and distinguish `selected`, `prepared`, and `executed`.
