---
description: Use the Agentlas browser hardpoint for browser-required work.
argument-hint: '<url-or-query>'
allowed-tools: Bash, Read, Glob, Grep
---
Update fallback: if auto-update fails, run `hephaestus update` once. The current command still works without updating.

# /hep-browser

Use this when the task needs a real browser, page rendering, login-visible state,
click/form behavior, or JS-heavy evidence. Prefer the Agentlas browser hardpoint
first; do not route browser work through generic research commands unless this
command reports that the hardpoint is unavailable.

Behavior:
- `/hep-browser <url>` reads a rendered browser snapshot.
- `/hep-browser <url> "<instruction>"` or `/hep-browser <url> --act "<instruction>"`
  performs browser automation through `browser.agent_cli`, then captures a
  snapshot.
- Add `--read` to force snapshot-only mode when extra text is context rather
  than an action.
- Pass `--cdp`, `--profile`, `--auto-connect`, or `--headed` only when the user
  needs an existing Desktop/browser session or a specific browser launch mode.

Raw arguments: `$ARGUMENTS`

## Run

```bash
RUNNER=""
for candidate in \
  "$HOME/.agentlas/runtime/current/bin/hephaestus" \
  "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/bin/hephaestus}" \
  "${PLUGIN_ROOT:+$PLUGIN_ROOT/bin/hephaestus}" \
  "./bin/hephaestus"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then RUNNER="$candidate"; break; fi
done
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
"$RUNNER" hep-browser "$ARGUMENTS"
```

## Answer Shape

1. Report whether `browser.agent_cli` was mounted or needs setup.
2. If setup is needed, show `hep-browser --setup` and `hep-browser --check`.
3. Include the receipt id and the browser module chain.

## Examples

```text
/hep-browser https://example.com
/hep-browser https://example.com "click the Docs link and report what changed"
/hep-browser https://example.com --act "open the pricing section" --cdp 9222 --keep-open
/hep-browser https://example.com "summarize this page" --read
/hep-browser login page render check
/hep-browser --setup
/hep-browser --check
```
