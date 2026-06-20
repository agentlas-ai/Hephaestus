# Hephaestus Call

Prepare explicitly named Agentlas Hub or Cloud agents.

Syntax: `/hep-call agent-a, agent-b {context}`.

Resolve the runner (`~/.agentlas/runtime/current/bin/hephaestus`, then
`./bin/hephaestus`), run `"$RUNNER" auth ensure --timeout 180`, split the
arguments into agent list and context, then run
`"$RUNNER" call "<agents>" "<context>" --runtime cursor`.

For each prepared agent, follow `output.entry_excerpt` and
`output.grounding.directive`. Report failures separately and include
`receipt_id` plus every prepared `execution_id`.
