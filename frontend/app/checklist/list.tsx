"use client"

import { useEffect, useState } from "react"
import { loadCase } from "../../lib/case"
import { copy, type Lang } from "../../lib/copy"
import { loadList, type Progress } from "../../lib/list"
import { StatusLine, Warning } from "../shell"

const LABELS = {
  f07: "Please upload the lease or the ownership paper.",
  f08: "permesso di soggiorno",
  f09: "name and address",
} as const

const MISSING_TITLE = "Please upload the lease or the ownership paper. Your name must be on it."
const UNREADABLE = "The file cannot be read."

function warningFor(items: Progress["items"]) {
  const title = items.find((item) => item.id === "f07")
  if (!title) return ""
  if (title.state === "missing") return MISSING_TITLE
  if (title.state === "blocked") return UNREADABLE
  return ""
}

export function List({ lang }: { lang: Lang }) {
  const text = copy[lang]
  const [view, setView] = useState<"loading" | "empty" | "error" | "list">("loading")
  const [progress, setProgress] = useState<Progress | null>(null)

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
      loadList(result.id).then((loaded) => {
        if (!current) return
        if ("error" in loaded) {
          setView("error")
          return
        }
        setProgress(loaded)
        setView("list")
      })
    })
    return () => {
      current = false
    }
  }, [])

  if (view === "loading") return <p className="status">{text.loading}</p>
  if (view === "empty") return <Warning text={text.none} />
  if (view === "error" || !progress) return <Warning text={text.error} />
  const ready = progress.stop === "ready to hand over"
  const warning = warningFor(progress.items)
  return (
    <div className="block">
      <StatusLine word={ready ? text.ready : text.notReady} role={ready ? "ready" : "not-ready"} />
      <ul>
        {progress.items.map((item) => (
          <li key={item.id}>
            {LABELS[item.id]} <span className="status">{item.state}</span>
          </li>
        ))}
      </ul>
      {warning ? <Warning text={warning} /> : null}
    </div>
  )
}
