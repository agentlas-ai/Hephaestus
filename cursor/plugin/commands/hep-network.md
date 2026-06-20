# Hephaestus Network routing

Route everything typed after this command through the Hephaestus Network
local-first router. Follow the `hephaestus-network` skill exactly: resolve the
runner (`~/.agentlas/runtime/current/bin/hephaestus`, then `./bin/hephaestus`,
then the newest Claude/Codex plugin cache copy), run
`"$RUNNER" auth ensure --timeout 180` first so the browser sign-in opens on
first use and existing Agentlas saved sign-ins are reused silently, then run
`"$RUNNER" route "<request>" --runtime cursor` in the terminal, then act on the
JSON decision (route / clarify / pipeline / hub_fallback / propose_new /
refuse). The router only chooses an agent or fetches a BYOM Hub bundle; actual
tool execution follows Cursor's runtime safety and permission model. Report the
routing `receipt_id`.
