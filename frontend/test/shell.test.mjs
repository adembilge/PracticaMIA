import assert from "node:assert/strict"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { dirname, join } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"
import { startPerson } from "../lib/start.ts"

const root = dirname(fileURLToPath(import.meta.url))
const app = join(root, "..", "app")
const lib = join(root, "..", "lib")
const HREFS = ["/case", "/chat", "/documents", "/checklist", "/review"]
const LABELS = {
  en: ["Case", "Chat", "Documents", "Checklist", "Review", "No open case", "Continue", "Loading"],
  it: ["Caso", "Chat", "Documenti", "Elenco", "Revisione", "Nessun caso aperto", "Continua", "Caricamento"],
}

function files(dir) {
  const found = []
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) found.push(...files(path))
    else found.push(path)
  }
  return found
}

test("start posts an empty body and returns the id", async () => {
  let called
  const result = await startPerson(async (url, options) => {
    called = { url, options }
    return { ok: true, json: async () => ({ id: "p1" }) }
  })
  assert.equal(called.url, "/v1/person")
  assert.equal(called.options.method, "POST")
  assert.equal(called.options.body, undefined)
  assert.deepEqual(result, { id: "p1" })
})

test("a failed response returns Error.", async () => {
  const result = await startPerson(async () => ({ ok: false, json: async () => ({}) }))
  assert.deepEqual(result, { error: "Error." })
})

test("the shell has the routes, both languages, and no secret field", () => {
  const sources = files(app).concat(files(lib)).map((path) => readFileSync(path, "utf8"))
  const joined = sources.join("\n")
  assert.equal(joined.toLowerCase().includes("password"), false)
  assert.equal(joined.includes('type="password"'), false)
  const shell = readFileSync(join(app, "shell.tsx"), "utf8")
  for (const href of HREFS) assert.equal(shell.includes('"' + href + '"'), true)
  for (const page of ["case", "chat", "documents", "checklist", "review"]) {
    const text = readFileSync(join(app, page, "page.tsx"), "utf8")
    assert.equal(text.includes("CaseShell"), true)
  }
  const empty = readFileSync(join(app, "empty-case.tsx"), "utf8")
  assert.equal(empty.includes("CaseShell"), false)
  assert.equal(empty.includes("<label>"), true)
  assert.equal(empty.includes("<textarea"), true)
  assert.equal(empty.includes('type="password"'), false)
  for (const href of HREFS) assert.equal(empty.includes(href), false)
  const open = readFileSync(join(app, "open-case.tsx"), "utf8")
  assert.equal(open.includes("CaseShell"), true)
  const dashboard = readFileSync(join(app, "page.tsx"), "utf8")
  assert.equal(dashboard.includes("CaseShell"), false)
  for (const href of HREFS) assert.equal(dashboard.includes(href), false)
  const css = readFileSync(join(app, "globals.css"), "utf8")
  assert.equal(css.includes("40rem"), true)
  const copy = readFileSync(join(lib, "copy.ts"), "utf8")
  for (const label of LABELS.en.concat(LABELS.it)) assert.equal(copy.includes(label), true)
  const appText = files(app).map((path) => readFileSync(path, "utf8")).join("\n")
  assert.equal(appText.includes("anagrafenazionale"), false)
})
