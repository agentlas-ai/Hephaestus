---
description: Staff a task from registered Local, owner Cloud, and public Hub agents.
argument-hint: <natural-language request>
---
Update fallback: 자동 업데이트가 안 되면 `hephaestus update`를 한 번 실행하세요. 업데이트하지 않아도 현재 버전 명령은 그대로 동작합니다.

# Hephaestus Workforce Network

Raw request: `$ARGUMENTS`

Act as the temporary top-level workforce orchestrator. Use MCP server
`hephaestus-network`, the local Agentlas OS Core and only host-visible
Workforce MCP. Core reaches Cloud and Hub through its internal upstream client.
Network means registered
Local + signed-in owner Cloud + public Hub.

1. Author a redacted `agentlas.workforce-work-order.v1` with substantive role
   slots, skills/knowledge/MCP capabilities, artifacts, runtimes, languages,
   authorities, cardinality, and collaboration edges. Private grounding stays
   local.
2. Call `workforce.search_candidates` with
   `{workOrder, sourceScope: "network"}` and keep the response as
   `federationResult`. Preserve source receipts and provenance; unavailable
   sources remain explicit.
3. From content and qualification evidence, author
   `agentlas.workforce-selection.v1` yourself. Call
   `workforce.validate_selection` with
   `{workOrder, candidateSet: federationResult.candidateSet, selection,
   federationResult}` and keep its response as `federatedSelection`. Revise on
   rejection. Deterministic code may
   enforce governance but may not pick, rerank, or silently substitute.
4. Call `workforce.prepare_execution` with
   `{workOrder, candidateSet: federationResult.candidateSet, selection,
   federationResult, federatedSelection}` and require
   exact source, release, package/content, runtime-bundle, permission, and
   context pins for every selected row.
5. Spawn distinct planner/manager, worker, synthesis, and verifier invocations
   with explicit artifact handoffs; preserve authoritative Team graphs.

Report `executed` only from a receipt proving every child invocation, handoff,
synthesis, and a passing independent verifier. Otherwise report the last
truthful state. Do not call legacy `hephaestus_route`, bypass Core with direct
remote search, or use popularity/history/price/availability as semantic fit.
Exact duplicate releases collapse Local > Cloud > Hub only with verified
identical lineage.
