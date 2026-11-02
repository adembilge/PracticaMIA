type Item = { id: "f07" | "f08" | "f09", state: "missing" | "blocked" | "waiting" | "done" }

export type Progress = {
  stop: "not ready" | "ready to hand over"
  missing: "f07" | "f08" | "f09" | null
  items: Item[]
}

function isItem(value: unknown): value is Item {
  if (!value || typeof value !== "object") return false
  const row = value as Record<string, unknown>
  return (
    (row.id === "f07" || row.id === "f08" || row.id === "f09") &&
    (row.state === "missing" || row.state === "blocked" || row.state === "waiting" || row.state === "done")
  )
}

export async function loadList(caseId: string, fetchImpl = fetch) {
  let response
  try {
    response = await fetchImpl("/v1/case/" + encodeURIComponent(caseId) + "/checklist", {
      credentials: "include",
    })
  } catch {
    return { error: "Error." as const }
  }
  if (!response.ok) return { error: "Error." as const }
  let body
  try {
    body = await response.json()
  } catch {
    return { error: "Error." as const }
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) return { error: "Error." as const }
  const stop = body.stop
  const missing = body.missing
  const items = body.items
  if (stop !== "not ready" && stop !== "ready to hand over") return { error: "Error." as const }
  if (missing !== null && missing !== "f07" && missing !== "f08" && missing !== "f09") {
    return { error: "Error." as const }
  }
  if (!Array.isArray(items) || !items.every(isItem)) return { error: "Error." as const }
  return { stop, missing, items }
}
