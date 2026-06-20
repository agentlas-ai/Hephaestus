---
description: Upload an Agentlas agent after asking Cloud vs Hub first.
argument-hint: <agent folder or request>
---

# Hephaestus Upload

Raw arguments: `$ARGUMENTS`

Always ask the destination question before doing anything else, even if the
arguments already say upload, publish, add, Cloud, Hub, or a target folder:

```text
Cloud에 업로드 할까요? 다른사람들이 볼 수 없어요.
Upload to Cloud? Other people cannot see it.

Agentlas Hub에 업로드 할까요? 다른 사람들이 빌려 쓸 수 있어요.
Upload to Agentlas Hub? Other people can borrow it.
```

Do not package, publish, register, add-source, reindex, or call an upload API
until the user answers Cloud or Agentlas Hub.

After the user chooses:

- Cloud: upload as the signed-in owner's private Cloud package. Prefer
  `agentlas cloud publish <agent-folder> --visibility private-link --json`.
- Agentlas Hub: publish through the Forge gate. Prefer
  `node scripts/validate-routing-cards.mjs --path <agent-folder> --json`, then
  `node scripts/forge-sync.mjs --path <agent-folder> --publish --json` from the
  Forge root when the folder is a Forge package.

If the destination is answered but the target folder is ambiguous, ask for the
exact agent folder before running any upload.
