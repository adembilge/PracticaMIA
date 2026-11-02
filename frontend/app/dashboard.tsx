"use client"

import { useEffect, useState } from "react"
import { copy, type Lang } from "../lib/copy"
import { loadCase } from "../lib/case"
import { EmptyCase } from "./empty-case"
import { OpenCase } from "./open-case"
import { Language, Warning } from "./shell"

export function Dashboard({ lang }: { lang: Lang }) {
  const text = copy[lang]
  const [view, setView] = useState<
    "loading" | "empty" | "error" | "not ready" | "ready to hand over"
  >("loading")

  useEffect(() => {
    let current = true
    loadCase().then((result) => {
      if (!current) return
      if ("error" in result) setView("error")
      else if ("empty" in result) setView("empty")
      else setView(result.stop)
    })
    return () => {
      current = false
    }
  }, [])

  if (view === "not ready" || view === "ready to hand over") {
    return <OpenCase lang={lang} stop={view} />
  }
  if (view === "empty") return <EmptyCase lang={lang} />
  return (
    <main id="content" lang={lang}>
      <Language path="/" />
      {view === "error" ? <Warning text={text.error} /> : <p className="status">{text.loading}</p>}
    </main>
  )
}
