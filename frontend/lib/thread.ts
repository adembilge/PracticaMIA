type Thread = {
  messages: string[]
  stop: "not ready" | "ready to hand over"
  question: string | null
  text?: string
}

function parsed(body: Record<string, unknown> | null): Thread | null {
  if (!body) return null
  const messages = body.messages
  const stop = body.stop
  const question = body.question
  if (!Array.isArray(messages) || messages.some((item) => typeof item !== "string")) return null
  if (stop !== "not ready" && stop !== "ready to hand over") return null
  if (question !== null && typeof question !== "string") return null
  const thread: Thread = {
    messages: messages as string[],
    stop,
    question: question as string | null,
  }
  if (typeof body.text === "string" && body.text) thread.text = body.text
  return thread
}

async function read(response: { ok: boolean, json: () => Promise<unknown> } | null) {
  if (!response || !response.ok) return { error: "Error." as const }
  try {
    const body = await response.json()
    if (!body || typeof body !== "object" || Array.isArray(body)) return { error: "Error." as const }
    const thread = parsed(body as Record<string, unknown>)
    if (!thread) return { error: "Error." as const }
    return thread
  } catch {
    return { error: "Error." as const }
  }
}

export async function loadThread(caseId: string, fetchImpl = fetch) {
  try {
    return await read(await fetchImpl("/v1/case/" + encodeURIComponent(caseId) + "/messages", {
      credentials: "include",
    }))
  } catch {
    return { error: "Error." as const }
  }
}

export async function sendLine(caseId: string, text: string, fetchImpl = fetch) {
  try {
    return await read(await fetchImpl("/v1/case/" + encodeURIComponent(caseId) + "/messages", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text }),
    }))
  } catch {
    return { error: "Error." as const }
  }
}
