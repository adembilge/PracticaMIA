import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"
import { loadList } from "../lib/list.ts"

const root = dirname(fileURLToPath(import.meta.url))

function response(status, payload) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => payload,
  }
}

const progress = {
  stop: "not ready",
  missing: "f07",
  items: [
    { id: "f07", state: "missing" },
    { id: "f09", state: "waiting" },
  ],
}

test("load reads the stored list", async () => {
  let called
  const result = await loadList("c 1", async (url, options) => {
    called = { url, options }
    return response(200, progress)
  })
  assert.equal(called.url, "/v1/case/c%201/checklist")
  assert.equal(called.options.method, undefined)
  assert.equal(called.options.credentials, "include")
  assert.deepEqual(result, progress)
})

test("a failed response returns Error.", async () => {
  const result = await loadList("c1", async () => response(405, {}))
  assert.deepEqual(result, { error: "Error." })
})

test("the checklist has no way to mark an item done", () => {
  const page = readFileSync(join(root, "..", "app", "checklist", "list.tsx"), "utf8")
  assert.equal(page.includes("<form"), false)
  assert.equal(page.includes("checkbox"), false)
  assert.equal(page.includes("anagrafenazionale"), false)
})
