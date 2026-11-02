async function bodyOf(response: { json: () => Promise<unknown> }) {
  try {
    const value = await response.json()
    if (!value || typeof value !== "object" || Array.isArray(value)) return null
    return value as Record<string, unknown>
  } catch {
    return null
  }
}

type Loaded =
  | { empty: true }
  | { error: "Error." }
  | { id: string, stop: "not ready" | "ready to hand over" }

export async function loadCase(fetchImpl = fetch): Promise<Loaded> {
  let session
  try {
    session = await fetchImpl("/v1/session", { credentials: "include" })
  } catch {
    return { error: "Error." }
  }
  if (session.status === 401) return { empty: true }
  if (!session.ok) return { error: "Error." }
  const body = await bodyOf(session)
  const caseId = body && body.case_id
  if (typeof caseId !== "string" || !caseId) return { error: "Error." }
  let row
  try {
    row = await fetchImpl("/v1/case/" + encodeURIComponent(caseId), {
      credentials: "include",
    })
  } catch {
    return { error: "Error." }
  }
  if (row.status === 404) return { empty: true }
  if (!row.ok) return { error: "Error." }
  const found = await bodyOf(row)
  const stop = found && found.stop
  if (stop === "not ready" || stop === "ready to hand over") return { id: caseId, stop }
  return { error: "Error." }
}
