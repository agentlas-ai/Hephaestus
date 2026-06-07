# Claude Code Plugin Install

Install from a new computer with the OS terminal:

On a fresh Mac, install Apple Command Line Tools first if `git` is unavailable:

```bash
xcode-select --install
git --version
```

```bash
claude plugin marketplace add https://github.com/agentlas-ai/Hephaestus --sparse .claude-plugin claude/plugins
claude plugin install hephaestus@agentlas-core-engine
```

Then open or restart Claude Code in the project and type:

```text
/reload-plugins
/hephaestus ontology
```

If an older install still points at `agentlas-meta-agent`:

```bash
claude plugin marketplace update agentlas-core-engine
claude plugin uninstall agentlas-meta-agent@agentlas-core-engine
claude plugin install hephaestus@agentlas-core-engine
```

That command creates and opens:

```text
.agentlas/ontology-gui/index.html
```

Use the same slash command for builder work:

```text
/hephaestus create a research agent for SEC filing analysis
/hephaestus package this existing Claude agent into Agentlas architecture
```

Local validation from this repository:

```bash
claude plugin validate claude/plugins/agentlas-core-engine-meta-agent
claude plugin validate claude
```

Local checkout install:

```bash
claude plugin marketplace add ./claude
claude plugin install hephaestus@agentlas-core-engine
```

Use directly for one Claude session without installing:

```bash
claude --plugin-dir claude/plugins/agentlas-core-engine-meta-agent
```
