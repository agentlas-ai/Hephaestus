# /hep-search

Search Agentlas Cloud and Hub candidates without invoking an agent.

1. Resolve the runner: `~/.agentlas/runtime/current/bin/hephaestus` first, then
   `./bin/hephaestus`.
2. Ensure sign-in: `hephaestus auth ensure --timeout 180`.
3. Run: `hephaestus search "<request>" --runtime antigravity --limit 10`.
4. Show `cloud` results first and `hub` results second. Include rank, name,
   slug, description, callable/routing status, why, and `receipt_id`.
5. Do not execute any candidate from this workflow.
