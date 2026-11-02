export async function beginCase(messages: string[], fetchImpl = fetch) {
  let response
  try {
    response = await fetchImpl("/v1/onboarding", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ messages }),
    })
  } catch {
    return { error: "Error." }
  }
  if (!response.ok) return { error: "Error." }
  let body
  try {
    body = await response.json()
  } catch {
    return { error: "Error." }
  }
  const found = body && body.case
  if (found && typeof found.id === "string" && found.id && (found.stop === "not ready" || found.stop === "ready to hand over")) {
    return { case: { id: found.id, stop: found.stop } }
  }
  if (body && body.case === null && typeof body.text === "string" && body.text) {
    return { text: body.text }
  }
  return { error: "Error." }
}
