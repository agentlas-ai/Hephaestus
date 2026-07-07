---
description: Use the Agentlas browser hardpoint for browser-required work.
---

Update fallback: if auto-update fails, run `hephaestus update` once. The current command still works without updating.

# /hep-browser

Use this for rendered pages, JS-heavy sites, click/form flows, login-visible
state, or browser evidence. The request is the exact text the user typed after
`/hep-browser`.

Behavior:
- `<url>` reads a rendered browser snapshot.
- `<url> "<instruction>"` or `<url> --act "<instruction>"` performs browser
  automation through `browser.agent_cli`, then captures a snapshot.
- Add `--read` to force snapshot-only mode when extra text is context.

## How to run

Run the shell block below verbatim, replacing only the `REQUEST` value.

```bash
REQUEST="<replace with the exact text the user typed after /hep-browser>"

case "$REQUEST" in
  "<replace"*) echo "REQUEST placeholder not filled -- substitute the user's request first." >&2; exit 2 ;;
esac

RUNNER=""
for candidate in \
  "$HOME/.agentlas/runtime/current/bin/hephaestus" \
  "./bin/hephaestus"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then RUNNER="$candidate"; break; fi
done
if [ -z "$RUNNER" ]; then
  for cache in "$HOME/.claude/plugins/cache/agentlas-core-engine/hephaestus" \
               "${CODEX_HOME:-$HOME/.codex}/plugins/cache/agentlas-core-engine/hephaestus"; do
    newest="$(ls -d "$cache"/*/bin/hephaestus 2>/dev/null | sort -V | tail -1)"
    if [ -n "$newest" ] && [ -x "$newest" ]; then RUNNER="$newest"; break; fi
  done
fi
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
"$RUNNER" hep-browser "$REQUEST"
```

Report whether `browser.agent_cli` mounted, whether setup is needed, the module
chain, the receipt id, and the action/snapshot result for automation runs.
