---
description: Run Hephaestus to create/package Agentlas agents or open the project ontology GUI.
---

# /hephaestus

Run Hephaestus, the Agentlas Core Engine Meta-Agent, inside this Antigravity
workspace. The request is the text the user typed after `/hephaestus`. It may
be empty, `ontology`, or a build/package instruction such as
`create a research agent for SEC filings`.

## Step 0 — Resolve the engine root (always do this first)

Hephaestus may live in this workspace OR in a global runtime cache. Resolve the
engine root before routing:

```bash
ENGINE=""
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
# 1) Workspace-local package wins when present.
if [ -f "./AGENTS.md" ] && [ -f "./.agentlas/mode-map.json" ]; then
  ENGINE="."
else
  # 2) Otherwise use the newest globally installed engine (Claude/Codex plugin cache).
  for dir in \
    "$HOME/.claude/plugins/cache/agentlas-core-engine/hephaestus/"*/ \
    "$CODEX_HOME_DIR/plugins/cache/agentlas-core-engine/hephaestus/"*/
  do
    [ -f "$dir/SKILL.md" ] && ENGINE="$dir"
  done
fi
echo "ENGINE=$ENGINE"
```

If `ENGINE` is empty, go to the final section ("not installed").

## Route

### If the request is `ontology`

Open the project-local ontology GUI by running the first executable runner:

```bash
RUNNER=""
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
for candidate in \
  "./bin/hephaestus" \
  "./claude/plugins/agentlas-core-engine-meta-agent/bin/hephaestus" \
  "./codex/plugins/agentlas-core-engine-meta-agent/bin/hephaestus"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    RUNNER="$candidate"
  fi
done
if [ -z "$RUNNER" ]; then
  for cache in "$HOME/.claude/plugins/cache/agentlas-core-engine/hephaestus" \
               "${CODEX_HOME:-$HOME/.codex}/plugins/cache/agentlas-core-engine/hephaestus"; do
    newest="$(ls -d "$cache"/*/bin/hephaestus 2>/dev/null | sort -V | tail -1)"
    if [ -n "$newest" ] && [ -x "$newest" ]; then RUNNER="$newest"; break; fi
  done
fi
if [ -z "$RUNNER" ]; then
  echo "Hephaestus runtime not found. Run the installer first." >&2
  exit 1
fi
"$RUNNER" ontology --gui .
```

Report the returned `gui_url`, `db_path`, `inbox_path`, and verification status.

### Otherwise (create, package, or repair an agent/team)

All canonical files are read from `$ENGINE` (workspace layout uses
`.agents/skills/`; the global cache layout uses `skills/` — use whichever
exists under `$ENGINE`):

1. Read the canonical contract: `$ENGINE/AGENTS.md` if it exists, otherwise
   `$ENGINE/SKILL.md` (global cache entrypoint), plus `$ENGINE/agents/*/agent.md`.
2. Read `$ENGINE/.agentlas/mode-map.json` and
   `$ENGINE/.agentlas/global-commands.json` when present (workspace installs);
   the global cache ships the same routing rules inside `SKILL.md`.
3. Classify the request with the mode-classification skill
   (`$ENGINE/.agents/skills/mode-classification/SKILL.md` or
   `$ENGINE/skills/mode-classification/SKILL.md`) as single-agent builder,
   multi-agent team builder, or agentlas-packager.
4. If missing details would change files, adapters, or the public/private
   boundary, run the clarify-question-loop skill first (same two locations).
5. Generate or repair the smallest useful Agentlas package **in the current
   workspace** (never write into the global cache), then verify with
   `$ENGINE/scripts/verify-package.sh` when present.
6. Return `status`, `evidence`, `output`, `global_commands`, and `blockers`.
   The `global_commands` section must list the exact Claude Code, Codex, Gemini
   CLI, Antigravity, generic `AGENTS.md`, and terminal commands from
   `.agentlas/global-commands.json` (or the equivalents documented in
   `$ENGINE/SKILL.md`).

## If no engine root was found ("not installed")

Tell the user to run the one-touch installer from an OS terminal, then reopen
the workspace in Antigravity:

```bash
curl -fsSL https://raw.githubusercontent.com/agentlas-ai/Hephaestus/main/scripts/install-all-runtimes.sh | bash
```

The installer registers `/hephaestus` as an Antigravity global workflow at
`~/.gemini/antigravity/global_workflows/hephaestus.md` (and
`~/.gemini/antigravity-ide/global_workflows/` when that variant is installed),
so it is available in every Antigravity workspace.
