---
description: Staff a task from registered Local, owner Cloud, and public Hub agents.
---
Update fallback: 자동 업데이트가 안 되면 `hephaestus update`를 한 번 실행하세요. 업데이트하지 않아도 현재 버전 명령은 그대로 동작합니다.

# /hep-network

Use the exact request after `/hep-network`. Act as the temporary top-level
workforce orchestrator and use local MCP server `hephaestus-network`, the only
host-visible Workforce MCP. Core owns its Cloud/Hub upstream calls. Network means
registered Local + signed-in owner Cloud + public Hub.

1. Author a redacted `agentlas.workforce-work-order.v1`; keep private project
   grounding on-host.
2. Call `workforce.search_candidates` with
   `{workOrder, sourceScope: "network"}` and keep the response as
   `federationResult`, retaining all source receipts and provenance.
3. Author `agentlas.workforce-selection.v1` yourself from content and
   qualification evidence; call `workforce.validate_selection` with
   `{workOrder, candidateSet: federationResult.candidateSet, selection,
   federationResult}` and keep `federatedSelection`. Revise on rejection.
4. Call `workforce.prepare_execution` with
   `{workOrder, candidateSet: federationResult.candidateSet, selection,
   federationResult, federatedSelection}` and require exact source, release,
   package/content, runtime, permission, and context pins.
5. Execute distinct planner/manager, worker, synthesis, and verifier
   invocations with explicit artifact handoffs and preserved Team graphs.

Report `executed` only from a receipt proving every child invocation and a
passing verifier. Otherwise report the last truthful state and source outages.
Do not call legacy `hephaestus_route`, bypass Core with direct remote search,
accept a deterministic picker, or use popularity/history/price/availability as
semantic fit.
