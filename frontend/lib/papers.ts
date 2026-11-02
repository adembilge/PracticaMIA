type Paper = { id: string, role: "title" | "identity", status: "failed" | "unreadable" | "read" }

export type Papers = {
  stop: "not ready" | "ready to hand over"
  f05: string | null
  f06: string | null
  uploads: Paper[]
}

function isPaper(value: unknown): value is Paper {
  if (!value || typeof value !== "object") return false
  const row = value as Record<string, unknown>
  return (
    typeof row.id === "string" &&
    !!row.id &&
    (row.role === "title" || row.role === "identity") &&
    (row.status === "failed" || row.status === "unreadable" || row.status === "read")
  )
}

async function bodyOf(response: { json: () => Promise<unknown> }) {
  try {
    const value = await response.json()
    if (!value || typeof value !== "object" || Array.isArray(value)) return null
    return value as Record<string, unknown>
  } catch {
    return null
  }
}

export async function loadPapers(
  caseId: string,
  fetchImpl = fetch,
): Promise<Papers | { error: "Error." }> {
  const id = encodeURIComponent(caseId)
  let found
  let listed
  try {
    found = await fetchImpl("/v1/case/" + id, { credentials: "include" })
    listed = await fetchImpl("/v1/case/" + id + "/uploads", { credentials: "include" })
  } catch {
    return { error: "Error." as const }
  }
  if (!found.ok || !listed.ok) return { error: "Error." as const }
  const caseRow = await bodyOf(found)
  const papers = await bodyOf(listed)
  const stop = caseRow && caseRow.stop
  const uploads = papers && papers.uploads
  if (stop !== "not ready" && stop !== "ready to hand over") return { error: "Error." as const }
  const checked = stop === "ready to hand over" ? "ready to hand over" : "not ready"
  if (!Array.isArray(uploads) || !uploads.every(isPaper)) return { error: "Error." as const }
  const f05 = caseRow && caseRow.f05
  const f06 = caseRow && caseRow.f06
  return {
    stop: checked,
    f05: typeof f05 === "string" ? f05 : null,
    f06: typeof f06 === "string" ? f06 : null,
    uploads,
  }
}

export async function sendPaper(
  caseId: string,
  role: "title" | "identity",
  file: File,
  fetchImpl = fetch,
) {
  const body = new FormData()
  body.append("role", role)
  body.append("file", file)
  let response
  try {
    response = await fetchImpl("/v1/case/" + encodeURIComponent(caseId) + "/upload", {
      method: "POST",
      credentials: "include",
      body,
    })
  } catch {
    return { error: "Error." as const }
  }
  if (response.status === 400) return { failed: true as const }
  if (!response.ok) return { error: "Error." as const }
  const saved = await bodyOf(response)
  if (!saved || typeof saved.id !== "string" || saved.role !== role) return { error: "Error." as const }
  return { id: saved.id, role }
}
