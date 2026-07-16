---
description: Staff a task from registered Local, owner Cloud, and public Hub agents.
---
Update fallback: 자동 업데이트가 안 되면 `hephaestus update`를 한 번 실행하세요. 업데이트하지 않아도 현재 버전 명령은 그대로 동작합니다.

Act as the temporary top-level workforce orchestrator. Use local MCP server
`hephaestus-network`, the only host-visible Workforce MCP. Core owns its
Cloud/Hub upstream calls. Author a redacted
WorkOrder and call `workforce.search_candidates` with exact
`sourceScope: "network"` (registered Local + owner Cloud + public Hub), keeping
the response as `federationResult`. Author the final Selection yourself, call
`workforce.validate_selection` with
`{workOrder, candidateSet: federationResult.candidateSet, selection,
federationResult}`, keep `federatedSelection`, then call
`workforce.prepare_execution` with
`{workOrder, candidateSet: federationResult.candidateSet, selection,
federationResult, federatedSelection}`. Preserve source receipts/provenance and all
immutable pins. Execute planner/manager, workers, synthesis, and verifier as
distinct invocations with handoffs and preserved Team graphs. Never use legacy
`hephaestus_route`, direct remote search, deterministic staffing, silent
substitution, or preparation as execution proof.
