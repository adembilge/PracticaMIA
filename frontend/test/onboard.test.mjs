import assert from "node:assert/strict"
import { test } from "node:test"
import { beginCase } from "../lib/begin.ts"

function response(status, payload) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => payload,
  }
}

test("begin posts the messages and returns the case", async () => {
  let called
  const result = await beginCase(["hello"], async (url, options) => {
    called = { url, options }
    return response(200, { case: { id: "c1", stop: "not ready", f04: "hidden" }, text: "saved" })
  })
  assert.equal(called.url, "/v1/onboarding")
  assert.equal(called.options.method, "POST")
  assert.equal(called.options.credentials, "include")
  assert.deepEqual(JSON.parse(called.options.body), { messages: ["hello"] })
  assert.deepEqual(result, { case: { id: "c1", stop: "not ready" } })
})

test("a refusal returns the sentence and no case", async () => {
  const result = await beginCase(["no"], async () => response(200, {
    case: null,
    text: "I will not open the address-change case.",
  }))
  assert.deepEqual(result, { text: "I will not open the address-change case." })
})

test("a failed response returns Error.", async () => {
  const result = await beginCase(["hello"], async () => response(400, {}))
  assert.deepEqual(result, { error: "Error." })
})
