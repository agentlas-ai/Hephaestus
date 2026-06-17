# Changelog

## v0.7.1 - 2026-06-18

- Added the A2A Agent Card boundary: import external Agent Cards as pending
  alignment proposals, export public-safe cards at
  `/.well-known/agent-card.json`, and keep private/local fields out of public
  cards.
- Added caller-aware routing gates through CLI `route --caller` and MCP
  `hephaestus_route.caller_id`/`caller`, so agent-to-agent calls can be denied
  before a route is selected.
- Hardened A2A input handling: malformed JSON returns structured errors,
  non-object cards are rejected, and oversized skill lists are bounded.
- Made `ao lint` and `ao diff` return non-zero exits on invalid graphs or drift
  so CI and release gates cannot silently pass.
- Documented the architecture-sync handoff alongside the A2A upgrade and kept
  the broader ontology roadmap out of the release claim.

## v0.7.0 - 2026-06-16

- Published Hephaestus Stormbreaker as the robust execution contract with the
  v2 loop: scope lock, issue contract, failure memory, verifier-first plan,
  bounded evidence loop, adversarial review gate, outcome ledger, and final
  gate.
- Kept public benchmark claims inside the verified local operational robustness
  boundary.
