# Agentlas OS Architecture Positioning

Date: 2026-07-08
Status: corrected positioning memo after rejecting the narrower "repeated work into agents" framing.
Scope: README, Product Hunt, model page, Hub/connector copy, and future launch copy.

## Corrected Core

Agentlas OS is not mainly "turn repeated work into agents."

That phrase is one possible use case, but it makes the product sound like an automation packager or a Claude subagent generator. The real product is broader:

> Agentlas OS is the architecture for running AI agents as an owned, local-first execution system.

More plainly:

> Anyone can create an agent. Agentlas gives agents the architecture to actually work.

The distinction matters because the market already has many ways to create agents:

- Claude Code subagents and Claude Agent SDK agents;
- OpenAI Agents SDK agents and handoffs;
- LangGraph orchestration graphs;
- browser-use / agent-browser style browser tools;
- MCP servers and skills;
- hosted agent platforms and workflow builders.

Agentlas should not compete as "another place to create an agent." It should compete as the operating layer that makes agents usable as a team: routing, memory, browser action, permissions, Hub borrowing, verification, local execution, packaging, and surfaces across Desktop, the Hephaestus plugin, and LLM command tools.

## One-by-One Product Map

### 1. Agent creation is only the entry point

Current evidence:

- `temp/AGENTLAS-MASTER-BRIEF-2026-07-03.md` defines Desktop as the body for building, hiring, and running agents.
- `agentlas_desktop/Hephaestus/.claude/commands/hep-build.md` covers single-agent creation, multi-agent team creation, packaging existing work, ontology, public profile copy, package gates, routing-card migration, and verification.
- `.agentlas/sitemap.json` inside Hephaestus defines three modes: single-agent creator, team builder, and Agentlas packager.

Implication:

Agentlas can build agents, but "agent builder" is too small. The product creates an operating architecture around agents.

### 2. Architecture is the advantage over "just make a Claude agent"

Claude subagents are useful, but the official Claude SDK docs make the boundary clear: a subagent starts with a fresh context and the parent-to-subagent channel is the Agent tool prompt string. The subagent gets its own prompt/tools, but not the parent's full conversation or tool results unless the caller passes needed context directly.

Agentlas's answer is not "we make better prompts." It is:

- canonical agent/team package contracts;
- runtime adapters across Claude Code, Codex, Gemini, Cursor, Antigravity, OpenCode, Hermes, and OpenClaw;
- routing cards and anti-triggers;
- memory tickets and Memory Curator promotion;
- PM Soul / Policy Gate / Eval / QA roles for teams;
- package verification before release;
- Hub/Cloud boundary and BYOM bundle execution;
- Desktop/plugin/browser surfaces that continue outside one chat session.

This is why "architecture" should be a headline word, not an internal detail.

### 3. Browser is not a side feature

Current evidence:

- `/hep-browser` is a first-class command next to build/network/cloud/search/call/upload.
- The browser command exists specifically for rendered pages, login-visible state, click/form behavior, JS-heavy evidence, and real browser snapshots.
- It can attach to a live Agentlas Browser CDP port so logged-in Desktop/browser state can be reused.
- It prefers human-facing URLs and has deterministic primitives like `--click-text`, `--click`, and `--wait-ms`.

Implication:

Agentlas should not market browser as "web browsing." It should market it as an execution hardpoint: the place where agents can see and act on real app surfaces, then return evidence.

Recommended phrase:

> Browser hardpoints for real app work, not screenshots in a prompt.

### 4. Hub is not a marketplace of downloadable prompts

Current evidence:

- The master brief defines Hub as an agent/team registry and market with borrowing, credits, and rent distribution.
- Hephaestus Network docs say Hub searches send redacted keywords, not raw prompts, and the router fetches BYOM bundles.
- `/hep-network` says Hub bundles are borrowed and then run locally in the current LLM/runtime with the current project's grounding.

Implication:

Agentlas Hub should be framed as "borrow expertise into your local execution system," not "download another agent."

Recommended phrase:

> Borrow specialists without handing them your data or copying their private work.

