import assert from "node:assert/strict"
import { test } from "node:test"
import { loadPapers, sendPaper } from "../lib/papers.ts"

function response(status, payload) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => payload,
  }
}

test("load reads the case and the current papers", async () => {
  const calls = []
  const result = await loadPapers("c 1", async (url) => {
    calls.push(url)
    if (url.endsWith("/uploads")) {
      return response(200, {
        stop: "not ready",
        uploads: [{ id: "u1", role: "title", status: "unreadable" }],
      })
    }
    return response(200, { stop: "not ready", f05: "named tenant", f06: null })
  })
  assert.deepEqual(calls, ["/v1/case/c%201", "/v1/case/c%201/uploads"])
  assert.equal(result.f05, "named tenant")
  assert.equal(result.uploads[0].status, "unreadable")
  assert.equal(result.stop, "not ready")
})

test("send posts the role and the file", async () => {
  const file = new File([new Uint8Array([1])], "lease.pdf", { type: "application/pdf" })
  let called
  const result = await sendPaper("c1", "title", file, async (url, options) => {
    called = { url, options }
    return response(200, { id: "u1", role: "title" })
  })
  assert.equal(called.url, "/v1/case/c1/upload")
  assert.equal(called.options.method, "POST")
  assert.equal(called.options.credentials, "include")
  assert.equal(called.options.body instanceof FormData, true)
  assert.equal(called.options.body.get("role"), "title")
  assert.equal(called.options.body.get("file").name, "lease.pdf")
  assert.deepEqual(result, { id: "u1", role: "title" })
})

test("a rejected file is a failed upload", async () => {
  const file = new File([new Uint8Array([1])], "note.txt")
  const result = await sendPaper("c1", "title", file, async () => response(400, {}))
  assert.deepEqual(result, { failed: true })
})

test("a failed response returns Error.", async () => {
  const result = await loadPapers("c1", async () => response(500, {}))
  assert.deepEqual(result, { error: "Error." })
})
