# Hephaestus Search

Search Agentlas Cloud and public Hub candidates without invoking agents.

Resolve the runner (`~/.agentlas/runtime/current/bin/hephaestus`, then
`./bin/hephaestus`), run `"$RUNNER" auth ensure --timeout 180`, then run
`"$RUNNER" search "<request>" --runtime cursor --limit 10`.

Show `cloud` and `hub` sections with rank, name, slug, description,
callable/routing status, why, and `receipt_id`. Do not invoke candidates from
this command.
