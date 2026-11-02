type Reading = { type: string, value: string }

type Column = {
  status: "conflict" | "missing" | "match"
  values: Reading[]
  absent: string[]
}

export type Review = {
  stop: "not ready" | "ready to hand over"
  missing: string[]
  name: string | null
  address: string | null
  language: "English" | "Italian"
  warnings: { name: Column, address: Column }
  link?: string
  notice?: string
}

export function signIn(language: Review["language"]) {
  return language === "Italian" ? "CIE" : "SPID"
}

function isReading(value: unknown): value is Reading {
  if (!value || typeof value !== "object") return false
  const row = value as Record<string, unknown>
  return typeof row.type === "string" && typeof row.value === "string"
}

function isColumn(value: unknown): value is Column {
  if (!value || typeof value !== "object") return false
  const row = value as Record<string, unknown>
  return (
    (row.status === "conflict" || row.status === "missing" || row.status === "match") &&
    Array.isArray(row.values) &&
    row.values.every(isReading) &&
    Array.isArray(row.absent) &&
    row.absent.every((item) => typeof item === "string")
  )
}

export function readReview(body: unknown): Review | { error: "Error." } {
  if (!body || typeof body !== "object" || Array.isArray(body)) return { error: "Error." }
  const row = body as Record<string, unknown>
  const stop = row.stop
  const missing = row.missing
  const name = row.name
  const address = row.address
  const warnings = row.warnings
  if (stop !== "not ready" && stop !== "ready to hand over") return { error: "Error." }
  if (!Array.isArray(missing) || !missing.every((item) => typeof item === "string")) {
    return { error: "Error." }
  }
  if (name !== null && typeof name !== "string") return { error: "Error." }
  if (address !== null && typeof address !== "string") return { error: "Error." }
  if (!warnings || typeof warnings !== "object" || Array.isArray(warnings)) return { error: "Error." }
  const columns = warnings as Record<string, unknown>
  if (!isColumn(columns.name) || !isColumn(columns.address)) return { error: "Error." }
  const language = row.language
  if (language !== "English" && language !== "Italian") return { error: "Error." }
  const link = row.link
  const notice = row.notice
  const warningsBody = { name: columns.name, address: columns.address }
  if (stop !== "ready to hand over" || name === null || address === null) {
    if ("link" in row || "notice" in row) return { error: "Error." }
    return { stop, missing, name, address, language, warnings: warningsBody }
  }
  if (typeof link !== "string" || !link || typeof notice !== "string" || !notice) return { error: "Error." }
  return { stop, missing, name, address, language, warnings: warningsBody, link, notice }
}

async function payload(response: { ok: boolean, json: () => Promise<unknown> }) {
  if (!response.ok) return { error: "Error." as const }
  try {
    return readReview(await response.json())
  } catch {
    return { error: "Error." as const }
  }
}

export async function loadReview(caseId: string, fetchImpl = fetch) {
  try {
    return await payload(await fetchImpl("/v1/case/" + encodeURIComponent(caseId) + "/review", {
      credentials: "include",
    }))
  } catch {
    return { error: "Error." as const }
  }
}

export async function nameValue(caseId: string, name: string, address: string, fetchImpl = fetch) {
  try {
    return await payload(await fetchImpl("/v1/case/" + encodeURIComponent(caseId) + "/review", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name, address }),
    }))
  } catch {
    return { error: "Error." as const }
  }
}
