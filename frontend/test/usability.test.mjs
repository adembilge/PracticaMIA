import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"
import { copy } from "../lib/copy.ts"

const root = dirname(fileURLToPath(import.meta.url))
const app = join(root, "..", "app")

function read(path) {
  return readFileSync(path, "utf8")
}

function controlsInsideLabels(source) {
  const tags = [...source.matchAll(/<(input|textarea)\b/g)]
  for (const match of tags) {
    const before = source.slice(0, match.index)
    const open = before.lastIndexOf("<label")
    const close = before.lastIndexOf("</label>")
    if (open === -1 || close > open) return false
  }
  return tags.length > 0
}

test("journeys keep the shell, both stops, and the language query", () => {
  for (const page of ["case", "chat", "documents", "checklist", "review"]) {
    assert.equal(read(join(app, page, "page.tsx")).includes("CaseShell"), true)
  }
  const dashboard = read(join(app, "dashboard.tsx"))
  for (const state of ["loading", "empty", "error", "not ready", "ready to hand over"]) {
    assert.equal(dashboard.includes('"' + state + '"'), true)
  }
  const shell = read(join(app, "shell.tsx"))
  assert.equal(shell.includes('path + "?lang=it"'), true)
  assert.equal(shell.includes("lang={lang}"), true)
})

test("the narrow layout stacks the shell and keeps 44px targets", () => {
  const css = read(join(app, "globals.css"))
  assert.equal(css.includes("@media (max-width: 40rem)"), true)
  assert.equal(css.includes("grid-template-columns: 1fr"), true)
  assert.equal(css.includes("min-height: 44px"), true)
  assert.equal(css.includes("min-width: 44px"), true)
})

test("keyboard focus is visible and tab order is not rearranged", () => {
  const css = read(join(app, "globals.css"))
  for (const control of ["a:focus-visible", "button:focus-visible", "textarea:focus-visible", "input:focus-visible"]) {
    assert.equal(css.includes(control), true)
  }
  const sources = ["shell.tsx", "dashboard.tsx", "empty-case.tsx", "open-case.tsx", "chat/thread.tsx", "documents/papers.tsx", "checklist/list.tsx", "review/view.tsx"]
  for (const name of sources) assert.equal(read(join(app, name)).includes("tabIndex"), false)
})

test("every field sits in a label and no control asks for a password", () => {
  for (const name of ["empty-case.tsx", "chat/thread.tsx", "documents/papers.tsx", "review/view.tsx"]) {
    const source = read(join(app, name))
    assert.equal(controlsInsideLabels(source), true)
    assert.equal(source.includes('type="submit"'), true)
    assert.equal(source.includes('type="password"'), false)
  }
})

test("italian chrome differs and the document language follows the choice", () => {
  assert.equal(copy.en.chat, "Chat")
  assert.equal(copy.it.chat, "Chat")
  for (const key of ["case", "documents", "checklist", "review", "none", "continue", "loading", "notReady", "ready", "error", "name", "address"]) {
    assert.notEqual(copy.it[key], copy.en[key])
  }
  assert.equal(copy.en.error, "Error.")
  assert.equal(copy.it.notReady, "non pronto")
  assert.equal(copy.it.ready, "pronto da consegnare")
  assert.equal(copy.it.error, "Errore.")
  assert.equal(copy.en.name, "Name")
  assert.equal(copy.it.name, "Nome")
  assert.equal(copy.en.address, "Address")
  assert.equal(copy.it.address, "Indirizzo")
  const shell = read(join(app, "shell.tsx"))
  assert.equal(shell.includes("document.documentElement.lang"), true)
  assert.equal(shell.includes("lang: Lang"), true)
  assert.equal(read(join(app, "dashboard.tsx")).includes("<Language path=\"/\" lang={lang} />"), true)
  assert.equal(read(join(app, "empty-case.tsx")).includes("<Language path=\"/\" lang={lang} />"), true)
})

test("a failed send keeps the draft and announces the error", () => {
  assert.equal(read(join(app, "shell.tsx")).includes('role="alert"'), true)
  for (const name of ["empty-case.tsx", "chat/thread.tsx"]) {
    const source = read(join(app, name))
    const errorAt = source.indexOf("setWarning(text.error)")
    const clearAt = source.indexOf('setDraft("")')
    assert.equal(errorAt !== -1 && clearAt !== -1 && errorAt < clearAt, true)
    assert.equal(source.includes("text.ready"), false)
  }
})

test("a late response cannot replace the screen", () => {
  for (const name of ["dashboard.tsx", "chat/thread.tsx", "documents/papers.tsx", "checklist/list.tsx", "review/view.tsx"]) {
    const source = read(join(app, name))
    assert.equal(source.includes("let current = true"), true)
    assert.equal(source.includes("if (!current) return"), true)
    assert.equal(source.includes("current = false"), true)
  }
})

test("ready text appears only for a real handoff", () => {
  const review = read(join(app, "review/view.tsx"))
  assert.equal(
    review.includes('pack.stop === "ready to hand over" && typeof pack.link === "string" && typeof pack.notice === "string"'),
    true,
  )
  assert.equal(review.includes("{text.name}"), true)
  assert.equal(review.includes("{text.address}"), true)
  const page = read(join(app, "case/page.tsx"))
  assert.equal(page.includes("notReady"), true)
  assert.equal(page.includes("text.ready"), false)
  assert.equal(page.includes("copy[lang].ready"), false)
})
