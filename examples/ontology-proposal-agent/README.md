# Ontology Proposal Agent (reference)

Golden-path reference for the `ontology-backed-agent` overlay: a proposal
writing agent whose every corpus-backed claim carries a source ref, with a
separate-context verifier and a human gate before submission.

## Workflow

1. **ingest** — load company docs and past proposals from
   `.agentlas/ontology-inbox/` with `bin/ontology ingest` (HWPX/docx/pdf
   supported).
2. **retrieve** — query GraphRAG for the proposal topic. Returns chunks,
   entities, relation edges, and source spans.
3. **draft** — write the proposal from retrieved evidence; attach a source ref
   (source_id + span) to every corpus-backed claim.
4. **verify** — a verifier in a separate context (never the drafting agent)
   checks citation presence and source-span consistency. Self-grading is
   forbidden (`loop_policy: verified`).
5. **gate** — `side-effect-containment`: a human reviews before any submission
   or send.

## Contracts

Injected by rule from `.agentlas/contract-injection-map.json`
(see `.agentlas/injected-contracts.json`); the other contracts are
intentionally not injected (smallest useful package).

## Verify

```bash
examples/ontology-proposal-agent/verify.sh
```

Runs behavioral checks: Korean corpus ingest, retrieval with source spans,
privacy-scope blocking, and contract/loop-policy wiring.