### 5. Local-first is a trust and cost model, not only privacy copy

Current evidence:

- Desktop README: runs AI-native apps and agent teams on Claude/ChatGPT/Gemini plans the user already pays for, locally.
- Desktop README: no model proxy; keys stay in OS keychain; chats and agents in local SQLite.
- Master brief: Agentlas does not host models; Hephaestus is open source; Hub/Cloud deliver bundles, not server-side model completions.

Implication:

The user value is not only "privacy." It is:

- no second model bill;
- no lock-in to a model vendor;
- no platform-owned agent memory;
- local chat/agent history;
- ability to move surfaces.

Recommended phrase:

> Your agents run on your LLMs, with your keys, on your machine.

### 6. Memory is governed architecture

Current evidence:

- `docs/memory-architecture.md` defines ticketed memory, PM Soul, Memory Curator, Policy Gate, candidate-first promotion, and no direct durable writes.
- `docs/ontology-runtime.md` defines project-local ontology activation, explicit source registration, SQLite storage, GraphRAG query, working memory, and direct durable-memory write prevention.

Implication:

Do not say "agents remember everything." Say the opposite: agents do not get to silently rewrite permanent memory.

Recommended phrase:

> Memory that is proposed, evidenced, and approved before it becomes durable.

### 7. Stormbreaker is the execution proof layer

Current evidence:

- Desktop README says serious work gets scope lock, goals, work packets, plugin selection, continuation, repair, and final-gate evidence.
- `/hep-storm` defines a verifier-first execution loop that refuses to report success without evidence.
- The memory record for this workspace already says the differentiator Mason wanted was not a better model but "the execution system that gets real work finished."

Implication:

Stormbreaker should be used to prove that Agentlas is not just a directory of agents. It is a completion discipline.

Recommended phrase:

> Agentlas does not stop at a draft. It routes, executes, repairs, and verifies.

### 8. Desktop and the plugin are product surfaces, not footnotes

Current evidence:

- Desktop README positions Agentlas Desktop as a local Apps OS for AI work.
- Hephaestus README positions the plugin as the open-source command surface for LLM runtimes.

Implication:

The public README should not make Hephaestus feel like the whole product. It should say:

- Agentlas Desktop: visual/local OS for apps and agent teams.
- Hephaestus: open-source engine and external LLM command surface.
- Agentlas Hub/Cloud: borrow/publish/sync layer.

## Competitive Frame

### Claude agents / subagents

Claude gives users a strong way to define and invoke specialized agents. The weakness for Agentlas positioning is not that Claude is weak. The point is that Claude agents live inside Claude's session/runtime model unless the user builds additional architecture around them.

Agentlas should say:

> Claude can run an agent. Agentlas gives the agent an operating system.

### OpenAI Agents SDK

OpenAI's Agents SDK is a serious orchestration layer: loops, handoffs, tracing, guardrails, sessions, and approvals. It is developer/server-oriented. OpenAI's docs say the SDK path fits when your server owns deployment, tools, storage, approval decisions, and product logic while the SDK runs the loop.

Agentlas distinction:

> OpenAI Agents SDK is for developers building an agent app. Agentlas OS is for users and builders who want agents, teams, browser work, memory, Hub borrowing, and local execution as an installed product surface.

### LangGraph

LangGraph is the best comparison for "architecture over prompt." Its docs frame it as a low-level orchestration runtime for durable execution, streaming, human-in-the-loop, and persistence.

Agentlas distinction:

> LangGraph is an orchestration framework. Agentlas OS is an installed operating layer with GUI, terminal, Hub, browser hardpoints, package contracts, and local-first runtime boundaries.

### Browser-use and agent-browser

Browser-use owns a powerful browser execution wedge: give your coding agent a reliable browser. Agentlas should not pretend browser is unique by itself.

Agentlas distinction:

> Browser-use gives agents a browser. Agentlas gives browser work a place in the agent operating system: routed agents, local memory, permissions, receipts, and verified completion.

### MCP

