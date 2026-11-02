import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"
import { loadReview, nameValue, signIn } from "../lib/review.ts"

const root = dirname(fileURLToPath(import.meta.url))
const blocked = {
  stop: "not ready",
  missing: ["f07"],
  name: null,
  address: null,
  language: "English",
  warnings: {
    name: { status: "missing", values: [], absent: ["lease"] },
    address: { status: "missing", values: [], absent: ["lease"] },
  },
}

function response(status, payload) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => payload,
  }
}

test("load reads the package", async () => {
  let called
  const result = await loadReview("c 1", async (url, options) => {
    called = { url, options }
    return response(200, blocked)
  })
  assert.equal(called.url, "/v1/case/c%201/review")
  assert.equal(called.options.method, undefined)
  assert.equal(called.options.credentials, "include")
  assert.deepEqual(result, blocked)
})

test("a link on a blocked case is refused", async () => {
  const result = await loadReview("c1", async () => response(200, {
    ...blocked,
    link: "https://www.anagrafenazionale.interno.it/servizi-al-cittadino/",
  }))
  assert.deepEqual(result, { error: "Error." })
})

test("name posts only the two values", async () => {
  let called
  const ready = {
    stop: "ready to hand over",
    missing: [],
    name: "Ada Lovelace",
    address: "Via Torino 20, Milano",
    language: "English",
    warnings: blocked.warnings,
    link: "https://www.anagrafenazionale.interno.it/servizi-al-cittadino/",
    notice: "I will not take your SPID password, and I will not file it.",
  }
  const result = await nameValue("c1", "Ada Lovelace", "Via Torino 20, Milano", async (url, options) => {
    called = { url, options }
    return response(200, ready)
  })
  assert.equal(called.url, "/v1/case/c1/review")
  assert.equal(called.options.method, "POST")
  assert.equal(called.options.credentials, "include")
  assert.deepEqual(JSON.parse(called.options.body), {
    name: "Ada Lovelace",
    address: "Via Torino 20, Milano",
  })
  assert.equal(result.link, ready.link)
})

test("the handoff names the sign-in and does not file", () => {
  assert.equal(signIn("English"), "SPID")
  assert.equal(signIn("Italian"), "CIE")
  const page = readFileSync(join(root, "..", "app", "review", "view.tsx"), "utf8")
  assert.equal(page.toLowerCase().includes("password"), false)
  assert.equal(page.includes('type="password"'), false)
  assert.equal(page.includes("anagrafe"), false)
  assert.equal(page.includes("pack.notice"), true)
  assert.equal(page.includes("You sign in yourself at"), true)
})
