import assert from "node:assert/strict"
import { test } from "node:test"
import { loadCase } from "../lib/case.ts"

function response(status, payload) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => payload,
  }
}

test("a missing session is an empty dashboard", async () => {
  const calls = []
  const result = await loadCase(async (url, options) => {
    calls.push({ url, options })
    return response(401, { message: "The session is not valid.", case_id: "hidden" })
  })
  assert.deepEqual(result, { empty: true })
  assert.deepEqual(calls, [{ url: "/v1/session", options: { credentials: "include" } }])
})

test("a case the session cannot read is an empty dashboard", async () => {
  const calls = []
  const result = await loadCase(async (url) => {
    calls.push(url)
    if (url === "/v1/session") return response(200, { case_id: "c1", person_id: "p1" })
    return response(404, { message: "Not found.", stop: "ready to hand over" })
  })
  assert.deepEqual(result, { empty: true })
  assert.deepEqual(calls, ["/v1/session", "/v1/case/c1"])
})

test("the stored stop is returned as stored", async () => {
  for (const stop of ["not ready", "ready to hand over"]) {
    const result = await loadCase(async (url) => {
      if (url === "/v1/session") return response(200, { case_id: "c1" })
      return response(200, { id: "c1", stop, missing_field: "f02" })
    })
    assert.deepEqual(result, { id: "c1", stop })
  }
})

test("an unknown stop is Error.", async () => {
  const result = await loadCase(async (url) => {
    if (url === "/v1/session") return response(200, { case_id: "c1" })
    return response(200, { stop: "accepted" })
  })
  assert.deepEqual(result, { error: "Error." })
})

test("a thrown read is Error.", async () => {
  const result = await loadCase(async () => {
    throw new Error("down")
  })
  assert.deepEqual(result, { error: "Error." })
})
