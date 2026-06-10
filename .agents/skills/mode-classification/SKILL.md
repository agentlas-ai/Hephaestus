---
name: mode-classification
description: "Use before routing a /meta-agent request to choose single-agent-creator, team-builder, or agentlas-packager from the user's wording and available files."
---

# Mode Classification

Pick one Agentlas meta-agent mode before generating or repairing files.

## Procedure

1. Inspect the user request and any provided path, repo, ZIP, prompt, or agent
   files.
2. If existing material is being converted, repaired, cleaned, imported, or
   released, choose `agentlas-packager`.
3. Else if the request needs a roster, HQ, departments, debate, policy, eval,
   QA, handoffs, or parallel ownership, choose `team-builder`.
4. Else choose `single-agent-creator`.
5. Overlay check: if the request depends on knowledge search over user
   documents, evidence-based or citation-attached generation, or a document
   corpus (HWPX/docx/pdf/제안서/계약서/견적서), additionally apply the
   `ontology-backed-agent` overlay (`modes/ontology-backed-agent.md`) with
   `ontology_backed: true` on the chosen base mode.
6. Loop policy: derive `loop_policy` from task purpose and risk using
   `.agentlas/contract-injection-map.json` risk tiers — `none` for simple
   one-shot tasks, `self-correct` for complex or long-running work, `verified`
   (separate-context verifier + side-effect gate) when the agent performs
   external writes or sends. Do not force loops onto simple tasks.
7. If the choice changes the output and the request is ambiguous, run the
   clarify question loop instead of guessing.

## Return

Return the selected mode, whether the `ontology-backed-agent` overlay applies,
the derived `loop_policy`, and one short reason. Then route to the matching
builder.

## Reference

See `docs/mode-classifier.md`.
