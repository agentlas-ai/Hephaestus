# Claude Plugin Package

Claude-native plugin root:

```text
claude/plugins/agentlas-core-engine-meta-agent/
```

Validate:

```bash
claude plugin validate claude/plugins/agentlas-core-engine-meta-agent
claude plugin validate claude
```

Add this repo's Claude marketplace from a local checkout:

```bash
claude plugin marketplace add ./claude
claude plugin install agentlas-meta-agent@agentlas-core-engine
```

Use directly for a Claude session:

```bash
claude --plugin-dir claude/plugins/agentlas-core-engine-meta-agent
```
