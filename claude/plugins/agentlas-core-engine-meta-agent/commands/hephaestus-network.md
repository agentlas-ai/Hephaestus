# /hephaestus-network

Route a natural-language request through the Hephaestus Network local-first
router. Also triggered by `@Hephaestus <request>` in chat.

Raw arguments: `$ARGUMENTS`

## Route

1. Find the first executable Hephaestus runner:

```bash
RUNNER=""
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
for candidate in \
  "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/bin/hephaestus}" \
  "${CODEX_PLUGIN_ROOT:+$CODEX_PLUGIN_ROOT/bin/hephaestus}" \
  "${PLUGIN_ROOT:+$PLUGIN_ROOT/bin/hephaestus}" \
  "$HOME/.claude/plugins/cache/agentlas-core-engine/hephaestus/"*/bin/hephaestus \
  "$CODEX_HOME_DIR/plugins/cache/agentlas-core-engine/hephaestus/"*/bin/hephaestus \
  "./bin/hephaestus" \
  "./claude/plugins/agentlas-core-engine-meta-agent/bin/hephaestus"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then RUNNER="$candidate"; break; fi
done
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
"$RUNNER" route "$ARGUMENTS" --runtime claude-code
```

2. Act on the returned JSON decision — never bypass it:
   - `action: "route"` — report the selected card (`selected.id`, `entrypoints.canonical_command`).
     If `approval_request` is present, ask the user to approve the listed
     capabilities FIRST; only after explicit approval invoke the selected
     agent's canonical command with the original request.
   - `action: "clarify"` — ask `clarify_question` with the candidate list and re-route with the answer.
   - `action: "hub_fallback"` or `"hub_candidates"` — the Hub needs approval.
     Show `approval_request.payload_preview` (redacted keywords only — the raw
     prompt is never sent). After the user explicitly approves, re-run with
     `--approve-hub` and present installable/cloud-callable candidates for a
     second approval before any use.
   - `action: "propose_new"` — offer to build a new agent/team via `/hephaestus`.
   - `action: "refuse"` — explain `reasons` (loop guard or privacy block). Do not retry around it.

3. Hard rules: local memory stays local unless the user explicitly approves an
   export; never auto-run `file_write`, `cloud_call`, `payment`, `publish`,
   `delete`, `private_data_export`, or `external_tool` capabilities without a
   user approval; report the routing `receipt_id` in your final message.

## Examples

```text
/hephaestus-network turn these meeting notes into a weekly report
/hephaestus-network 이 작업에 맞는 에이전트 찾아줘
@Hephaestus draft a launch plan for my product
```
