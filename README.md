# Agentlas Core Engine Meta-Agent Team

Portable, Markdown-first meta-agent team for creating or packaging Agentlas
agents and agent teams across Codex, Claude Code, Gemini CLI, Cursor, and
generic `AGENTS.md` runtimes.

## The Team

This repo is intentionally a three-agent meta-agent team:

- `10-single-agent-builder`: creates one installable, self-evolving worker
  package.
- `20-multi-agent-team-builder`: creates a multi-role team package with
  orchestrator/HQ, PM Soul, Memory Curator, policy, eval, QA, memory, and
  runtime adapters.
- `30-agentlas-packager`: takes agents or teams made locally, in another tool,
  or in an existing repo, repairs them, and packages them into the Agentlas
  architecture for local use, Agentlas import, Codex plugin use, Claude adapter
  use, or public open-source release.

PM Soul, Memory Curator, runtime adapters, sitemap/task-bias, policy, eval, and
verification are architecture contracts generated or repaired by those three
agents. They are not extra members of this meta-agent team.

## What It Gives You

- Visible `agents/` folder with the three core team members.
- `modes/` contracts for single-agent creation, team creation, and packaging.
- `skills/` procedures for self-evolving single agents, team-builder packaging,
  Agentlas packaging, memory tickets, runtime adapters, PM Soul, sitemap/task
  bias, and release verification.
- `.agentlas/` contracts for mode map, agent card, company blueprint, sitemap,
  memory map, Memory Tickets, vault references, and validation ledger.
- Thin adapters for Codex, Claude Code, Gemini CLI, and generic `AGENTS.md`
  runtimes.
- One-line terminal install for any local project.

## One-Line Install

Run this from the project where you want the meta-agent team available:

```bash
curl -fsSL https://raw.githubusercontent.com/jeongmk522-netizen/agent_agentlas_core_engine_meta_agent/v0.1.0/scripts/install.sh | bash
```

To install into a different folder:

```bash
curl -fsSL https://raw.githubusercontent.com/jeongmk522-netizen/agent_agentlas_core_engine_meta_agent/v0.1.0/scripts/install.sh | bash -s -- /path/to/project
```

## Repository Map

```text
.
├── AGENTS.md                         # canonical portable entry point
├── CLAUDE.md                         # Claude Code adapter
├── GEMINI.md                         # Gemini CLI adapter
├── agent.md                          # single-file meta-agent team contract
├── agents/                           # 3 visible meta-agent team members
├── modes/                            # single, team, packaging contracts
├── skills/                           # reusable architecture procedures
├── .agents/                          # portable runtime-discovered core
├── .agentlas/                        # mode, memory, sitemap, package contracts
├── .claude/                          # Claude command/agent/skill adapters
├── .gemini/                          # Gemini adapter
├── codex/                            # Codex public plugin package scaffold
├── docs/                             # chain, PM, memory, runtime architecture
├── schemas/                          # JSON schemas for generated repos
├── templates/                        # starter files emitted by the meta-agent
├── examples/                         # minimal example output
└── scripts/                          # install and verification scripts
```

## Core Chain

1. The root meta-agent reads the request and selects one of three agents.
2. `10-single-agent-builder` creates one worker package when the user wants a
   single agent.
3. `20-multi-agent-team-builder` creates a team package when the user wants a
   roster, orchestrator, HQ, gates, or multi-role workflow.
4. `30-agentlas-packager` converts existing local or external agents/teams into
   Agentlas architecture and prepares distribution.
5. The selected agent emits or repairs the required Agentlas contracts:
   `AGENTS.md`, `.agents/`, `.agentlas/`, `modes/`, `skills/`, schemas,
   templates, runtime adapters, install scripts, and verification.

## Mode Split

`single-agent-creator` creates one installable worker. It may contain several
skills, setup guides, memory contracts, research refresh commands, and
self-evolution repair proposals, but it must not invent a team.

`team-builder` creates a multi-role team package. It must include an
orchestrator/HQ, PM Soul or project owner, Memory Curator, Policy Gate, worker
roles, eval judge, QA/evidence gate, handoff rules, runtime adapters, memory
architecture, and release checks.

`agentlas-packager` takes existing agents or teams and makes them Agentlas-ready:
canonical core, thin adapters, `.agentlas` contracts, public/private cleanup,
manifest, installer, and verification.

## Public Boundaries

This repo intentionally does not include private Agentlas web service code,
hosted billing, production credentials, local private research notes, raw
benchmarks, or customer data. It is the portable operating-system layer, not the
hosted SaaS backend.

## License

Apache-2.0. See [LICENSE](LICENSE).
