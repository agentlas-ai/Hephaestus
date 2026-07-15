// Local OpenCode plugin: capture the current user prompt, then inject the
// bounded Agentlas ontology capsule into the next system prompt. It uses only
// Bun/Node built-ins and the installed local runtime; there are no npm or
// network dependencies.

const latestBySession = new Map()
const RECALL_TIMEOUT_MS = 12_000

function promptText(parts) {
  return (parts || [])
    .filter((part) => part && part.type === "text" && typeof part.text === "string")
    .map((part) => part.text)
    .join("\n")
    .slice(0, 12000)
}

async function recall(directory, sessionID, prompt) {
  const home = process.env.HOME || ""
  const executable = `${home}/.agentlas/runtime/current/bin/agentlas-memory-hook`
  try {
    const child = Bun.spawn(
      [executable, "--host", "opencode", "--event", "UserPromptSubmit"],
      {
        stdin: new Blob([JSON.stringify({ cwd: directory, sessionID, user_prompt: prompt })]),
        stdout: "pipe",
        stderr: "ignore",
        env: process.env,
      },
    )
    let timer
    const completed = (async () => {
      try {
        const [output, status] = await Promise.all([
          new Response(child.stdout).text(),
          child.exited,
        ])
        const trimmed = output.trim()
        return status === 0 && trimmed.startsWith("<agentlas-memory-context") ? trimmed : ""
      } catch {
        return ""
      }
    })()
    const timedOut = new Promise((resolve) => {
      timer = setTimeout(() => {
        try {
          child.kill()
        } catch {
          // The child may have exited between the race and the kill.
        }
        resolve("")
      }, RECALL_TIMEOUT_MS)
    })
    const result = await Promise.race([completed, timedOut])
    clearTimeout(timer)
    return result
  } catch {
    return ""
  }
}

export const AgentlasMemoryPlugin = async ({ directory }) => ({
  event: async ({ event }) => {
    if (event?.type !== "session.deleted") return
    const properties = event.properties || {}
    const sessionID = properties.info?.id || properties.sessionID || properties.id
    if (sessionID) latestBySession.delete(sessionID)
  },

  "chat.message": async (input, output) => {
    const prompt = promptText(output.parts)
    if (!prompt) return
    const capsule = await recall(directory, input.sessionID, prompt)
    if (capsule) latestBySession.set(input.sessionID, capsule)
    else latestBySession.delete(input.sessionID)
  },

  "experimental.chat.system.transform": async (input, output) => {
    const capsule = input.sessionID ? latestBySession.get(input.sessionID) : ""
    if (capsule && !output.system.includes(capsule)) output.system.push(capsule)
  },

  "experimental.session.compacting": async (input, output) => {
    const capsule = latestBySession.get(input.sessionID)
    if (capsule && !output.context.includes(capsule)) output.context.push(capsule)
  },

  dispose: async () => latestBySession.clear(),
})
