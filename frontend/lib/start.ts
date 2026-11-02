export async function startPerson(fetchImpl = fetch) {
  const response = await fetchImpl("/v1/person", { method: "POST" })
  if (!response.ok) return { error: "Error." }
  const body = await response.json()
  if (!body || typeof body.id !== "string" || !body.id) return { error: "Error." }
  return { id: body.id }
}
