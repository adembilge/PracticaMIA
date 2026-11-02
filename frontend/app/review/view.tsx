"use client"

import { useEffect, useState, type FormEvent } from "react"
import { loadCase } from "../../lib/case"
import { copy, type Lang } from "../../lib/copy"
import { loadReview, nameValue, type Review as Package } from "../../lib/review"
import { StatusLine, Warning } from "../shell"

const MISSING_TITLE = "Please upload the lease or the ownership paper. Your name must be on it."
const WHICH = "Which value is correct? I will not pick one."

function conflictValues(view: Package) {
  return (["name", "address"] as const).flatMap((field) => {
    const column = view.warnings[field]
    if (column.status !== "conflict") return []
    return column.values.map((item) => ({ field, type: item.type, value: item.value }))
  })
}

export function Review({ lang }: { lang: Lang }) {
  const text = copy[lang]
  const [view, setView] = useState<"loading" | "empty" | "error" | "review">("loading")
  const [caseId, setCaseId] = useState("")
  const [pack, setPack] = useState<Package | null>(null)
  const [pending, setPending] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let current = true
    loadCase().then((result) => {
      if (!current) return
      if ("error" in result) {
        setView("error")
        return
      }
      if ("empty" in result) {
        setView("empty")
        return
      }
      loadReview(result.id).then((loaded) => {
        if (!current) return
        if ("error" in loaded) {
          setView("error")
          return
        }
        setCaseId(result.id)
        setPack(loaded)
        setView("review")
      })
    })
    return () => {
      current = false
    }
  }, [])

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const name = form.elements.namedItem("name")
    const address = form.elements.namedItem("address")
    if (!(name instanceof HTMLInputElement) || !(address instanceof HTMLInputElement) || pending) return
    if (!name.value.trim() || !address.value.trim()) return
    setPending(true)
    try {
      const result = await nameValue(caseId, name.value.trim(), address.value.trim())
      if ("error" in result) {
        setFailed(true)
        setPending(false)
        return
      }
      form.reset()
      setPack(result)
      setFailed(false)
      setPending(false)
    } catch {
      setFailed(true)
      setPending(false)
    }
  }

  if (view === "loading") return <p className="status">{text.loading}</p>
  if (view === "empty") return <Warning text={text.none} />
  if (view === "error" || !pack) return <Warning text={text.error} />
  const ready = pack.stop === "ready to hand over" && typeof pack.link === "string" && typeof pack.notice === "string"
  const readings = ready ? [] : conflictValues(pack)
  const missingTitle = !ready && pack.missing.includes("f07") && readings.length === 0
  return (
    <div className="block">
      <StatusLine word={ready ? text.ready : text.notReady} role={ready ? "ready" : "not-ready"} />
      {readings.length > 0 ? (
        <>
          <Warning text={WHICH} />
          <ul>
            {readings.map((item) => (
              <li key={item.field + item.type + item.value}>{item.type}: {item.value}</li>
            ))}
          </ul>
          <form onSubmit={onSubmit}>
            <label>
              {text.name}
              <input name="name" type="text" />
            </label>
            <label>
              {text.address}
              <input name="address" type="text" />
            </label>
            <button type="submit">{pending ? text.loading : text.continue}</button>
          </form>
        </>
      ) : null}
      {missingTitle ? <Warning text={MISSING_TITLE} /> : null}
      {failed ? <Warning text={text.error} /> : null}
      {ready ? (
        <>
          <p>{pack.name}</p>
          <p>{pack.address}</p>
          <p>
            You sign in yourself at <a href={pack.link}>{pack.link}</a>. {pack.notice}
          </p>
        </>
      ) : null}
    </div>
  )
}
