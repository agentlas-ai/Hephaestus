# README Demo GIF Snippet

Use this near the top of `README.md`, under the Hephaestus Network section.

```md
<p align="center">
  <img src="assets/hephaestus-network-mcp-demo.gif" alt="Hephaestus Network calls Hub MCP agents and returns a traceable summary">
</p>

<p align="center">
  <sub>One prompt. Hub MCP agents only. Hephaestus shows which public agents it called, why, and what they decided.</sub>
</p>
```

Short caption:

```text
One prompt. Hub MCP agents only. A traceable summary.
```

Demo prompt:

```text
Pick viral AgentSkills for GitHub.
```

GIF beats:

```text
0-2s   Hephaestus Network runs in --hub-only mode.
2-4s   marketplace.search_agents returns public Hub candidates.
4-7s   agentlas.get_runtime_bundle prepares three cloud-callable agents.
7-10s  It summarizes who was called, why, and the best README demo angle.
```
