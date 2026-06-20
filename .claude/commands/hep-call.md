---
description: Prepare explicitly named Agentlas Hub or Cloud agents.
argument-hint: 'agent-a, agent-b {context}'
allowed-tools: Bash, Read, Glob, Grep
---

# /hep-call

Call the exact agents named by the user. This prepares BYOM runtime bundles and
receipts; Claude still performs the actual model/tool execution.

Raw arguments: `$ARGUMENTS`

## Call

```bash
RUNNER=""
for candidate in \
  "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/bin/hephaestus}" \
  "${PLUGIN_ROOT:+$PLUGIN_ROOT/bin/hephaestus}" \
  "$HOME/.agentlas/runtime/current/bin/hephaestus" \
  "./bin/hephaestus"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then RUNNER="$candidate"; break; fi
done
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
if [ "${HEPHAESTUS_AUTH_AUTOPOPUP:-1}" != "0" ]; then
  "$RUNNER" auth ensure --timeout 180 >/dev/null 2>&1 || true
fi
RAW="$ARGUMENTS"
if printf '%s' "$RAW" | grep -q '{'; then
  AGENTS="${RAW%%\{*}"
  CONTEXT="${RAW#*\{}"
  CONTEXT="${CONTEXT%\}}"
else
  AGENTS="${RAW%% *}"
  CONTEXT="${RAW#* }"
fi
AGENTS="$(printf '%s' "$AGENTS" | sed 's/[[:space:]]*$//')"
CONTEXT="$(printf '%s' "$CONTEXT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
"$RUNNER" call "$AGENTS" "$CONTEXT" --runtime claude-code
```

## Answer Shape

1. Report each requested agent slug and status.
2. If `status: "prepared"`, use the returned `output.entry_excerpt` and
   `output.grounding.directive` as the agent's runtime instructions.
3. If an agent fails, continue with prepared agents and clearly list failures.
4. Include `receipt_id` and each prepared `execution_id`.

## Examples

```text
/hep-call market-researcher, report-writer {시장 리포트 초안 만들어줘}
/hep-call cloud:my-finance-agent {이 리포트 리스크 검토}
```
