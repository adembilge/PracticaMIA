import assert from "node:assert/strict"
import { test } from "node:test"
import { loadThread, sendLine } from "../lib/thread.ts"

function response(status, payload) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => payload,
  }
}

const thread = {
  messages: ["Via Roma 1, Milano", "Please upload the lease."],
  stop: "not ready",
  question: "Please upload the lease.",
}

test("load reads the stored thread", async () => {
  let called
  const result = await loadThread("c 1", async (url, options) => {
    called = { url, options }
    return response(200, thread)
  })
  assert.equal(called.url, "/v1/case/c%201/messages")
  assert.equal(called.options.credentials, "include")
  assert.deepEqual(result, thread)
})

test("send posts one line", async () => {
  let called
  const result = await sendLine("c1", "Via Roma 1, Milano", async (url, options) => {
    called = { url, options }
    return response(200, thread)
  })
  assert.equal(called.url, "/v1/case/c1/messages")
  assert.equal(called.options.method, "POST")
  assert.equal(called.options.credentials, "include")
  assert.deepEqual(JSON.parse(called.options.body), { text: "Via Roma 1, Milano" })
  assert.deepEqual(result, thread)
})

test("a refusal keeps the sentence off the stored thread", async () => {
  const result = await sendLine("c1", "secret", async () => response(200, {
    messages: [],
    stop: "not ready",
    question: "Please upload the lease.",
    text: "I will not take your SPID password.",
  }))
  assert.equal(result.text, "I will not take your SPID password.")
  assert.deepEqual(result.messages, [])
})

test("a failed response returns Error.", async () => {
  const result = await loadThread("c1", async () => response(400, {}))
  assert.deepEqual(result, { error: "Error." })
})