MCP is the connector layer. It gives AI apps standard access to tools, data, and workflows. Agentlas should not market MCP as the product itself.

Agentlas distinction:

> MCP connects tools. Agentlas decides which agent should use them, with what memory, what permissions, what browser session, and what verification gate.

## Better Catchphrase Direction

The previous repeated-work tagline:

Rejected. Too narrow. It sounds like workflow reuse.

Better candidates:

1. `Don't just create agents. Run them like a company.`
2. `Agents are easy to create. Agentlas gives them an operating system.`
3. `The architecture layer for agents that actually work.`
4. `Run owned and borrowed agents on the LLMs you already use.`
5. `Your agents, your memory, your browser, your models. One operating layer.`

Recommended README hero:

```md
# Agentlas OS

Don't just create agents. Run them like a company.

Agentlas OS gives agents the architecture they need to actually work:
routing, memory, browser control, permissions, verification, Hub specialists,
and local execution on the LLMs you already use. Hephaestus is the open-source
engine underneath.
```

Recommended Product Hunt tagline:

```text
An operating system for agents that actually work.
```

Recommended Korean line:

```text
에이전트는 누구나 만들 수 있습니다. Agentlas는 그 에이전트들이 실제로 일하게 만드는 구조입니다.
```

Sharper Korean social line:

```text
Claude에서 에이전트 하나 만드는 것과, 에이전트 회사가 굴러가는 구조를 갖는 건 다릅니다.
```

## README Structure After This Correction

1. Hero: Agentlas OS, not Hephaestus.
2. The problem: creating agents is easy; running agents reliably is the hard part.
3. What Agentlas adds: architecture.
4. Product surfaces:
   - Desktop
   - Hephaestus plugin
   - Hephaestus command surface
   - Hub/Cloud
5. Proof blocks:
   - browser hardpoint
   - routed Hub borrowing
   - Stormbreaker verification
   - governed memory
   - local-first BYOM/BYOK
6. Install prompt.
7. First run examples.
8. Architecture details.
9. Current limits.

## Words To Use

- architecture layer
- execution system
- operating layer
- browser hardpoint
- owned agents
- borrowed specialists
- local-first runtime
- governed memory
- routed teams
- verification gate
- receipts
- Hub bundle
- BYOM / BYOK
- command surface
- Desktop / Hephaestus plugin / LLM adapters

## Words To Avoid

- repeated work as the main frame
- agent builder as the main frame
- prompt marketplace
- autonomous workforce
- replace your team
- fully autonomous
- zero hallucinations
- browser browsing as if it were just page reading
- marketplace without borrow/runtime boundary

## Sources

Local:

- `temp/AGENTLAS-MASTER-BRIEF-2026-07-03.md`
- `temp/agentlascorevaluebrief.md`
- `agentlas_desktop/README.md`
- `agentlas_terminal/README.md`
- `agentlas/AgentsAtlas/README.md`
- `agentlas_desktop/Hephaestus/README.md`
- `agentlas_desktop/Hephaestus/.claude/commands/hep-browser.md`
- `agentlas_desktop/Hephaestus/.claude/commands/hep-build.md`
- `agentlas_desktop/Hephaestus/.claude/commands/hep-network.md`
- `agentlas_desktop/Hephaestus/.claude/commands/hep-storm.md`
- `agentlas_desktop/Hephaestus/docs/hephaestus-network-2.0.md`
- `agentlas_desktop/Hephaestus/docs/memory-architecture.md`
- `agentlas_desktop/Hephaestus/docs/ontology-runtime.md`

External:

- Claude Code Agent SDK docs: https://code.claude.com/docs/en/agent-sdk/overview
- Claude Code subagents docs: https://code.claude.com/docs/en/agent-sdk/subagents
- OpenAI Agents SDK docs: https://developers.openai.com/api/docs/guides/agents
- LangGraph docs: https://docs.langchain.com/oss/python/langgraph/overview
- Browser-use README: https://github.com/browser-use/browser-use
- MCP docs: https://modelcontextprotocol.io/docs/getting-started/intro
